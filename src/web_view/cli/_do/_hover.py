"""`web-view do hover` — move the pointer over an element."""

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
        cdp.hover(page, role, name, timeout_s=arguments.timeout)
        return
    page.locator(addressing).hover(timeout=int(arguments.timeout * 1000))


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="hovered", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do hover --role button --name "Tooltip target"
  web-view do hover --selector ".dropdown-trigger"
  web-view do hover --role button --name "Tip" --frame 1

`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto').
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "hover",
        help="move the pointer over an element",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
