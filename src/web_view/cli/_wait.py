"""Wait for a URL or top-frame element condition on the selected tab."""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ._shared import connected_tab

_MAX_TIMEOUT_SECONDS = 86400
_MIN_TIMEOUT_SECONDS = 0.001


def _timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be a number of seconds") from error
    if not math.isfinite(seconds) or not _MIN_TIMEOUT_SECONDS <= seconds <= _MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError("timeout must be between 0.001 and 86400 seconds")
    return seconds


def _nonempty(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("target must not be empty")
    return value


def _wait_for_condition(page: Any, arguments: argparse.Namespace) -> None:
    timeout = int(arguments.timeout * 1000)
    if arguments.url_contains is not None:
        page.wait_for_url(
            lambda current: arguments.url_contains in current,
            timeout=timeout,
            wait_until="commit",
        )
        return
    locator = (
        page.locator(arguments.selector)
        if arguments.selector is not None
        else page.get_by_text(arguments.text, exact=False)
    )
    locator.first.wait_for(state=arguments.state or "visible", timeout=timeout)


def handle(arguments: argparse.Namespace) -> int:
    if arguments.url_contains is not None and arguments.state is not None:
        print("error: --state applies only to --selector or --text", file=sys.stderr)
        return 1
    try:
        with connected_tab(arguments.port, arguments.tab) as page:
            if page is None:
                return 1
            _wait_for_condition(page, arguments)
    except PlaywrightTimeoutError:
        print(
            f"timeout: condition was not satisfied within {arguments.timeout:g}s", file=sys.stderr
        )
        return 1
    except PlaywrightError as error:
        print(f"error: unable to wait for condition: {error}", file=sys.stderr)
        return 1
    print("condition satisfied")
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "wait",
        help="wait for a URL, element, or text condition on the selected tab",
        description=(
            "Wait on the selected tab's top frame. Text uses case-insensitive substring "
            "matching; URL matching is case-sensitive. The first element match is used; "
            "hidden also succeeds when it is absent. Navigation keeps the same tab."
        ),
    )
    condition = parser.add_mutually_exclusive_group(required=True)
    condition.add_argument("--url-contains", type=_nonempty, help="substring of the current URL")
    condition.add_argument("--selector", type=_nonempty, help="CSS selector for the first match")
    condition.add_argument("--text", type=_nonempty, help="text substring for the first match")
    parser.add_argument(
        "--state", choices=("visible", "hidden"), help="element state (default: visible)"
    )
    parser.add_argument(
        "--timeout", type=_timeout, default=15.0, help="timeout in seconds (default: 15)"
    )
    parser.add_argument("--port", type=int, default=None, help="CDP port")
    parser.add_argument(
        "--tab", default=None, help="tab index, URL substring, or unique:<substring>"
    )
    parser.set_defaults(func=handle)
