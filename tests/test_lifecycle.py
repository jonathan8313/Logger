import logging
from jvlogger.lifecycle import ApplicationLifecycleLogger, PSUTIL_AVAILABLE


class DummyLogger(logging.Logger):
    def __init__(self):
        super().__init__("dummy")
        self.messages = []

    def info(self, msg):
        self.messages.append(msg)


def test_lifecycle_without_psutil(monkeypatch):
    monkeypatch.setattr(
        "jvlogger.lifecycle.PSUTIL_AVAILABLE",
        False,
    )

    logger = DummyLogger()
    lifecycle = ApplicationLifecycleLogger(logger, app_name="TestApp")

    lifecycle.start()
    lifecycle.stop()

    assert any("initialization started" in m for m in logger.messages)
    assert any("execution finished" in m for m in logger.messages)


def test_lifecycle_with_mocked_psutil(monkeypatch):
    class FakeProcess:
        def cpu_times(self):
            class T:
                user = 1.0
            return T()

        def memory_info(self):
            class M:
                rss = 100_000_000
            return M()

    monkeypatch.setattr(
        "jvlogger.lifecycle.PSUTIL_AVAILABLE",
        True
    )
    monkeypatch.setattr(
        "jvlogger.lifecycle.psutil",
        type("psutil", (), {"Process": lambda: FakeProcess()})
    )

    logger = DummyLogger()
    lifecycle = ApplicationLifecycleLogger(logger, app_name="TestApp")

    lifecycle.start()
    lifecycle.stop()

    assert any("CPU time" in m for m in logger.messages)
    assert any("RAM delta" in m for m in logger.messages)
