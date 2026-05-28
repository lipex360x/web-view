"""Screenshots, ARIA snapshots, HTML inspection.

`dual_snapshot` is the canonical capture: PNG (what the user sees) +
ARIA YAML (what Playwright can query against) under the same numeric
prefix. `next_index` keeps the sequence monotonic per destination
directory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ._shared import locator_by_role


def screenshot(page: Any, destination: Path, *, full_page: bool = True) -> Path:
    """Save a PNG screenshot of `page` to `destination`. Returns `destination`."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(destination), full_page=full_page)
    return destination


def aria_snapshot(page: Any, destination: Path | None = None) -> str:
    """Return Playwright's ARIA snapshot (YAML). Optionally write to `destination`."""
    text = page.aria_snapshot()
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text + "\n", encoding="utf-8")
    return text


def next_index(destination_dir: Path) -> int:
    """Return the next numeric prefix to use for files in `destination_dir`."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    used: list[int] = []
    for entry in destination_dir.iterdir():
        match = re.match(r"^(\d+)-", entry.name)
        if match:
            used.append(int(match.group(1)))
    return (max(used) + 1) if used else 1


def dual_snapshot(
    page: Any,
    slug: str,
    *,
    dest_dir: Path,
    index: int | None = None,
) -> tuple[Path, Path]:
    """Canonical snapshot: save NN-<slug>.png + NN-<slug>.aria.yaml.

    The PNG captures what the user sees; the ARIA YAML captures the role/name
    tree Playwright queries against — together they form a reproducible record
    of "where we were", suitable for human review, selector authoring, and
    regression diffing.

    Returns (png_path, aria_path). `index` auto-assigned if None.
    """
    safe_slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    if not safe_slug:
        raise ValueError("slug must contain at least one alphanumeric char")
    resolved_index = next_index(dest_dir) if index is None else index
    png_path = dest_dir / f"{resolved_index:02d}-{safe_slug}.png"
    aria_path = dest_dir / f"{resolved_index:02d}-{safe_slug}.aria.yaml"
    screenshot(page, png_path)
    aria_snapshot(page, aria_path)
    return png_path, aria_path


def get_html(page: Any, *, locator: Any = None) -> str:
    """Return full-page HTML, or the outer HTML of a specific locator."""
    if locator is None:
        return page.content()
    return locator.evaluate("element => element.outerHTML")


def inspect_element(
    page: Any,
    role: str,
    name: str,
    *,
    exact: bool = True,
) -> dict[str, Any]:
    """Return a structured snapshot of a single element: html, attrs, bbox."""
    locator = locator_by_role(page, role, name, exact=exact)
    locator.wait_for(state="attached", timeout=5000)
    return {
        "outer_html": locator.evaluate("e => e.outerHTML"),
        "tag": locator.evaluate("e => e.tagName.toLowerCase()"),
        "id": locator.evaluate("e => e.id || null"),
        "classes": locator.evaluate("e => Array.from(e.classList)"),
        "attrs": locator.evaluate(
            "e => Object.fromEntries(Array.from(e.attributes).map(a => [a.name, a.value]))"
        ),
        "bounding_box": locator.bounding_box(),
        "is_visible": locator.is_visible(),
        "is_enabled": locator.is_enabled(),
    }
