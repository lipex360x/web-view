"""`web-view do press` — send keyboard key(s) to the active tab."""

from __future__ import annotations

import argparse
import sys

from ... import cdp
from .._shared import print_no_tab_found, resolve_single_port, resolve_target_tab


def _parse_keys(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def handle(arguments: argparse.Namespace) -> int:
    keys = _parse_keys(arguments.keys)
    if not keys:
        print("error: --keys must list at least one key", file=sys.stderr)
        return 1
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    with cdp.connect(port=target_port) as (_, context):
        page = resolve_target_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        cdp.press(page, *keys)
        if not arguments.quiet:
            print(f"pressed: {', '.join(keys)}")
    return 0


EPILOG = """\
Examples:
  web-view do press --keys "Enter"
  web-view do press --keys "Control+a,Backspace"
  web-view do press --keys "Meta+v" --tab github.com

`--keys` accepts a comma-separated chord list. Each segment is one
keystroke; chords use `+` (`Control+a`, `Meta+Shift+p`). Whitespace
around commas is stripped.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "press",
        help="send keyboard key(s) to the tab",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--keys",
        required=True,
        help="comma-separated key chord list (e.g. 'Control+a,Backspace')",
    )
    parser.add_argument("--port", type=int, default=None, help="CDP port (optional)")
    parser.add_argument("--tab", default=None, help="target tab: index or URL substring")
    parser.add_argument("--quiet", "-q", action="store_true", help="suppress success ack on stdout")
    parser.set_defaults(func=handle)
