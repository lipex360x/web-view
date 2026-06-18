"""`web-view do fill` — type a value into an element by role+name or selector."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ... import cdp
from ._shared import (
    add_addressing_arguments,
    add_runtime_arguments,
    run_addressed_verb,
)


def _read_value(arguments: argparse.Namespace) -> str:
    if arguments.value is not None:
        return arguments.value
    return sys.stdin.read()


def _perform(page: Any, addressing: tuple[str, str] | str, arguments: argparse.Namespace) -> None:
    value = _read_value(arguments)
    if isinstance(addressing, tuple):
        role, name = addressing
        cdp.fill(page, role, name, value, timeout_s=arguments.timeout)
        return
    page.locator(addressing).fill(value)


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="filled", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do fill --role textbox --name "Email" --value "user@example.com"
  web-view do fill --role textbox --name "Body" < long-message.txt
  echo "hello" | web-view do fill --selector "#title"
  web-view do fill --role textbox --name "Answer" --value "42" --frame 1

`--value` is optional: when omitted, the value is read from stdin until
EOF. Useful for multi-line content and shell here-docs.
`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto').
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "fill",
        help="type text into an input element",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    parser.add_argument(
        "--value",
        default=None,
        help="text to type (omit to read from stdin)",
    )
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
