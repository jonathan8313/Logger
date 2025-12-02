"""
Global exception hooks. They are not installed on import.
Call install_global_exception_handlers() explicitly from your application if needed.
"""

import sys
import logging
import traceback
import asyncio
import threading
from pathlib import Path

LAST_CRASH_FILE = Path(__file__).resolve().parent.parent / "last_crash.log"
_GLOBAL_HOOKS_INSTALLED = False

def dump_last_crash(exc_type, exc_value, exc_tb):
    try:
        with open(LAST_CRASH_FILE, "w", encoding="utf-8") as f:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass

def sys_excepthook(exc_type, exc_value, exc_tb):
    logger = logging.getLogger()
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    dump_last_crash(exc_type, exc_value, exc_tb)

def thread_excepthook(args):
    logger = logging.getLogger()
    # args: ThreadException args (thread, exc_type, exc_value, exc_traceback)
    logger.critical(
        f"Unhandled exception in thread '{args.thread.name}'",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    dump_last_crash(args.exc_type, args.exc_value, args.exc_traceback)

def asyncio_exception_handler(loop, context):
    logger = logging.getLogger()
    exception = context.get("exception")
    message = context.get("message", "Asyncio exception")
    if exception:
        logger.error(message, exc_info=exception)
        dump_last_crash(type(exception), exception, exception.__traceback__)
    else:
        logger.error(message)

def install_global_exception_handlers():
    """
    Install global exception handlers once. Safe to call multiple times.
    """
    global _GLOBAL_HOOKS_INSTALLED
    if _GLOBAL_HOOKS_INSTALLED:
        return

    sys.excepthook = sys_excepthook

    if sys.version_info >= (3, 8):
        try:
            threading.excepthook = thread_excepthook
        except Exception:
            # Some runtimes may be restrictive; swallow safely
            pass

    # asyncio: attach to running loop if available, otherwise leave it to the app
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(asyncio_exception_handler)
    except RuntimeError:
        # no running loop — that's fine
        pass

    _GLOBAL_HOOKS_INSTALLED = True
