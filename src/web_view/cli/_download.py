"""`web-view download` — fetch a URL through the browser and save it to disk."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import cdp
from ._shared import resolve_single_port


def _is_success(status: int) -> bool:
    return 200 <= status < 300


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    destination = Path(arguments.output_path).expanduser().resolve()
    with cdp.connect(port=target_port) as (_, context):
        result = cdp.download_resource(context, arguments.source_url, destination)
    print(f"status: {result['status']}")
    print(f"bytes: {result['bytes']}")
    if not _is_success(result["status"]):
        print(f"error: download failed with HTTP status {result['status']}", file=sys.stderr)
        return 1
    return 0


EPILOG = """\
Examples:
  web-view download --url "https://host/path/clip.mp4" --out /tmp/clip.mp4
  web-view download --url "https://host/report.pdf" --out ./report.pdf

The request goes through the browser context, so the logged-in session's
cookies are reused and a resource behind a login is reachable. The HTTP
status and saved byte count are printed to stdout; a non-2xx status prints
an error to stderr and exits 1.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "download",
        help="fetch a URL through the browser (reusing cookies) and save it",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        dest="source_url",
        required=True,
        help="URL of the resource to download",
    )
    parser.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="path to save the downloaded resource",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="CDP port (optional when exactly one CDP Chrome is running)",
    )
    parser.set_defaults(func=handle)
