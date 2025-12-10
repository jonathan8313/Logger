"""
Main Logger wrapper. Exposes Logger class that configures:
- colored console handler
- rotating text file handler (daily)
- rotating json file handler (size-based)
- optional single-instance lock (platform-specific)
- optional signer passed into JsonFormatter
- optional global exception hooks (installable)
"""

import logging
import logging.handlers
from logging.config import dictConfig
import sys
import json
import socket
import psutil
from pathlib import Path
from typing import Optional
from .formatters import ColoredFormatter, JsonFormatter
from .hooks import install_global_exception_handlers
from .mutex import create_lock
from .exceptions import SingleInstanceError
from .signing import Signer
from .lifecycle import ApplicationLifecycleLogger


DEFAULT_BACKUP_COUNT = 7
DEFAULT_JSON_MAX_BYTES = 10_485_760  # 10 MB

class JVLogger:
    def __init__(
        self,
        name: str = None,
        level: int = logging.INFO,
        install_excepthooks: bool = True,
        single_instance: bool = False,
        mutex_name: str = None,
        signer: Signer = None,
        log_dir: str = None,
        lifecycle: bool = False
    ):
        """
        Create and configure a logger.

        Parameters:
            name: logger name (module / app). Defaults to script stem.
            level: logging level.
            install_excepthooks: if True, installs global exception hooks.
            single_instance: if True, try to acquire platform lock; raise SingleInstanceError if not possible.
            mutex_name: optional explicit name for the lock.
            signer: optional Signer instance to sign JSON logs.
            log_dir: optional directory path for logs; defaults to <script_dir>/logs
        """
        base_name = name or (Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "application")
        self.name = base_name
        self.signer = signer
        self._lock = None
        self._lifecycle = lifecycle
        self._process = psutil.Process()

        self.log_dir = self._log_dir(log_dir)

        # Optional single-instance lock (platform-aware)
        if single_instance:
            lock_id = mutex_name or base_name
            lock = create_lock(lock_id)
            if lock is not None:
                if not lock.acquire():
                    raise SingleInstanceError("Another instance is already running")
                self._lock = lock

        # Setup logger object
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        if not self.logger.handlers:
            self._setup_logging_from_json(level)

        logging.captureWarnings(True)

        if install_excepthooks:
            install_global_exception_handlers()

        if lifecycle:
            self._lifecycle = ApplicationLifecycleLogger(
                logger=self.logger,
                app_name=self.name,
            )
            self._lifecycle.start()
        else:
            self.logger.debug("Logger initialized")


    def _log_dir(self, log_dir: Optional[Path]) -> Path:
        # Explicit directory provided → respect it
        if log_dir is not None:
            final_dir = Path(log_dir).resolve()
            final_dir.mkdir(parents=True, exist_ok=True)
            return final_dir

        # Default behavior: <script_dir>/logs/<hostname>
        hostname = socket.gethostname()

        # Frozen executable (PyInstaller)
        if hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(sys.argv[0]).resolve().parent

        base_dir = base_dir / "logs"

        final_dir = base_dir / hostname
        final_dir.mkdir(parents=True, exist_ok=True)
        return final_dir


    def _setup_logging_from_json(self, level: int) -> None:
        config_path = Path(__file__).parent / "logging.json"
    
        with config_path.open(encoding="utf-8") as f:
            config = json.load(f)
    
        # --- Injection dynamique (OBLIGATOIRE) ---
    
        # Logger name
        config["loggers"][self.name] = config["loggers"].pop("APP_LOGGER")
    
        # Log directory + file names
        for handler in config["handlers"].values():
            if "filename" in handler:
                handler["filename"] = str(self.log_dir / handler["filename"].replace("APP_NAME", self.name))
    
        # Inject signer into JsonFormatter
        # Inject signer into JsonFormatter
        config["formatters"]["json"]["signer"] = self.signer
    
        dictConfig(config)

    
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(level)


    def get_logger(self) -> logging.Logger:
        return self.logger

    def close(self) -> None:
        if self._lifecycle:
            self._lifecycle.stop()
            self._lifecycle = None

        # Close and remove handlers
        for handler in list(self.logger.handlers):
            try:
                handler.close()
            except Exception:
                pass
            try:
                self.logger.removeHandler(handler)
            except Exception:
                pass

        # release lock if any
        if self._lock:
            try:
                self._lock.release()
            finally:
                self._lock = None

    def __enter__(self) -> logging.Logger:
        return self.get_logger()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
