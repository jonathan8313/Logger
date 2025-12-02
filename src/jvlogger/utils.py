"""
Utility functions for human-readable formatting.

- duration formatting (wall / CPU time)
- byte size formatting (RAM, files, buffers)
"""

from __future__ import annotations


SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR
SECONDS_PER_MONTH = 30 * SECONDS_PER_DAY    # approximation
SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY    # approximation


def format_duration(seconds: float) -> str:
    """
    Convert a duration in seconds into a human-readable string.

    Units:
    - ms, s, min, h, day, month, year

    Examples:
        0.034            -> "34 ms"
        1.25             -> "1.25 s"
        61.8             -> "1 min 1.8 s"
        3_900            -> "1 h 5 min"
        172_800          -> "2 days"
        5_184_000        -> "2 months"
        63_072_000       -> "2 years"
    """
    if seconds <= 0:
        return "0 s"

    # milliseconds
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"

    remaining = int(seconds)
    parts: list[str] = []

    years, remaining = divmod(remaining, SECONDS_PER_YEAR)
    if years:
        parts.append(f"{years} year" + ("s" if years > 1 else ""))

    months, remaining = divmod(remaining, SECONDS_PER_MONTH)
    if months:
        parts.append(f"{months} month" + ("s" if months > 1 else ""))

    days, remaining = divmod(remaining, SECONDS_PER_DAY)
    if days:
        parts.append(f"{days} day" + ("s" if days > 1 else ""))

    hours, remaining = divmod(remaining, SECONDS_PER_HOUR)
    if hours:
        parts.append(f"{hours} h")

    minutes, remaining = divmod(remaining, SECONDS_PER_MINUTE)
    if minutes:
        parts.append(f"{minutes} min")

    # seconds (only if no larger unit or if remainder exists)
    if remaining and not parts:
        parts.append(f"{remaining:.0f} s")
    elif remaining and len(parts) < 2:
        parts.append(f"{remaining:.0f} s")

    return " ".join(parts)



def format_bytes(num_bytes: int) -> str:
    """
    Convert a byte count into a human-readable string.

    Examples:
        512        -> "512 B"
        2048       -> "2.0 KB"
        1048576    -> "1.0 MB"
        3221225472 -> "3.0 GB"
    """
    if num_bytes < 0:
        return "0 B"

    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if num_bytes < step:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= step

    return f"{num_bytes:.2f} EB"
