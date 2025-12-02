import os
import fcntl
from pathlib import Path
from .base import SingleInstanceLock

class FileLock(SingleInstanceLock):
    """
    Simple advisory lock using fcntl.flock on a file in /tmp.
    Non-blocking acquire: returns False if lock already held.
    """

    def __init__(self, name: str):
        lock_dir = Path(os.getenv("MYLOGGER_LOCK_DIR", "/tmp"))
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = lock_dir / f"{name}.lock"
        self._fd = None

    def acquire(self) -> bool:
        self._fd = open(self.lock_file, "a+")
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Optionally write pid for debugging
            try:
                self._fd.seek(0)
                self._fd.truncate(0)
                self._fd.write(str(os.getpid()))
                self._fd.flush()
            except Exception:
                pass
            return True
        except BlockingIOError:
            # someone else holds the lock
            try:
                self._fd.close()
            except Exception:
                pass
            self._fd = None
            return False

    def release(self) -> None:
        if self._fd:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            finally:
                try:
                    self._fd.close()
                finally:
                    self._fd = None