"""
Command-line interface for simple log emission and testing.
Entry point `jvlogger` will map to jvlogger.cli:main via pyproject scripts.
"""

import argparse
import logging
from .jvlogger import JVLogger, ApplicationLifecycleLogger
from .signing import HMACSigner, RSASigner
from pathlib import Path
import os
import sys

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jvlogger", description="jvlogger CLI - emit test logs and run checks")
    p.add_argument("level", nargs="?", choices=["debug","info","warning","error","critical"], help="Log level")
    p.add_argument("message", nargs="?", help="Log message")
    p.add_argument("--name", help="Logger name (default: script name)")
    p.add_argument("--single-instance", action="store_true", help="Enable single-instance lock")
    p.add_argument("--no-hooks", action="store_true", help="Do not install global exception hooks")
    p.add_argument("--sign-hmac-key-file", help="Path to HMAC key file (base raw bytes)")
    p.add_argument("--sign-rsa-private", help="Path to RSA private PEM (requires cryptography)")
    p.add_argument("--test-exception", action="store_true", help="Raise a test exception to exercise global hook")
    p.add_argument("--show-config", action="store_true", help="Show logger configuration and exit")
    return p

def _load_signer_from_args(args):
    if args.sign_rsa_private:
        from .signing import RSASigner
        priv = Path(args.sign_rsa_private).read_bytes()
        return RSASigner(priv)
    if args.sign_hmac_key_file:
        key = Path(args.sign_hmac_key_file).read_bytes()
        return HMACSigner(key)
    return None

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    signer = _load_signer_from_args(args)

    wrapper = JVLogger(
        name=args.name,
        level=logging.DEBUG,
        install_excepthooks=not args.no_hooks,
        single_instance=args.single_instance,
        signer=signer,
    )

    logger = wrapper.get_logger()

    with ApplicationLifecycleLogger(logger, app_name=args.name):
        run_cleaning_logic()


    if args.show_config:
        logger.info(f"name={logger.name}, handlers={len(logger.handlers)}")
        wrapper.close()
        return

    if args.test_exception:
        # raise to let hooks exercise
        raise RuntimeError("CLI test exception")

    if args.level and args.message:
        lvl = getattr(logging, args.level.upper())
        logger.log(lvl, args.message)
        wrapper.close()
        return

    parser.print_help()
