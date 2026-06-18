"""Helpers shared by every `web-view tab <verb>` subcommand."""

from __future__ import annotations

import argparse


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach `--port` and `--quiet` (shared by every tab verb)."""
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="CDP port (optional when exactly one CDP Chrome is running)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="suppress the success ack on stdout",
    )


def is_index_selector(selector: str | None) -> bool:
    """True when `selector` addresses a tab by 0-based index (negatives allowed)."""
    if selector is None:
        return False
    candidate = selector[1:] if selector.startswith("-") else selector
    return candidate.isdigit()
