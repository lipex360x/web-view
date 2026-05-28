"""`web-view navigate` — load a URL in an already-running CDP Chrome."""

from __future__ import annotations

import argparse
from typing import Any

from .. import cdp
from ._shared import ensure_instance_on_port, print_no_tab_found


def _parse_tab_index(selector: str) -> int | None:
    candidate = selector[1:] if selector.startswith("-") else selector
    if candidate.isdigit():
        return int(selector)
    return None


def _pick_tab(context: Any, selector: str | None) -> Any:
    if selector is None:
        page = cdp.find_page(context, url_contains="")
        if page is not None:
            return page
        return context.pages[0] if context.pages else None
    index = _parse_tab_index(selector)
    if index is not None:
        if not context.pages:
            return None
        try:
            return context.pages[index]
        except IndexError:
            return None
    return cdp.find_page(context, url_contains=selector)


def handle(arguments: argparse.Namespace) -> int:
    if not ensure_instance_on_port(arguments.port):
        return 1
    with cdp.connect(port=arguments.port) as (_, context):
        if arguments.new_tab:
            cdp.open_tab(context, arguments.url)
            print(f"opened new tab on port {arguments.port}: {arguments.url}")
            return 0
        page = _pick_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        cdp.goto(page, arguments.url)
        print(f"navigated tab on port {arguments.port}: {arguments.url}")
    return 0


EPILOG = """\
Examples:
  web-view navigate --url https://example.com
  web-view navigate --url https://x.com --tab 0
  web-view navigate --url https://x.com --tab github.com
  web-view navigate --url https://x.com --new-tab
  web-view navigate --url https://x.com --port 9333

Tab selection:
  (default)             first non-helper tab
  --tab N               by index (0-based; negatives count from the end)
  --tab <substring>     by URL substring (first match wins)
  --new-tab             open the URL in a fresh tab

`--tab` and `--new-tab` are mutually exclusive. If no port has a running
CDP Chrome, the command prints a hint pointing at `web-view start`
and `web-view list` instead of leaking a Playwright traceback.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "navigate",
        help="load a URL in a running CDP Chrome (existing tab or new one)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", required=True, help="URL to load")
    parser.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT, help="CDP port")
    tab_selection = parser.add_mutually_exclusive_group()
    tab_selection.add_argument(
        "--tab",
        default=None,
        help="target tab: index (0-based, negatives allowed) or URL substring",
    )
    tab_selection.add_argument(
        "--new-tab",
        action="store_true",
        help="open the URL in a new tab instead of reusing one",
    )
    parser.set_defaults(func=handle)
