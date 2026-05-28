"""`web-view list` — show running CDP Chrome instances and their tabs."""

from __future__ import annotations

import argparse

from .. import cdp


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


def handle(_: argparse.Namespace) -> int:
    _print_instances()
    return 0


EPILOG = """\
Output columns: PID, PORT, USER_DATA_DIR, TABS (count + tree of URLs/titles).
TABS shows `?` when the instance is up but the tabs can't be enumerated
(e.g. CDP busy or auth-gated); the rest of the row still prints.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "list",
        help="list running CDP Chrome instances",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=handle)
