"""Helpers shared by multiple `web-view` subcommands."""

from __future__ import annotations

import sys
from typing import Any

from .. import cdp


def _parse_tab_index(selector: str) -> int | None:
    candidate = selector[1:] if selector.startswith("-") else selector
    if candidate.isdigit():
        return int(selector)
    return None


def resolve_target_tab(context: Any, selector: str | None) -> Any:
    """Pick the tab a tab-bound command should target.

    Selector forms (matching `web-view navigate --tab`):
      - `None` (default)   → first non-helper tab, falling back to `pages[0]`
      - integer string     → 0-based index (negatives count from the end)
      - any other string   → URL substring; first match wins

    Returns `None` if the selector cannot be resolved against the open tabs.
    """
    if selector is None:
        page = cdp.find_page(context, url_contains="")
        if page is not None:
            return page
        return context.pages[0] if context.pages else None
    index = _parse_tab_index(selector)
    if index is not None:
        if not context.pages:
            return None
        try:
            return context.pages[index]
        except IndexError:
            return None
    return cdp.find_page(context, url_contains=selector)


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
