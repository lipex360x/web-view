"""Helpers shared by every `web-view do <verb>` subcommand."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

from ... import cdp
from .._shared import (
    print_no_frame_found,
    print_no_tab_found,
    resolve_single_port,
    resolve_target_frame,
    resolve_target_tab,
)

DEFAULT_TIMEOUT_SECONDS = 15.0


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach `--port`, `--tab`, `--timeout`, `--quiet` (shared by every verb)."""
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
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="upper bound in seconds for waiting on the element (default 15)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="suppress the success ack on stdout",
    )


def add_addressing_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach `--role`, `--name`, `--selector` for addressing the target element."""
    parser.add_argument("--role", help="ARIA role of the target element")
    parser.add_argument("--name", help="accessible name of the target element")
    parser.add_argument(
        "--selector",
        help="CSS selector (mutually exclusive with --role/--name)",
    )


def resolve_addressing(arguments: argparse.Namespace) -> tuple[str, str] | str | None:
    """Validate addressing flags and return either (role, name) or a CSS selector.

    Returns None and prints a structured error when the user passed both forms
    or neither.
    """
    if arguments.selector is not None:
        if arguments.role is not None or arguments.name is not None:
            print(
                "error: --selector is mutually exclusive with --role/--name",
                file=sys.stderr,
            )
            return None
        return arguments.selector
    if arguments.role is None or arguments.name is None:
        print(
            "error: must specify --role + --name (or --selector)",
            file=sys.stderr,
        )
        return None
    return (arguments.role, arguments.name)


def print_ack(verb: str, addressing: tuple[str, str] | str, *, quiet: bool) -> None:
    """Print the one-line success ack on stdout unless `--quiet` was set."""
    if quiet:
        return
    if isinstance(addressing, tuple):
        role, name = addressing
        print(f'{verb}: {role} "{name}"')
        return
    print(f'{verb}: selector="{addressing}"')


PerformAction = Callable[[Any, tuple[str, str] | str, argparse.Namespace], None]


def addressing_probe(addressing: tuple[str, str] | str) -> Callable[[Any], bool]:
    """Build the cheap, non-waiting presence check used by `--frame auto`.

    Returns a predicate that counts matches of `addressing` on a candidate
    root via Playwright's `.count()` (which never waits), so resolving the
    winning frame does not multiply `--timeout` across frames.
    """

    def probe(root: Any) -> bool:
        if isinstance(addressing, tuple):
            role, name = addressing
            return root.get_by_role(role, name=name, exact=True).count() > 0
        return root.locator(addressing).count() > 0

    return probe


def run_addressed_verb(
    arguments: argparse.Namespace,
    *,
    verb: str,
    perform_action: PerformAction,
) -> int:
    """Boilerplate for every addressed interaction verb.

    Resolves addressing → port → tab → frame → action → ack. Verb-specific
    work (translating addressing into a `cdp.*` call or a raw locator action)
    lives in `perform_action`, which receives the resolved frame as its root.
    """
    addressing = resolve_addressing(arguments)
    if addressing is None:
        return 1
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    with cdp.connect(port=target_port) as (_, context):
        page = resolve_target_tab(context, arguments.tab)
        if page is None:
            print_no_tab_found(arguments.tab or "")
            return 1
        root = resolve_target_frame(page, arguments.frame, probe=addressing_probe(addressing))
        if root is None:
            print_no_frame_found(arguments.frame)
            return 1
        perform_action(root, addressing, arguments)
        print_ack(verb, addressing, quiet=arguments.quiet)
    return 0
