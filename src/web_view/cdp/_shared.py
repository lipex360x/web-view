"""Helpers reused by multiple modules of the `cdp` package.

Centralises three small reuse points:

  * `poll_localhost_json` — the one-shot probe used by `is_cdp_ready` and
    `wait_for_chrome_stopped` to ask `http://localhost:<port>/json/version`
    whether Chrome is currently listening.
  * `locator_by_role` / `wait_locator` — the locator + `wait_for(state=…)`
    pair shared by every element-interaction helper (`click`, `fill`,
    `hover`, …) and by `inspect_element`.
  * `ensure_storage_kind` — the `kind in {"local", "session"}` guard used
    by every storage helper.
"""

from __future__ import annotations

import http.client
import re
from typing import Any

STORAGE_KINDS: tuple[str, str] = ("local", "session")


def poll_localhost_json(port: int, *, request_timeout_s: float = 1.0) -> bool:
    """One probe of `http://localhost:<port>/json/version`.

    Returns True when the endpoint responds with a successful status,
    False on any failure. Uses `http.client` directly (no URL parsing)
    so the connection is locked to plain HTTP on localhost. Callers layer
    the polling loop on top of this primitive.
    """
    connection = http.client.HTTPConnection("localhost", port, timeout=request_timeout_s)
    try:
        connection.request("GET", "/json/version")
        response = connection.getresponse()
        response.read()
        return response.status == http.client.OK
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def locator_by_role(root: Any, role: str, name: Any, *, exact: bool) -> Any:
    """Resolve a Playwright locator by accessible role + name.

    `name` can be a string (matched literally — `exact` controls the mode)
    or a compiled regex (Playwright handles regex natively; the `exact`
    flag is irrelevant in that branch).
    """
    if isinstance(name, re.Pattern):
        return root.get_by_role(role, name=name)
    return root.get_by_role(role, name=name, exact=exact)


def wait_locator(
    root: Any,
    role: str,
    name: Any,
    *,
    exact: bool,
    timeout_s: float,
    state: str = "visible",
) -> Any:
    """Resolve a locator and wait for it to reach `state`. Returns the locator."""
    locator = locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state=state, timeout=int(timeout_s * 1000))
    return locator


def ensure_storage_kind(kind: str) -> None:
    """Validate the `kind` arg used by `get_storage` / `set_storage_item` / `clear_storage`."""
    if kind not in STORAGE_KINDS:
        raise ValueError(f"kind must be one of {STORAGE_KINDS!r}")
