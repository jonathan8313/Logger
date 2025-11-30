import logging
from myLogger import Logger

def test_logger_creation(temp_log_dir):
    wrapper = Logger(
        name="test_app",
        level=logging.DEBUG,
        install_excepthooks=False,
        log_dir=temp_log_dir,
    )
    logger = wrapper.get_logger()

    assert logger.name == "test_app"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 3  # console + text + json

    wrapper.close()
