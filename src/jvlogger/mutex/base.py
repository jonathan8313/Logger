from abc import ABC, abstractmethod

class SingleInstanceLock(ABC):
    """Abstract base for single-instance locks."""

    @abstractmethod
    def acquire(self) -> bool:
        """Try to acquire; return True if acquired, False if another instance holds it."""
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        """Release the lock. Safe to call multiple times."""
        raise NotImplementedError