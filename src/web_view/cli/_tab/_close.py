"""`web-view tab close` — close a specific tab (requires --tab for safety)."""

from __future__ import annotations

import argparse

from ... import cdp
from .._shared import print_no_tab_found, resolve_single_port, resolve_target_tab
from ._shared import add_common_arguments, is_index_selector


def _close_ack(selector: str) -> str:
    if is_index_selector(selector):
        return f"closed: tab {selector}"
    return f'closed: tab "{selector}"'


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    selector = arguments.tab
    with cdp.connect(port=target_port) as (_, context):
        page = resolve_target_tab(context, selector)
        if page is None:
            print_no_tab_found(selector)
            return 1
        cdp.close_tab(page)
        if not arguments.quiet:
            print(_close_ack(selector))
    return 0


EPILOG = """\
Examples:
  web-view tab close --tab 2                         # close tab at index 2
  web-view tab close --tab github.com                # close by URL substring
  web-view tab close --tab -1 --port 9333 --quiet    # close the last tab

`--tab` is required: closing a tab is destructive, so there is no
implicit default. Pass a 0-based index (negatives count from the end)
or a URL substring (first match wins).
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "close",
        help="close a specific tab (--tab required)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tab",
        required=True,
        help="tab to close: index (0-based, negatives allowed) or URL substring",
    )
    add_common_arguments(parser)
    parser.set_defaults(func=handle)
