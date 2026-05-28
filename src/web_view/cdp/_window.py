"""Window-level operations: OS-window resize and page-viewport overrides.

Two helpers, two different mental models:

  set_window_size(page, width=W, height=H)
    Resizes the OS-level Chrome window using CDP `Browser.setWindowBounds`.
    The user sees the window physically shrink/grow on their desktop.
    Persists at the browser instance level until the window is manually
    resized or the browser restarts.

  set_viewport(page, width=W, height=H)
    Overrides the page-rendering viewport via Playwright's
    `page.set_viewport_size`. Does not touch the OS window — only the
    canvas the page draws on. Persists per-page until the document
    reloads.
"""

from __future__ import annotations

from typing import Any


def set_window_size(page: Any, *, width: int, height: int) -> None:
    """Resize the OS Chrome window the given page lives in.

    Sends `Browser.getWindowForTarget` followed by `Browser.setWindowBounds`
    through a short-lived CDP session attached to `page`.
    """
    cdp_session = page.context.new_cdp_session(page)
    try:
        window_info = cdp_session.send("Browser.getWindowForTarget")
        window_identifier = window_info["windowId"]
        cdp_session.send(
            "Browser.setWindowBounds",
            {
                "windowId": window_identifier,
                "bounds": {"width": width, "height": height},
            },
        )
    finally:
        cdp_session.detach()


def set_viewport(page: Any, *, width: int, height: int) -> None:
    """Override the rendering viewport size for `page` (Playwright)."""
    page.set_viewport_size({"width": width, "height": height})
