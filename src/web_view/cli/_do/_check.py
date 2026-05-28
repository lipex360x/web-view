"""`web-view do check` — tick a checkbox / radio / switch."""

from __future__ import annotations

import argparse
from typing import Any

from ... import cdp
from ._shared import (
    add_addressing_arguments,
    add_runtime_arguments,
    run_addressed_verb,
)


def _perform(page: Any, addressing: tuple[str, str] | str, arguments: argparse.Namespace) -> None:
    if isinstance(addressing, tuple):
        role, name = addressing
        cdp.check(page, role, name, timeout_s=arguments.timeout)
        return
    page.locator(addressing).check(timeout=int(arguments.timeout * 1000))


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="checked", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do check --role checkbox --name "Remember me"
  web-view do check --selector "input[name=tos]"

Idempotent: no-op if the element is already checked.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "check",
        help="tick a checkbox / radio / switch",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
