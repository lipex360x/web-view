"""`web-view tab new` — open a new tab, optionally loading a URL."""

from __future__ import annotations

import argparse

from ... import cdp
from .._shared import resolve_single_port
from ._shared import add_common_arguments


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    target_url = arguments.url or "about:blank"
    with cdp.connect(port=target_port) as (_, context):
        cdp.open_tab(context, target_url)
        if not arguments.quiet:
            print(f"opened: {target_url}")
    return 0


EPILOG = """\
Examples:
  web-view tab new                                  # opens about:blank
  web-view tab new --url https://example.com
  web-view tab new --url https://x.com --port 9333 --quiet

Port selection follows `web-view navigate` semantics:
  `--port` is optional when exactly one CDP Chrome is running.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "new",
        help="open a new tab (about:blank by default)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default=None,
        help="URL to load in the new tab (defaults to about:blank)",
    )
    add_common_arguments(parser)
    parser.set_defaults(func=handle)
