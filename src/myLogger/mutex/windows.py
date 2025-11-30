import os
import ctypes
from ctypes import wintypes
from .base import SingleInstanceLock

class WindowsMutex(SingleInstanceLock):
    ERROR_ALREADY_EXISTS = 183

    def __init__(self, name: str):
        self.name = f"Local\\{name}"
        self.handle = None
        self._kernel32 = ctypes.windll.kernel32

        # Arg and result types
        self._kernel32.CreateMutexW.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        self._kernel32.CreateMutexW.restype = wintypes.HANDLE
        self._kernel32.GetLastError.restype = wintypes.DWORD

    def acquire(self) -> bool:
        # On non-windows this class should not be used; guard in selector
        self.handle = self._kernel32.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise OSError("CreateMutexW failed")
        # If the mutex already existed, GetLastError returns ERROR_ALREADY_EXISTS
        return self._kernel32.GetLastError() != self.ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if self.handle:
            try:
                self._kernel32.CloseHandle(self.handle)
            finally:
                self.handle = None