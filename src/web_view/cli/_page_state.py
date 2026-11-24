"""Report concise state for the selected document."""

from __future__ import annotations

import argparse
import json
import sys

from playwright.sync_api import Error as PlaywrightError

from .. import cdp
from ._shared import connected_tab

_MAX_TEXT_LIMIT = 10000
_SCRIPT = """limit => ({
    url: location.href,
    title: document.title,
    readyState: document.readyState,
    ...(limit > 0 ? {text: (document.body?.innerText ?? '').slice(0, limit)} : {})
})"""


def _text_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("text limit must be a non-negative integer") from error
    if limit < 0 or limit > _MAX_TEXT_LIMIT:
        raise argparse.ArgumentTypeError("text limit must be between 0 and 10000")
    return limit


def handle(arguments: argparse.Namespace) -> int:
    try:
        with connected_tab(arguments.port, arguments.tab) as page:
            if page is None:
                return 1
            result = cdp.evaluate(page, _SCRIPT, arguments.text_limit)
    except PlaywrightError as error:
        print(f"error: could not read page state: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "state",
        help="report selected page URL, title, and document readiness as JSON",
        description="Read document readiness, which does not guarantee the application is ready.",
    )
    parser.add_argument("--port", type=int, default=None, help="CDP port")
    parser.add_argument(
        "--tab", default=None, help="tab index, URL substring, or unique:<substring>"
    )
    parser.add_argument(
        "--text-limit",
        type=_text_limit,
        default=0,
        metavar="N",
        help="include at most N visible text characters (0-10000; default: omit text)",
    )
    parser.set_defaults(func=handle)
