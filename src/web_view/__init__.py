"""web-view — reusable CDP / Playwright toolkit for driving Chrome.

Re-exports everything from `cdp` at the package root, so callers can write
either of:

    from web_view import cdp
    cdp.click(page, "button", "Submit")

or

    import web_view as cdp
    cdp.click(page, "button", "Submit")
"""

from . import cdp as cdp  # noqa: PLC0414

__all__ = ["cdp"]
