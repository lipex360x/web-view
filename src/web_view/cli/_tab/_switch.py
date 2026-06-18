"""`web-view tab switch` — bring a tab to the front."""

from __future__ import annotations

import argparse
from typing import Any

from ... import cdp
from .._shared import print_no_tab_found, resolve_single_port, resolve_target_tab
from ._shared import add_common_arguments, is_index_selector


def _focus_by_index(context: Any, selector: str) -> Any:
    page = resolve_target_tab(context, selector)
    if page is not None:
        page.bring_to_front()
    return page


def _focus_by_url(context: Any, selector: str | None) -> Any:
    try:
        return cdp.switch_to_tab(context, url_contains=selector or "")
    except RuntimeError:
        return None


def _switch_ack(selector: str | None) -> str:
    if selector is None:
        return "switched: first tab"
    if is_index_selector(selector):
        return f"switched: tab {selector}"
    return f'switched: tab "{selector}"'


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    selector = arguments.tab
    with cdp.connect(port=target_port) as (_, context):
        if is_index_selector(selector):
            page = _focus_by_index(context, selector)
        else:
            page = _focus_by_url(context, selector)
        if page is None:
            print_no_tab_found(selector or "")
            return 1
        if not arguments.quiet:
            print(_switch_ack(selector))
    return 0


EPILOG = """\
Examples:
  web-view tab switch                                # focus first non-helper tab
  web-view tab switch --tab 1                        # focus tab at index 1
  web-view tab switch --tab classmark               # focus by URL substring
  web-view tab switch --tab 0 --port 9333 --quiet

Tab selection (defaults to the first non-helper tab when omitted):
  --tab N             by index (0-based; negatives count from the end)
  --tab <substring>   by URL substring (first match wins)
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "switch",
        help="bring a tab to the front (defaults to the first non-helper tab)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tab",
        default=None,
        help="tab to focus: index (0-based, negatives allowed) or URL substring",
    )
    add_common_arguments(parser)
    parser.set_defaults(func=handle)
