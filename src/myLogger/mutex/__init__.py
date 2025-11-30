import os
from typing import Optional

# lazy import to avoid platform-specific errors at import time
def create_lock(name: str) -> Optional[object]:
    """
    Factory that returns a platform-appropriate SingleInstanceLock implementation,
    or None if none available for current platform.
    """
    if os.name == "nt":
        from .windows import WindowsMutex
        return WindowsMutex(name)
    elif os.name == "posix":
        from .posix import FileLock
        return FileLock(name)
    else:
        # Unsupported platform — return None (no lock)
        return None
