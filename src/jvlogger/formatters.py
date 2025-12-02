"""
Formatters: ColoredFormatter for console, JsonFormatter for file output.
JsonFormatter accepts an optional signer implementing sign/verify API.
"""

import logging
import json
from datetime import datetime
from typing import Optional
from .signing import Signer
from colorama import Fore, Style

_COLOR_LEVELS = {
    "DEBUG": Fore.BLUE + Style.DIM,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT,
}

class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _COLOR_LEVELS.get(record.levelname, "")
        record_copy = logging.makeLogRecord(record.__dict__.copy())
        record_copy.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record_copy)

class JsonFormatter(logging.Formatter):
    """
    Produce one JSON object per line. Optionally sign the canonical payload with a Signer.
    The signature is appended in the 'signature' field (base64).
    """

    def __init__(self, signer: Optional[Signer] = None):
        super().__init__()
        self.signer = signer

    @staticmethod
    def _canonical_bytes(obj: dict) -> bytes:
        # stable deterministic serialization
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }
        if record.exc_info:
            obj["traceback"] = self.formatException(record.exc_info)

        if self.signer:
            # compute signature over canonicalized payload (without 'signature' field)
            canonical = self._canonical_bytes(obj)
            signature_b64 = self.signer.sign(canonical)
            obj["signature"] = signature_b64

        return json.dumps(obj, ensure_ascii=False)