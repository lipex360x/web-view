"""`web-view do drag` — drag one element onto another."""

from __future__ import annotations

import argparse
import sys

from ... import cdp
from .._shared import (
    print_no_frame_found,
    print_no_tab_found,
    resolve_single_port,
    resolve_target_frame,
    resolve_target_tab,
)
from ._shared import addressing_probe


def _parse_role_name(raw: str) -> tuple[str, str] | None:
    if ":" not in raw:
        return None
    role, _, name = raw.partition(":")
    role = role.strip()
    name = name.strip()
    if not role or not name:
        return None
    return (role, name)


def handle(arguments: argparse.Namespace) -> int:
    source = _parse_role_name(arguments.from_)
    target = _parse_role_name(arguments.to)
    if source is None or target is None:
        print(
            "error: --from and --to expect 'role:name' (e.g. 'button:Item')",
            file=sys.stderr,
        )
        return 1
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    with cdp.connect(port=target_port) as (_, context):
        page = resolve_target_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        root = resolve_target_frame(page, arguments.frame, probe=addressing_probe(source))
        if root is None:
            print_no_frame_found(arguments.frame)
            return 1
        cdp.drag(root, source=source, target=target, timeout_s=arguments.timeout)
        if not arguments.quiet:
            print(f'dragged: {source[0]} "{source[1]}" -> {target[0]} "{target[1]}"')
    return 0


EPILOG = """\
Examples:
  web-view do drag --from "button:Item" --to "region:Trash"
  web-view do drag --from "row:Task A" --to "row:Task B"
  web-view do drag --from "button:Item" --to "region:Trash" --frame 1

`--from` and `--to` use the `role:name` micro-syntax. CSS-selector
drags are not supported in this MVP — use the library
(`cdp.drag(page, source=..., target=...)`) for selector-based drags.
`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto');
both endpoints are resolved inside the same frame.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "drag",
        help="drag one element onto another",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--from",
        dest="from_",
        required=True,
        help="source element as 'role:name'",
    )
    parser.add_argument(
        "--to",
        required=True,
        help="target element as 'role:name'",
    )
    parser.add_argument("--port", type=int, default=None, help="CDP port (optional)")
    parser.add_argument("--tab", default=None, help="target tab: index or URL substring")
    parser.add_argument(
        "--frame",
        default="auto",
        help="target frame: index (0 is the top frame), URL substring, or 'auto' (default)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="upper bound in seconds for element waits (default 15)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="suppress success ack on stdout")
    parser.set_defaults(func=handle)
