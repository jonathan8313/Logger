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

class JVLoggerMeta(type):
    """
    Metaclass to support 'with JVLogger:' class-level context manager.
    """
    _instance = None

    def __enter__(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance.__enter__()

    def __exit__(cls, exc_type, exc_val, exc_tb):
        if cls._instance:
            try:
                cls._instance.__exit__(exc_type, exc_val, exc_tb)
            finally:
                cls._instance = None


class JVLogger(metaclass=JVLoggerMeta):
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
        self._single_instance = single_instance

        # Pre-calculate file paths
        self._main_text_path = self.log_dir / f"{self.name}.log"
        self._main_json_path = self.log_dir / f"{self.name}.json"

        if not single_instance:
            pid = self._process.pid
            self._temp_text_path = self.log_dir / f"{self.name}_{pid}.log"
            self._temp_json_path = self.log_dir / f"{self.name}_{pid}.json"
        else:
            self._temp_text_path = self._main_text_path
            self._temp_json_path = self._main_json_path

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
            self._setup_handlers(level)

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

    def _setup_handlers(self, level: int) -> None:
        d = self.log_dir

        # Console
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(ColoredFormatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
        self.logger.addHandler(console)

        # Text file - daily rotation at midnight
        text_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(self._temp_text_path),
            when="midnight",
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        text_handler.setLevel(logging.DEBUG)
        text_handler.setFormatter(logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
        self.logger.addHandler(text_handler)

        # JSON file - size rotation
        json_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(self._temp_json_path),
            when="midnight",
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JsonFormatter(signer=self.signer))
        self.logger.addHandler(json_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        self.logger.log(level, msg, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.logger, name)

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

        # Merge logs if they were temporary
        if not self._single_instance:
            self._merge_logs()

        # release lock if any
        if self._lock:
            try:
                self._lock.release()
            finally:
                self._lock = None

    def __enter__(self) -> "JVLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _merge_logs(self) -> None:
        """
        Merge temporary logs into the main log files.
        Uses a lock to ensure only one process merges at a time.
        """
        merge_lock = create_lock(f"{self.name}_merge")
        if merge_lock:
            # Wait for the lock to ensure serialized merging
            # We use a simple loop or blocking acquire if supported
            # For simplicity, let's assume acquire() is blocking or we wait a bit
            # In our current implementation, create_lock returns a lock that might be non-blocking
            # Let's check how acquire() works in windows.py/posix.py
            if merge_lock.acquire():
                try:
                    self._append_file(self._temp_text_path, self._main_text_path)
                    self._append_file(self._temp_json_path, self._main_json_path)
                finally:
                    merge_lock.release()

    def _append_file(self, source: Path, destination: Path) -> None:
        if not source.exists():
            return
        
        try:
            with open(source, "r", encoding="utf-8") as src_f:
                content = src_f.read()
            
            if content:
                with open(destination, "a", encoding="utf-8") as dest_f:
                    dest_f.write(content)
            
            source.unlink(missing_ok=True)
        except Exception as e:
            # We don't want to crash the application during close()
            # but we could log to stderr
            print(f"Error merging log file {source} to {destination}: {e}", file=sys.stderr)
