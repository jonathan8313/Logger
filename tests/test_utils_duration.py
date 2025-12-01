from myLogger.utils import format_duration, format_bytes


def test_duration_days():
    assert format_duration(172_800) == "2 days"


def test_duration_months():
    assert format_duration(5_184_000) == "2 months"


def test_duration_years():
    assert format_duration(63_072_000) == "2 years"


def test_duration_hours_minutes():
    assert format_duration(3_900) == "1 h 5 min"


def test_duration_ms():
    assert format_duration(0.02) == "20 ms"

def test_format_bytes_small():
    assert format_bytes(512) == "512.00 B"


def test_format_bytes_mb():
    assert format_bytes(1024 * 1024) == "1.00 MB"