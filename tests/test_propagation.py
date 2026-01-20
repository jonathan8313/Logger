import logging
from jvlogger import JVLogger

def test_jvlogger_context_manager_returns_wrapper():
    """Verify that 'with JVLogger() as logger' returns the JVLogger instance."""
    with JVLogger(name="test_wrapper") as logger:
        # Check that it's the wrapper, not the standard logger
        assert isinstance(logger, JVLogger)
        # Verify it has get_logger method
        inner_logger = logger.get_logger()
        assert isinstance(inner_logger, logging.Logger)
        assert inner_logger.name == "test_wrapper"

def test_jvlogger_delegation():
    """Verify that JVLogger wrapper delegates logging methods to the inner logger."""
    with JVLogger(name="test_delegation") as logger:
        # Test direct logging methods
        logger.info("Test info message")
        logger.debug("Test debug message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Test __getattr__ delegation (e.g., setLevel)
        logger.setLevel(logging.DEBUG)
        assert logger.level == logging.DEBUG
        
        # Test property access
        assert logger.name == "test_delegation"

def test_propagation_use_case():
    """Verify the user's specific use case."""
    loggers_received = []

    def set_lib_logger(lib_logger):
        loggers_received.append(lib_logger)

    with JVLogger(name="my_app") as logger:
        set_lib_logger(logger.get_logger())
        logger.info("Application started")
    
    assert len(loggers_received) == 1
    assert isinstance(loggers_received[0], logging.Logger)
    assert loggers_received[0].name == "my_app"
