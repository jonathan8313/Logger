"""
Simple verifier utility to validate signature fields in JSON log files.
Usage:
    from mylogger.verify import verify_log_file
    results = verify_log_file(Path("logs/app.json"), signer)
"""

from pathlib import Path
import json
from typing import List, Tuple, Dict, Any
from .signing import Signer

def verify_log_file(path: Path, signer: Signer) -> List[Tuple[int, bool, Dict[str, Any]]]:
    """
    Read JSON lines, verify signature field using signer.
    Returns list of tuples: (line_number, is_valid, parsed_entry_or_error)
    """
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception as exc:
                results.append((lineno, False, {"error": f"invalid json: {exc}"}))
                continue

            sig = entry.pop("signature", None)
            if not sig:
                results.append((lineno, False, {"error": "missing signature", "entry": entry}))
                continue

            canonical = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            valid = False
            try:
                valid = signer.verify(canonical, sig)
            except Exception as exc:
                results.append((lineno, False, {"error": f"verification exception: {exc}"}))
                continue

            results.append((lineno, bool(valid), entry))
    return results
