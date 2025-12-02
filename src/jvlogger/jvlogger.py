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
import sys
import os
import psutil
import socket
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
        lifecycle: bool = False  # <= nouveau paramètre
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
            self._setup_handlers(level, log_dir=log_dir)

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
        hostname = socket.gethostname()

        # Explicit directory provided → respect it
        if log_dir is not None:
            base_dir = Path(log_dir).resolve()
        else:
            # Frozen executable (PyInstaller)
            if hasattr(sys, "_MEIPASS"):
                base_dir = Path(sys.executable).resolve().parent
            else:
                base_dir = Path(sys.argv[0]).resolve().parent

        base_dir = base_dir / "logs"

        final_dir = base_dir / hostname
        final_dir.mkdir(parents=True, exist_ok=True)
        return final_dir

    def _setup_handlers(self, level: int, log_dir: Optional[Path] = None) -> None:
        d = self._log_dir(log_dir)

        # Console
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(ColoredFormatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
        self.logger.addHandler(console)

        # Text file - daily rotation at midnight
        text_path = d / f"{self.name}.log"
        text_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(text_path),
            when="midnight",
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        text_handler.setLevel(logging.DEBUG)
        text_handler.setFormatter(logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
        self.logger.addHandler(text_handler)

        # JSON file - size rotation
        json_path = d / f"{self.name}.json"
        json_handler = logging.handlers.RotatingFileHandler(
            filename=str(json_path),
            maxBytes=DEFAULT_JSON_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JsonFormatter(signer=self.signer))
        self.logger.addHandler(json_handler)

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
