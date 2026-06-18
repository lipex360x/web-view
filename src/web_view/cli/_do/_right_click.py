"""`web-view do right-click` — right-click (context-menu click) an element."""

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
        cdp.right_click(page, role, name, timeout_s=arguments.timeout)
        return
    page.locator(addressing).click(button="right", timeout=int(arguments.timeout * 1000))


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="right-clicked", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do right-click --role cell --name "A1"
  web-view do right-click --selector "[data-row=3]"
  web-view do right-click --role cell --name "A1" --frame 1

`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto').
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "right-click",
        help="right-click (context-menu) an element",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
