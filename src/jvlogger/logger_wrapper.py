from .jvlogger import JVLogger as BaseLogger
from .lifecycle_logger import ApplicationLifecycleLogger

class JVLogger(BaseLogger):
    def __init__(self, *args, lifecycle: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._lifecycle_enabled = lifecycle
        if lifecycle:
            self._lifecycle_manager = ApplicationLifecycleLogger(self.logger, app_name=self.name)
            self._lifecycle_manager.__enter__()

    def close(self):
        if getattr(self, "_lifecycle_enabled", False):
            self._lifecycle_manager.__exit__(None, None, None)
        super().close()