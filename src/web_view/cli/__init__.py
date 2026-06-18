"""web-view — thin CLI around the `cdp` toolkit.

Exposes the most common operations (start a Chrome with CDP, list running
instances, stop them, load a URL in a tab, snapshot a page). Each subcommand
lives in its own module under this package; this module wires them together
into a single `argparse` parser.
"""

from __future__ import annotations

import argparse
import sys

from . import _do, _list, _navigate, _resize, _snap, _start, _stop, _tab

DESCRIPTION = "Drive Chrome over CDP. Run 'web-view <command> -h' for details."

EPILOG = """\
Library mode (programmatic use):
  from web_view import cdp
  `uv tool install` is CLI-only — for the library, install with:
    uv add git+https://github.com/lipex360x/web-view
    uv run --with git+https://github.com/lipex360x/web-view python my_script.py
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="web-view",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    _start.register(subparsers)
    _list.register(subparsers)
    _stop.register(subparsers)
    _navigate.register(subparsers)
    _snap.register(subparsers)
    _do.register(subparsers)
    _resize.register(subparsers)
    _tab.register(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    return int(arguments.func(arguments))


if __name__ == "__main__":
    sys.exit(main())
