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


def resolve_single_port(explicit_port: int | None) -> int | None:
    """Pick the port a port-bound command should target.

    If `explicit_port` is given, verify a CDP Chrome listens there and
    return it (or print a structured error and return None). With no
    explicit port: auto-resolve when exactly one instance is running;
    error out with port-list guidance when zero or 2+ are running.
    """
    if explicit_port is not None:
        instances = [
            instance for instance in cdp.list_cdp_instances() if instance.port == explicit_port
        ]
        if not instances:
            print_no_instance_on_port(explicit_port)
            return None
        return explicit_port

    instances = cdp.list_cdp_instances()
    if not instances:
        print_no_instances()
        return None
    if len(instances) > 1:
        print_ambiguous_instances(instances)
        return None
    return instances[0].port
