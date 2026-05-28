"""Element interaction: click, fill, hover, drag, keyboard, etc.

Every helper here resolves a locator by accessible role + name, waits for
it to reach a usable state, then performs the action. The locator +
wait pair lives in `_shared.wait_locator` so each helper here is a
two-liner.
"""

from __future__ import annotations

from typing import Any

from ._shared import locator_by_role, wait_locator


def click(
    root: Any,
    role: str,
    name: Any,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Click the element with accessible role + name.

    `root` may be a Page or a Locator (use a Locator to scope to a region).
    `name` may be a string (matched exactly when `exact=True`) or a regex.
    """
    locator = wait_locator(root, role, name, exact=exact, timeout_s=timeout_s)
    locator.click()


def fill(
    root: Any,
    role: str,
    name: Any,
    value: str,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Fill the input with accessible role + name. Clears existing content first."""
    locator = wait_locator(root, role, name, exact=exact, timeout_s=timeout_s)
    locator.fill(value)


def check(
    root: Any,
    role: str,
    name: Any,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Tick a checkbox / radio / switch with accessible name. Idempotent."""
    locator = wait_locator(root, role, name, exact=exact, timeout_s=timeout_s)
    if not locator.is_checked():
        locator.check()


def press(page: Any, *keys: str) -> None:
    """Send keyboard key(s). Single key or chord, e.g. press(page, "Control+a")."""
    for key in keys:
        page.keyboard.press(key)


def scroll_into_view(root: Any, role: str, name: str, *, exact: bool = True) -> None:
    locator = locator_by_role(root, role, name, exact=exact)
    locator.scroll_into_view_if_needed()


def hover(
    root: Any,
    role: str,
    name: str,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    locator = wait_locator(root, role, name, exact=exact, timeout_s=timeout_s)
    locator.hover()


def dblclick(
    root: Any,
    role: str,
    name: str,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    locator = wait_locator(root, role, name, exact=exact, timeout_s=timeout_s)
    locator.dblclick()


def right_click(
    root: Any,
    role: str,
    name: str,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    locator = wait_locator(root, role, name, exact=exact, timeout_s=timeout_s)
    locator.click(button="right")


def drag(
    page: Any,
    *,
    source: tuple[str, str],
    target: tuple[str, str],
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Drag the source element onto the target. Both as (role, name) pairs."""
    source_locator = wait_locator(page, source[0], source[1], exact=exact, timeout_s=timeout_s)
    target_locator = wait_locator(page, target[0], target[1], exact=exact, timeout_s=timeout_s)
    source_locator.drag_to(target_locator)
