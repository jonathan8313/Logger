# jvlogger

A production‑ready Python logger with multi‑instance support, colored console output, JSON log files, daily rotation, optional Windows single‑instance protection, log merging, lifecycle tracking, JSON signing and global exception hooks.

---

## Features

- **Colored console logs** – easy to read during development.
- **JSON log files** – structured logs for downstream processing.
- **Daily rotation** – automatic log file rollover at midnight.
- **Windows single‑instance protection** (optional) – prevents multiple processes from writing to the same file.
- **Multi‑instance log merging** – temporary logs are merged into the primary log on shutdown.
- **Lifecycle tracking** – records CPU/RAM usage at start and stop.
- **JSON log signing** – optional cryptographic signing of log entries.
- **Global exception hooks** – uncaught exceptions are logged automatically.

---

## Installation

```bash
pip install jvlogger
```

---

## Quick start

```python
from jvlogger import JVLogger
from app import main
# Simple usage as a context manager
with JVLogger(name="my_app") as jv:
    logger = jv.get_logger()
    logger.info("Application started")
    main(logger, args)

```

### Explicit usage

```python
# Create a wrapper without the context manager
jv = JVLogger(name="my_app", single_instance=False)
logger = jv.get_logger()
logger.debug("Debug message")
# Remember to close the wrapper to merge temporary logs
jv.close()
```

---

## API reference

- `JVLogger(name: str = None, level: int = logging.INFO, install_excepthooks: bool = True, single_instance: bool = False, mutex_name: str = None, signer: Signer = None, log_dir: str = None, lifecycle: bool = False)` – creates and configures the logger.
- `JVLogger.get_logger()` – returns the underlying `logging.Logger` instance.
- Standard logging methods (`debug`, `info`, `warning`, `error`, `critical`, `exception`, `log`) are proxied to the wrapped logger.
- `JVLogger.close()` – flushes handlers, merges temporary logs (if applicable) and releases any locks.

---

## Contributing

Contributions are welcome! Please open issues or pull requests on the GitHub repository. Follow the usual fork‑branch‑pull‑request workflow and ensure that new code is covered by tests.

---

## License

MIT License – see the `LICENSE` file for details.