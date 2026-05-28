"""Page-level navigation: load a URL, wait for one, walk history."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def goto(page: Any, target_url: str, *, wait_until: str = "domcontentloaded") -> None:
    """Navigate `page` to `target_url`. Thin wrapper that sets a sane default wait."""
    page.goto(target_url, wait_until=wait_until)


def wait_for_url(
    page: Any,
    predicate: Callable[[str], bool],
    *,
    timeout_s: float = 60,
) -> str:
    """Wait until `predicate(page.url)` is true. Event-driven (no polling).

    Returns the URL once matched. Raises on timeout.
    """
    page.wait_for_url(predicate, timeout=int(timeout_s * 1000))
    return page.url


def _navigate_history(
    page: Any,
    method_name: str,
    *,
    wait_until: str,
) -> None:
    getattr(page, method_name)(wait_until=wait_until)


def back(page: Any, *, wait_until: str = "domcontentloaded") -> None:
    _navigate_history(page, "go_back", wait_until=wait_until)


def forward(page: Any, *, wait_until: str = "domcontentloaded") -> None:
    _navigate_history(page, "go_forward", wait_until=wait_until)


def reload(page: Any, *, wait_until: str = "domcontentloaded") -> None:
    _navigate_history(page, "reload", wait_until=wait_until)
