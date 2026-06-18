"""`web-view do upload` — attach a file to a file-input element."""

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
        cdp.upload(page, role, name, arguments.file, timeout_s=arguments.timeout)
        return
    page.locator(addressing).set_input_files(arguments.file)


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="uploaded", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do upload --role button --name "Choose file" --file ./report.pdf
  web-view do upload --selector "input[type=file]" --file ./avatar.png
  web-view do upload --role button --name "Attach" --file ./a.pdf --frame 1

`--file` is required and must point to an existing path.
`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto').
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "upload",
        help="attach a file to a file-input element",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    parser.add_argument(
        "--file",
        required=True,
        help="path to the file to attach",
    )
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
