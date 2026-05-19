"""web-view — thin CLI around the `cdp` toolkit.

Exposes the most common operations (start a Chrome with CDP, list
running instances, stop them, snapshot a page) so the package is useful
out of the box. For programmatic flows, import `web_view.cdp` directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import cdp


def _print_instances() -> None:
    instances = cdp.list_cdp_instances()
    if not instances:
        print("(no CDP Chrome instances)")
        return
    print(f"{'PID':>7}  {'PORT':>5}  USER_DATA_DIR")
    for instance in instances:
        print(f"{instance.pid:>7}  {instance.port:>5}  {instance.user_data_dir or '-'}")


def _cmd_start(args: argparse.Namespace) -> int:
    user_data = Path(args.user_data_dir).expanduser().resolve()
    user_data.mkdir(parents=True, exist_ok=True)
    process = cdp.start_chrome(
        port=args.port,
        user_data_dir=str(user_data),
        headless=args.headless,
    )
    print(f"Chrome started: pid={process.pid} port={args.port}")
    print(f"CDP URL: http://localhost:{args.port}")
    print(f"Profile: {user_data}")
    return 0


def _cmd_list(_: argparse.Namespace) -> int:
    _print_instances()
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    killed = cdp.stop_chrome(port=args.port)
    print(f"stopped {killed} process(es) on port {args.port}")
    return 0


def _cmd_snap(args: argparse.Namespace) -> int:
    destination_dir = Path(args.destination_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    with cdp.connect(port=args.port) as (_, context):
        page = cdp.find_page(context, url_contains=args.url_contains)
        if page is None:
            print(f"no tab containing {args.url_contains!r}", file=sys.stderr)
            return 1
        png_path, aria_path = cdp.dual_snapshot(
            page, args.slug, destination_dir=destination_dir
        )
        print(f"saved {png_path} + {aria_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="web-view",
        description="Drive Chrome over CDP. Library: `from web_view import cdp`.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="launch a CDP Chrome on a port")
    start.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT)
    start.add_argument(
        "--user-data-dir",
        default="~/.cache/web-view/profile",
        help="persistent Chrome profile dir (defaults to ~/.cache/web-view/profile)",
    )
    start.add_argument("--headless", action="store_true")
    start.set_defaults(func=_cmd_start)

    listing = sub.add_parser("list", help="list running CDP Chrome instances")
    listing.set_defaults(func=_cmd_list)

    stop = sub.add_parser("stop", help="stop the CDP Chrome on a port")
    stop.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT)
    stop.set_defaults(func=_cmd_stop)

    snap = sub.add_parser("snap", help="dual snapshot (PNG + ARIA YAML) of a tab")
    snap.add_argument("slug", help="snapshot name (kebab-case)")
    snap.add_argument(
        "--port", type=int, default=cdp.DEFAULT_CDP_PORT, help="CDP port"
    )
    snap.add_argument(
        "--url-contains",
        default="",
        help="substring to pick the tab (defaults to first non-helper tab)",
    )
    snap.add_argument(
        "--destination-dir",
        default="./captures",
        help="where to save NN-<slug>.png + NN-<slug>.aria.yaml",
    )
    snap.set_defaults(func=_cmd_snap)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
