"""`web-view navigate` — load a URL in an already-running CDP Chrome."""

from __future__ import annotations

import argparse

from .. import cdp
from ._shared import print_no_tab_found, resolve_single_port, resolve_target_tab


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    with cdp.connect(port=target_port) as (_, context):
        if arguments.new_tab:
            cdp.open_tab(context, arguments.url)
            print(f"opened new tab on port {target_port}: {arguments.url}")
            return 0
        page = resolve_target_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        cdp.goto(page, arguments.url)
        print(f"navigated tab on port {target_port}: {arguments.url}")
    return 0


EPILOG = """\
Examples:
  web-view navigate --url https://example.com               # single instance
  web-view navigate --url https://x.com --port 9333         # explicit port
  web-view navigate --url https://x.com --tab 0
  web-view navigate --url https://x.com --tab github.com
  web-view navigate --url https://x.com --new-tab

Port selection (same rule as `web-view stop`):
  `--port` is optional when exactly one CDP Chrome is running. With zero
  or 2+ running instances, the command exits with the candidate ports.

Tab selection:
  (default)             first non-helper tab
  --tab N               by index (0-based; negatives count from the end)
  --tab <substring>     by URL substring (first match wins)
  --new-tab             open the URL in a fresh tab

`--tab` and `--new-tab` are mutually exclusive.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "navigate",
        help="load a URL in a running CDP Chrome (existing tab or new one)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", required=True, help="URL to load")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="CDP port (optional when exactly one CDP Chrome is running)",
    )
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
