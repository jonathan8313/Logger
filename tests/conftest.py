import pytest
import tempfile
from pathlib import Path

@pytest.fixture()
def temp_log_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)
