"""`web-view do dblclick` — double-click an element."""

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
        cdp.dblclick(page, role, name, timeout_s=arguments.timeout)
        return
    page.locator(addressing).dblclick(timeout=int(arguments.timeout * 1000))


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="double-clicked", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do dblclick --role link --name "Open"
  web-view do dblclick --selector ".editable-cell"
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "dblclick",
        help="double-click an element",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
