"""`web-view eval` — run a JS expression in a tab/frame and print the result as JSON."""

from __future__ import annotations

import argparse
import json
import sys

from .. import cdp
from ._shared import (
    print_no_frame_found,
    print_no_tab_found,
    resolve_single_port,
    resolve_target_frame,
    resolve_target_tab,
)


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    with cdp.connect(port=target_port) as (_, context):
        page = resolve_target_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        root = resolve_target_frame(page, arguments.frame)
        if root is None:
            print_no_frame_found(arguments.frame)
            return 1
        result = cdp.evaluate(root, arguments.javascript_expression)
    try:
        rendered = json.dumps(result)
    except TypeError:
        print("error: eval result is not JSON-serialisable", file=sys.stderr)
        return 1
    print(rendered)
    return 0


EPILOG = """\
Examples:
  web-view eval --js "document.title"
  web-view eval --js "[...document.querySelectorAll('video')].map(v => v.currentSrc)"
  web-view eval --js "document.body.innerText.length" --frame index_lms
  web-view eval --js "location.href" --tab github.com

The expression result is printed to stdout as JSON. A result that cannot
be serialised to JSON prints a structured error to stderr and exits 1.
`--frame` targets a frame (index, URL substring, or 'auto'; default 'auto',
which runs in the top frame).
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "eval",
        help="run a JS expression in a tab/frame and print the result as JSON",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--js",
        dest="javascript_expression",
        required=True,
        help="JavaScript expression to evaluate",
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
        "--frame",
        default="auto",
        help="target frame: index (0 is the top frame), URL substring, or 'auto' (default)",
    )
    parser.set_defaults(func=handle)
