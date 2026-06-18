"""`web-view do scroll-into-view` — scroll an element into the viewport."""

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
        cdp.scroll_into_view(page, role, name)
        return
    page.locator(addressing).scroll_into_view_if_needed()


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="scrolled to", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do scroll-into-view --role region --name "Footer"
  web-view do scroll-into-view --selector "#contact-form"
  web-view do scroll-into-view --role region --name "Footer" --frame 1

Does not wait for visibility — call `do hover` or `do click` afterwards
to interact with the element.
`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto').
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "scroll-into-view",
        help="scroll an element into view",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
