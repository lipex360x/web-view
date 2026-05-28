"""cdp — reusable helpers for driving a Chrome instance over CDP.

Designed to be project-agnostic: nothing here knows about a specific site
or vendor. Higher layers compose these into flow-specific scripts.

================================================================================
GOLDEN RULE: WAIT FOR STATE CHANGES, NEVER FOR TIME
================================================================================

If you're tempted to write `page.wait_for_timeout(ms)`, `time.sleep(seconds)`,
or any fixed-duration delay anywhere in code that uses this library — STOP.
Express the actual state change you're waiting for:

    BAD:                                  GOOD:
    page.wait_for_timeout(5000)           page.locator("h1").wait_for(state="visible")
    time.sleep(2); click_next()           cdp.wait_for_url(page, predicate, timeout_s=30)
    sleep(N) hoping content renders       page.wait_for_load_state("load"|"domcontentloaded")
    poll url with sleep                   page.wait_for_url(predicate)
    sleep(N) hoping network finishes      cdp.network_recorder + wait on the request

Fixed waits are simultaneously too slow (you wait full duration even when ready
in ms) AND too fragile (you guess "enough time" and it breaks under load).

`timeout_s=N` on cdp.* helpers is an UPPER BOUND for protection, not a delay —
the call returns the instant the state changes.

================================================================================
PACKAGE LAYOUT
================================================================================

  _lifecycle    start/stop Chrome, list running instances, CDP readiness
  _connection   open a CDP session, enumerate tabs, find/open/close tabs
  _navigation   goto, wait_for_url, back/forward/reload
  _interaction  click, fill, hover, drag, keyboard, scroll
  _files        capture_download, upload
  _state        cookies, localStorage/sessionStorage, clipboard
  _snapshots    screenshot, ARIA snapshot, dual_snapshot, inspect_element
  _console      console.* event capture
  _network      request/response capture, dump to JSON
  _shared       cross-module helpers (locator + wait, localhost JSON probe,
                storage kind validation)

================================================================================
CONVENTIONS
================================================================================

- Every function takes the Playwright object it needs (Page, BrowserContext)
  as the first positional argument — never reads global state.
- URLs are passed as strings; predicates as callables `(url: str) -> bool`.
- Timeouts are in seconds at this API boundary (Playwright uses ms internally;
  we convert).
- All snapshot/screenshot functions take a `destination` path and return it
  for chaining.
- Never trust `context.pages[0]` — Chrome via CDP exposes auxiliary targets
  (RotateCookies, service workers, devtools). Use `find_page(...)` with a
  `url_contains=` or `predicate=` to pick the right tab.
- A "snapshot" is a PAIR: `.png` (visual) + `.aria.yaml` (selectors). Always
  capture both via `dual_snapshot(page, slug, dest_dir=...)`.
- Element interaction helpers (click, fill, check, hover, …) accept either a
  Page or a Locator as the first arg.

================================================================================
TYPICAL USAGE
================================================================================

    from web_view import cdp

    with cdp.connect() as (browser, context):
        page = cdp.find_page(context, url_contains="example.com")
        cdp.goto(page, "https://example.com/form")
        page.locator("input[name=email]").wait_for(state="visible")
        cdp.fill(page, "textbox", "Email", "user@x.com")
        cdp.click(page, "button", "Submit")
        cdp.wait_for_url(page, lambda url: "/done" in url, timeout_s=30)
        cdp.dual_snapshot(page, "after-submit", dest_dir=Path("captures"))
"""

from __future__ import annotations

from ._connection import (
    close_tab,
    connect,
    find_page,
    open_tab,
    pages_info,
    switch_to_tab,
)
from ._console import ConsoleEvent, ConsoleRecorder, console_recorder
from ._files import capture_download, upload
from ._interaction import (
    check,
    click,
    dblclick,
    drag,
    fill,
    hover,
    press,
    right_click,
    scroll_into_view,
)
from ._lifecycle import (
    CDP_URL,
    DEFAULT_CDP_PORT,
    CdpInstance,
    is_cdp_ready,
    list_cdp_instances,
    start_chrome,
    stop_chrome,
    wait_for_chrome_stopped,
)
from ._navigation import back, forward, goto, reload, wait_for_url
from ._network import (
    NetworkEntry,
    NetworkRecorder,
    dump_network,
    network_recorder,
)
from ._snapshots import (
    aria_snapshot,
    dual_snapshot,
    get_html,
    inspect_element,
    next_index,
    screenshot,
)
from ._state import (
    clear_cookies,
    clear_storage,
    get_cookies,
    get_storage,
    read_clipboard,
    set_cookie,
    set_storage_item,
    write_clipboard,
)

__all__ = [
    "CDP_URL",
    "DEFAULT_CDP_PORT",
    "CdpInstance",
    "ConsoleEvent",
    "ConsoleRecorder",
    "NetworkEntry",
    "NetworkRecorder",
    "aria_snapshot",
    "back",
    "capture_download",
    "check",
    "clear_cookies",
    "clear_storage",
    "click",
    "close_tab",
    "connect",
    "console_recorder",
    "dblclick",
    "drag",
    "dual_snapshot",
    "dump_network",
    "fill",
    "find_page",
    "forward",
    "get_cookies",
    "get_html",
    "get_storage",
    "goto",
    "hover",
    "inspect_element",
    "is_cdp_ready",
    "list_cdp_instances",
    "network_recorder",
    "next_index",
    "open_tab",
    "pages_info",
    "press",
    "read_clipboard",
    "reload",
    "right_click",
    "screenshot",
    "scroll_into_view",
    "set_cookie",
    "set_storage_item",
    "start_chrome",
    "stop_chrome",
    "switch_to_tab",
    "upload",
    "wait_for_chrome_stopped",
    "wait_for_url",
    "write_clipboard",
]
