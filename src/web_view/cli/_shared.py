"""Helpers shared by multiple `web-view` subcommands."""

from __future__ import annotations

import sys
from typing import Any

from .. import cdp


def print_no_instance_on_port(port: int) -> None:
    print(
        f"No CDP Chrome instance on port {port}.\n"
        f"Start one with: web-view start --port {port}\n"
        "Check running instances: web-view list",
        file=sys.stderr,
    )


def print_no_instances() -> None:
    print(
        "No CDP Chrome instances running.\nStart one with: web-view start",
        file=sys.stderr,
    )


def print_ambiguous_instances(instances: list[Any]) -> None:
    lines = [f"{len(instances)} CDP Chrome instances running. Specify --port:"]
    for instance in instances:
        lines.append(f"  web-view stop --port {instance.port}")
    print("\n".join(lines), file=sys.stderr)


def print_no_tab_found(selector: str) -> None:
    print(
        f"No tab matched {selector!r}.\nSee open tabs: web-view list",
        file=sys.stderr,
    )


def ensure_instance_on_port(port: int) -> bool:
    instances = cdp.list_cdp_instances()
    if not any(instance.port == port for instance in instances):
        print_no_instance_on_port(port)
        return False
    return True
