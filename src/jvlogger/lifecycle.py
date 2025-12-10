import time
from typing import Optional
import logging
from .utils import format_bytes, format_duration
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


class ApplicationLifecycleLogger:
    """
    Logs application start/end with:
    - wall duration
    - CPU time (user)
    - RAM usage (RSS)
    """

    def __init__(self, logger: logging.Logger, app_name: str):
        self.logger = logger
        self.app_name = app_name
        self._process = psutil.Process()
        self._start_time: Optional[float] = None
        self._start_cpu: Optional[float] = None
        self._start_mem: Optional[int] = None

    def start(self) -> None:
        self._start_time = time.perf_counter()

        if PSUTIL_AVAILABLE:
            self._process = psutil.Process()
            self._start_cpu = self._process.cpu_times().user
            self._start_mem = self._process.memory_info().rss

        self.logger.info(
            f"=== Application [{self.app_name}] initialization started ==="
        )

    def stop(self) -> None:
        end_time = time.perf_counter()
        duration = end_time - (self._start_time or end_time)

        cpu_used = None
        mem_used = None

        if PSUTIL_AVAILABLE and self._process:
            end_cpu = self._process.cpu_times().user
            end_mem = self._process.memory_info().rss

            cpu_used = end_cpu - (self._start_cpu or end_cpu)
            mem_used = end_mem - (self._start_mem or end_mem)

        parts = [
            f"Duration: {format_duration(duration)}",
        ]

        if cpu_used is not None:
            parts.append(f"CPU time: {format_duration(cpu_used)}")

        if mem_used is not None:
            parts.append(f"RAM delta: {format_bytes(mem_used)}")

        self.logger.info(
            f"=== Application [{self.app_name}] execution finished | "
            + " | ".join(parts)
            + " ==="
        )