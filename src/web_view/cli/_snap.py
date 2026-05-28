"""`web-view snap` — dual snapshot (PNG + ARIA YAML) of a tab."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import cdp
from ._shared import ensure_instance_on_port


def handle(arguments: argparse.Namespace) -> int:
    if not ensure_instance_on_port(arguments.port):
        return 1
    destination_dir = Path(arguments.destination_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    with cdp.connect(port=arguments.port) as (_, context):
        page = cdp.find_page(context, url_contains=arguments.url_contains)
        if page is None:
            print(f"no tab containing {arguments.url_contains!r}", file=sys.stderr)
            return 1
        png_path, aria_path = cdp.dual_snapshot(page, arguments.slug, dest_dir=destination_dir)
    print(str(png_path.resolve()))
    print(str(aria_path.resolve()))
    return 0


EPILOG = """\
Examples:
  web-view snap                              # auto-slug ("snap"), default port
  web-view snap homepage                     # explicit slug
  web-view snap login --url-contains login   # pick tab by URL substring
  web-view snap homepage --destination-dir ./captures

Output:
  Files are written as NN-<slug>.png + NN-<slug>.aria.yaml (NN is the
  next free integer in the destination dir). The two absolute paths are
  printed to stdout (PNG first, then ARIA YAML) so the command composes
  with `head`, `xargs`, etc.:

    web-view snap | head -1 | xargs open

If no port has a running CDP Chrome, prints a hint pointing at
`web-view start` and `web-view list` instead of a raw traceback.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "snap",
        help="dual snapshot (PNG + ARIA YAML) of a tab",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "slug",
        nargs="?",
        default="snap",
        help="snapshot name (kebab-case); defaults to 'snap'",
    )
    parser.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT, help="CDP port")
    parser.add_argument(
        "--url-contains",
        default="",
        help="substring to pick the tab (defaults to first non-helper tab)",
    )
    parser.add_argument(
        "--destination-dir",
        default="./captures",
        help="where to save NN-<slug>.png + NN-<slug>.aria.yaml",
    )
    parser.set_defaults(func=handle)
