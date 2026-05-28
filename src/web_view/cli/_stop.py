"""`web-view stop` — stop a running CDP Chrome instance."""

from __future__ import annotations

import argparse

from .. import cdp
from ._shared import resolve_single_port


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    killed = cdp.stop_chrome(port=target_port)
    print(f"stopped {killed} process(es) on port {target_port}")
    return 0


EPILOG = """\
Examples:
  web-view stop                  # stops the single running instance
  web-view stop --port 9333      # stops the instance on a specific port

`--port` is optional when exactly one CDP Chrome is running. With zero
instances, prints a hint pointing at `web-view start`. With two or more,
prints the candidate `--port` values and exits with a non-zero status.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "stop",
        help="stop a CDP Chrome instance",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=None)
    parser.set_defaults(func=handle)
