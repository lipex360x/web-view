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


def _parse_frame_index(selector: str) -> int | None:
    candidate = selector[1:] if selector.startswith("-") else selector
    return int(selector) if candidate.isdigit() else None


def _auto_frame(page: Any, probe: Any) -> Any:
    frames = list(getattr(page, "frames", []))
    if not frames or probe is None:
        return page
    for root in [page, *frames]:
        if probe(root):
            return root
    return page


def resolve_target_frame(page: Any, selector: str | None, *, probe: Any = None) -> Any:
    """Pick the frame a frame-bound `do` verb should act on.

    Selector forms (mirroring `--tab`):
      - `None` / `"auto"`   → cheap-probe the page and every frame; first hit
        wins, falling back to the page when nothing matches.
      - integer string      → 0-based index into `page.frames` (0 is the top
        frame); negatives count from the end.
      - any other string    → URL substring; the first matching frame wins.

    Returns `None` when an explicit index or substring cannot be resolved, so
    the caller can print a structured error.
    """
    if selector is None or selector == "auto":
        return _auto_frame(page, probe)
    index = _parse_frame_index(selector)
    if index is not None:
        frames = list(getattr(page, "frames", []))
        try:
            return frames[index]
        except IndexError:
            return None
    for frame in getattr(page, "frames", []):
        if selector in frame.url:
            return frame
    return None


def print_no_frame_found(selector: str) -> None:
    print(
        f"No frame matched {selector!r}.\n"
        "Use an index (0-based, 0 is the top frame), a URL substring, or 'auto'.\n"
        "See the frame tree: web-view snap (iframes are inlined by default)",
        file=sys.stderr,
    )


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
