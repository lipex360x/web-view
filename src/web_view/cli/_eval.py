"""`web-view eval` — run a JS expression in a tab/frame and print the result as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import cdp
from ._shared import (
    print_no_frame_found,
    print_no_tab_found,
    resolve_single_port,
    resolve_target_frame,
    resolve_target_tab,
)


def _resolve_expression(arguments: argparse.Namespace) -> str | None:
    if arguments.javascript_file is not None:
        path = Path(arguments.javascript_file).expanduser()
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            print(
                f"error: cannot read --js-file {arguments.javascript_file!r}: {error}",
                file=sys.stderr,
            )
            return None
    if arguments.javascript_expression == "-":
        return sys.stdin.read()
    return arguments.javascript_expression


def handle(arguments: argparse.Namespace) -> int:
    expression = _resolve_expression(arguments)
    if expression is None:
        return 1
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
        result = cdp.evaluate(root, expression)
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
  web-view eval --js-file ./find-media.js --frame index_lms
  echo "document.title" | web-view eval --js -
  cat ./find-media.js | web-view eval --js - --frame index_lms

The expression comes from exactly one source: `--js "<expr>"` inline,
`--js -` to read it from stdin, or `--js-file <path>` to read it from a
file (`--js` and `--js-file` are mutually exclusive). Multi-line scripts
are easier to keep in a file or pipe in than to quote inline.

The result is printed to stdout as JSON. A result that cannot be serialised
to JSON prints a structured error to stderr and exits 1. `--frame` targets a
frame (index, URL substring, or 'auto'; default 'auto', the top frame).
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "eval",
        help="run a JS expression in a tab/frame and print the result as JSON",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--js",
        dest="javascript_expression",
        help="JavaScript expression to evaluate; pass '-' to read it from stdin",
    )
    source.add_argument(
        "--js-file",
        dest="javascript_file",
        help="read the JavaScript expression from a file (mutually exclusive with --js)",
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
