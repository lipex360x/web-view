"""Browser-side state: cookies, web storage, clipboard."""

from __future__ import annotations

from typing import Any

from ._shared import ensure_storage_kind


def get_cookies(context: Any, *, urls: list[str] | None = None) -> list[dict[str, Any]]:
    """Return the context's cookies, optionally filtered to `urls`."""
    if urls:
        return list(context.cookies(urls))
    return list(context.cookies())


def set_cookie(
    context: Any,
    *,
    name: str,
    value: str,
    target_url: str | None = None,
    domain: str | None = None,
    path: str = "/",
    expires: float | None = None,
    http_only: bool = False,
    secure: bool = False,
    same_site: str | None = None,
) -> None:
    """Add a single cookie. Either `target_url` or (`domain` + `path`) must be set."""
    cookie: dict[str, Any] = {"name": name, "value": value, "path": path}
    if target_url is not None:
        cookie["url"] = target_url
    if domain is not None:
        cookie["domain"] = domain
    if expires is not None:
        cookie["expires"] = expires
    if http_only:
        cookie["httpOnly"] = True
    if secure:
        cookie["secure"] = True
    if same_site is not None:
        cookie["sameSite"] = same_site
    context.add_cookies([cookie])


def clear_cookies(context: Any) -> None:
    context.clear_cookies()


def get_storage(page: Any, *, kind: str = "local") -> dict[str, str]:
    """Dump localStorage (kind='local') or sessionStorage (kind='session')."""
    ensure_storage_kind(kind)
    store = f"{kind}Storage"
    return page.evaluate(
        f"() => {{ const out = {{}}; for (let i = 0; i < {store}.length; i++) "
        f"{{ const k = {store}.key(i); out[k] = {store}.getItem(k); }} return out; }}"
    )


def set_storage_item(page: Any, key: str, value: str, *, kind: str = "local") -> None:
    ensure_storage_kind(kind)
    page.evaluate(
        f"([k, v]) => {kind}Storage.setItem(k, v)",
        [key, value],
    )


def clear_storage(page: Any, *, kind: str = "local") -> None:
    ensure_storage_kind(kind)
    page.evaluate(f"() => {kind}Storage.clear()")


def read_clipboard(page: Any) -> str:
    """Read the OS clipboard from the page context.

    Requires `clipboard-read` permission on the BrowserContext.
    """
    return page.evaluate("() => navigator.clipboard.readText()")


def write_clipboard(page: Any, text: str) -> None:
    """Write `text` to the OS clipboard from the page context."""
    page.evaluate("(t) => navigator.clipboard.writeText(t)", text)
