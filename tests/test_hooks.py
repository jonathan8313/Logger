from jvlogger.hooks import install_global_exception_handlers

def test_hooks_installable_twice():
    # should not crash or reinstall twice
    install_global_exception_handlers()
    install_global_exception_handlers()
