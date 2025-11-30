import pytest
from myLogger import Logger
from myLogger.exceptions import SingleInstanceError

class DummyLock:
    """Simule un lock pour les tests, sans toucher au filesystem."""
    def __init__(self, acquire_result=True):
        self.acquire_result = acquire_result
        self.released = False

    def acquire(self):
        return self.acquire_result

    def release(self):
        self.released = True


def test_single_instance_ok(monkeypatch, temp_log_dir):
    """
    Test that Logger acquires the single-instance lock successfully.
    We patch `create_lock` to avoid touching the filesystem.
    """
    monkeypatch.setattr("myLogger.myLogger.create_lock", lambda name: DummyLock(True))

    logger = Logger(
        name="lock_ok",
        single_instance=True,
        install_excepthooks=False,
        log_dir=temp_log_dir,
    )
    try:
        # Check logger instance exists
        assert logger.get_logger() is not None
        # No exception should be raised
    finally:
        logger.close()

def test_single_instance_conflict(monkeypatch, temp_log_dir):
    """
    Test that Logger raises SingleInstanceError when lock cannot be acquired.
    We patch `create_lock` to simulate another instance running.
    """
    monkeypatch.setattr("myLogger.myLogger.create_lock", lambda name: DummyLock(False))

    with pytest.raises(SingleInstanceError):
        Logger(
            name="lock_fail",
            single_instance=True,
            install_excepthooks=False,
            log_dir=temp_log_dir,
        )
