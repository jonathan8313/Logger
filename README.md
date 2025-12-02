# jvlogger

Production-ready Python logger.

## Features
- Colored console logs
- JSON log files
- Daily rotation
- Global exception hooks
- Windows single-instance protection
- last_crash.log

## Installation
```bash
pip install jvlogger
```

### How to use it:
```python
from jvlogger import JVLogger

logger_wrapper = JVLogger()
logger = logger_wrapper.get_logger()

run your app (logger)
logger_wrapper.close()