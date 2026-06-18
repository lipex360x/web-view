"""`web-view do click` — click an element by role+name or CSS selector."""

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
        cdp.click(page, role, name, timeout_s=arguments.timeout)
        return
    page.locator(addressing).click(timeout=int(arguments.timeout * 1000))


def handle(arguments: argparse.Namespace) -> int:
    return run_addressed_verb(arguments, verb="clicked", perform_action=_perform)


EPILOG = """\
Examples:
  web-view do click --role button --name "Next slide"
  web-view do click --selector "[data-testid=submit]"
  web-view do click --role link --name "Open" --tab github.com
  web-view do click --role button --name "Go" --timeout 30 --quiet
  web-view do click --role button --name "ENTER" --frame index_lms

Addressing: pass `--role + --name` OR `--selector` (not both).
`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto').
Port / tab selection follows `web-view navigate` semantics.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "click",
        help="click an element",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_addressing_arguments(parser)
    add_runtime_arguments(parser)
    parser.set_defaults(func=handle)
