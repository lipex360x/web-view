"""`web-view resize` — resize the OS window or page viewport of a running CDP Chrome."""

from __future__ import annotations

import argparse

from .. import cdp
from ._shared import print_no_tab_found, resolve_single_port, resolve_target_tab


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    with cdp.connect(port=target_port) as (_, context):
        page = resolve_target_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        if arguments.viewport:
            cdp.set_viewport(page, width=arguments.width, height=arguments.height)
            label = "viewport set"
        else:
            cdp.set_window_size(page, width=arguments.width, height=arguments.height)
            label = "resized"
        if not arguments.quiet:
            print(f"{label}: {arguments.width}x{arguments.height}")
    return 0


EPILOG = """\
Examples:
  web-view resize --width 1280 --height 720
  web-view resize --width 800 --height 600 --viewport
  web-view resize --width 1920 --height 1080 --port 9333 --quiet
  web-view resize --width 1024 --height 768 --tab classmark

Default mode resizes the OS-level Chrome window via CDP
`Browser.setWindowBounds` — the user sees the window physically change.
`--viewport` switches to a page-only viewport override (does not touch
the OS window; useful for responsive-layout testing).

Port / tab selection follows `web-view navigate` semantics:
  `--port` is optional when exactly one CDP Chrome is running.
  `--tab` accepts a 0-based index (negatives allowed) or URL substring.

Persistence: OS-window resize sticks until the user manually resizes or
Chrome restarts. Viewport override sticks per-page until the document
reloads.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "resize",
        help="resize the OS window or page viewport",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--width",
        type=int,
        required=True,
        help="target width in pixels",
    )
    parser.add_argument(
        "--height",
        type=int,
        required=True,
        help="target height in pixels",
    )
    parser.add_argument(
        "--viewport",
        action="store_true",
        help="override only the page viewport instead of the OS window",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="CDP port (optional when exactly one CDP Chrome is running)",
    )
    parser.add_argument(
        "--tab",
        default=None,
        help="target tab: index (0-based, negatives allowed) or URL substring",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="suppress success ack on stdout",
    )
    parser.set_defaults(func=handle)
