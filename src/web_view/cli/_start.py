"""`web-view start` — launch a CDP-enabled Chrome on a port."""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import cdp


def _parse_window_size(raw: str) -> tuple[int, int]:
    """argparse `type=` callable: parses 'WxH' into (width, height)."""
    parts = raw.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"--window-size expects WxH (e.g. 1280x720); got {raw!r}")
    try:
        width = int(parts[0])
        height = int(parts[1])
    except ValueError as exception:
        raise argparse.ArgumentTypeError(
            f"--window-size expects WxH integers (e.g. 1280x720); got {raw!r}"
        ) from exception
    return (width, height)


def _navigate_first_tab(port: int, target_url: str) -> None:
    with cdp.connect(port=port) as (_, context):
        page = cdp.find_page(context, url_contains="")
        if page is None:
            page = context.pages[0] if context.pages else None
        if page is None:
            return
        cdp.goto(page, target_url)


def handle(arguments: argparse.Namespace) -> int:
    user_data_dir = Path(arguments.user_data_dir).expanduser().resolve()
    user_data_dir.mkdir(parents=True, exist_ok=True)
    process = cdp.start_chrome(
        port=arguments.port,
        user_data_dir=str(user_data_dir),
        headless=arguments.headless,
        window_size=arguments.window_size,
    )
    print(f"Chrome started: pid={process.pid} port={arguments.port}")
    print(f"CDP URL: http://localhost:{arguments.port}")
    print(f"Profile: {user_data_dir}")
    if arguments.url:
        _navigate_first_tab(arguments.port, arguments.url)
    return 0


EPILOG = """\
Examples:
  web-view start
  web-view start --port 9333
  web-view start --url file:///path/to/index.html
  web-view start --headless --url https://example.com
  web-view start --window-size 1280x720

The first tab loads `about:blank` unless `--url` is given. Chrome runs
detached and keeps running after this command exits — stop it with
`web-view stop`. `--window-size` accepts `WxH` (default 1920x1080). Use
`web-view resize` to change the window size of a running instance.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "start",
        help="launch a CDP Chrome on a port",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT)
    parser.add_argument(
        "--user-data-dir",
        default="~/.cache/web-view/profile",
        help="persistent Chrome profile dir (defaults to ~/.cache/web-view/profile)",
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--url",
        default=None,
        help="optional initial URL to load in the first tab",
    )
    parser.add_argument(
        "--window-size",
        type=_parse_window_size,
        default=(1920, 1080),
        help="initial window size as WxH (default 1920x1080)",
    )
    parser.set_defaults(func=handle)
