"""web-view — thin CLI around the `cdp` toolkit.

Exposes the most common operations (start a Chrome with CDP, list
running instances, stop them, snapshot a page) so the package is useful
out of the box. For programmatic flows, import `web_view.cdp` directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from . import cdp

DESCRIPTION = """Drive Chrome over CDP.

Common workflow:
  web-view start --port 9222 --url file:///path/to/index.html
  web-view snap my-page --port 9222
  web-view stop --port 9222

Library mode: `from web_view import cdp`. Requires the package in your
Python environment — `uv tool install` is CLI-only. Use one of:
  uv add git+https://github.com/lipex360x/web-view
  uv run --with git+https://github.com/lipex360x/web-view python my_script.py
"""


def _print_no_instance_on_port(port: int) -> None:
    print(
        f"No CDP Chrome instance on port {port}.\n"
        f"Start one with: web-view start --port {port}\n"
        "Check running instances: web-view list",
        file=sys.stderr,
    )


def _print_no_instances() -> None:
    print(
        "No CDP Chrome instances running.\nStart one with: web-view start",
        file=sys.stderr,
    )


def _print_ambiguous_instances(instances: list[Any]) -> None:
    lines = [f"{len(instances)} CDP Chrome instances running. Specify --port:"]
    for instance in instances:
        lines.append(f"  web-view stop --port {instance.port}")
    print("\n".join(lines), file=sys.stderr)


def _fetch_tab_info(port: int) -> list[dict[str, str]] | None:
    try:
        with cdp.connect(port=port) as (_, context):
            return cdp.pages_info(context)
    except Exception:
        return None


def _format_tab_line(tab: dict[str, str]) -> str:
    target_url = tab.get("url", "")
    title = tab.get("title", "")
    if title:
        return f'{target_url}  "{title}"'
    return target_url


def _print_instances() -> None:
    instances = cdp.list_cdp_instances()
    if not instances:
        print("(no CDP Chrome instances)")
        return
    print(f"{'PID':>7}  {'PORT':>5}  {'USER_DATA_DIR':<40}  TABS")
    for instance in instances:
        tabs = _fetch_tab_info(instance.port)
        tab_label = "?" if tabs is None else str(len(tabs))
        user_data_dir = instance.user_data_dir or "-"
        print(f"{instance.pid:>7}  {instance.port:>5}  {user_data_dir:<40}  {tab_label}")
        if tabs:
            last_index = len(tabs) - 1
            for index, tab in enumerate(tabs):
                connector = "└─" if index == last_index else "├─"
                print(f"{'':>57}  {connector} {_format_tab_line(tab)}")


def _navigate_first_tab(port: int, target_url: str) -> None:
    with cdp.connect(port=port) as (_, context):
        page = cdp.find_page(context, url_contains="")
        if page is None:
            page = context.pages[0] if context.pages else None
        if page is None:
            return
        cdp.goto(page, target_url)


def _handle_start(arguments: argparse.Namespace) -> int:
    user_data_dir = Path(arguments.user_data_dir).expanduser().resolve()
    user_data_dir.mkdir(parents=True, exist_ok=True)
    process = cdp.start_chrome(
        port=arguments.port,
        user_data_dir=str(user_data_dir),
        headless=arguments.headless,
    )
    print(f"Chrome started: pid={process.pid} port={arguments.port}")
    print(f"CDP URL: http://localhost:{arguments.port}")
    print(f"Profile: {user_data_dir}")
    if arguments.url:
        _navigate_first_tab(arguments.port, arguments.url)
    return 0


def _handle_list(_: argparse.Namespace) -> int:
    _print_instances()
    return 0


def _resolve_stop_port(explicit_port: int | None) -> int | None:
    if explicit_port is not None:
        instances = [
            instance for instance in cdp.list_cdp_instances() if instance.port == explicit_port
        ]
        if not instances:
            _print_no_instance_on_port(explicit_port)
            return None
        return explicit_port

    instances = cdp.list_cdp_instances()
    if not instances:
        _print_no_instances()
        return None
    if len(instances) > 1:
        _print_ambiguous_instances(instances)
        return None
    return instances[0].port


def _handle_stop(arguments: argparse.Namespace) -> int:
    target_port = _resolve_stop_port(arguments.port)
    if target_port is None:
        return 1
    killed = cdp.stop_chrome(port=target_port)
    print(f"stopped {killed} process(es) on port {target_port}")
    return 0


def _ensure_instance_on_port(port: int) -> bool:
    instances = cdp.list_cdp_instances()
    if not any(instance.port == port for instance in instances):
        _print_no_instance_on_port(port)
        return False
    return True


def _handle_snap(arguments: argparse.Namespace) -> int:
    if not _ensure_instance_on_port(arguments.port):
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="web-view",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="launch a CDP Chrome on a port")
    start.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT)
    start.add_argument(
        "--user-data-dir",
        default="~/.cache/web-view/profile",
        help="persistent Chrome profile dir (defaults to ~/.cache/web-view/profile)",
    )
    start.add_argument("--headless", action="store_true")
    start.add_argument(
        "--url",
        default=None,
        help="optional initial URL to load in the first tab",
    )
    start.set_defaults(func=_handle_start)

    listing = subparsers.add_parser("list", help="list running CDP Chrome instances")
    listing.set_defaults(func=_handle_list)

    stop = subparsers.add_parser("stop", help="stop a CDP Chrome instance")
    stop.add_argument("--port", type=int, default=None)
    stop.set_defaults(func=_handle_stop)

    snap = subparsers.add_parser("snap", help="dual snapshot (PNG + ARIA YAML) of a tab")
    snap.add_argument(
        "slug",
        nargs="?",
        default="snap",
        help="snapshot name (kebab-case); defaults to 'snap'",
    )
    snap.add_argument("--port", type=int, default=cdp.DEFAULT_CDP_PORT, help="CDP port")
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
    snap.set_defaults(func=_handle_snap)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    return int(arguments.func(arguments))


if __name__ == "__main__":
    sys.exit(main())
