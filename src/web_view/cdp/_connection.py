"""CDP connections and tab management.

`connect` opens a Playwright session over the CDP URL and yields
`(browser, context)`. The remaining helpers all work against the
yielded `context`: `pages_info` for read-only enumeration, `find_page`
for locating one tab by URL, `open_tab`/`switch_to_tab`/`close_tab`
for the obvious lifecycle operations.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from typing import Any

from ._lifecycle import CDP_URL


@contextlib.contextmanager
def connect(
    cdp_url: str | None = None,
    *,
    port: int | None = None,
) -> Iterator[tuple[Any, Any]]:
    """Open a Playwright connection to a running Chrome.

    Priority for picking the target:
      1. `port=N` → `http://localhost:N`
      2. `cdp_url="http://host:port"` → explicit URL
      3. neither → CDP_URL default (port 9222).

    Yields `(browser, context)`. Use `find_page(context, …)` to pick a tab.
    Chrome keeps running after this context exits.
    """
    if port is not None:
        cdp_url = f"http://localhost:{port}"
    elif cdp_url is None:
        cdp_url = CDP_URL

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        if not browser.contexts:
            raise RuntimeError(f"no contexts on CDP at {cdp_url}")
        yield browser, browser.contexts[0]


def pages_info(context: Any) -> list[dict[str, str]]:
    """Return a list of `{url, title}` dicts for every page in the context."""
    entries: list[dict[str, str]] = []
    for page in context.pages:
        try:
            entries.append({"url": page.url, "title": page.title()})
        except Exception:
            entries.append({"url": getattr(page, "url", ""), "title": ""})
    return entries


def find_page(
    context: Any,
    *,
    url_contains: str | None = None,
    predicate: Callable[[str], bool] | None = None,
) -> Any:
    """Return the first page matching `url_contains` or `predicate`.

    If both are given, `predicate` wins. If neither matches, returns None.
    """
    if url_contains is None and predicate is None:
        raise ValueError("pass either url_contains or predicate")
    matcher = predicate or (lambda page_url: url_contains in page_url)
    for page in context.pages:
        with contextlib.suppress(Exception):
            if matcher(page.url):
                return page
    return None


def open_tab(
    context: Any,
    target_url: str,
    *,
    wait_until: str = "domcontentloaded",
) -> Any:
    """Open a new tab and navigate to `target_url`. Returns the new Page."""
    page = context.new_page()
    page.goto(target_url, wait_until=wait_until)
    return page


def switch_to_tab(context: Any, *, url_contains: str) -> Any:
    """Bring the tab whose URL contains `url_contains` to the front. Returns it."""
    page = find_page(context, url_contains=url_contains)
    if page is None:
        raise RuntimeError(f"no tab found with url containing {url_contains!r}")
    page.bring_to_front()
    return page


def close_tab(page: Any) -> None:
    page.close()
