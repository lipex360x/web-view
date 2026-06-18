"""Downloads and uploads — file movement to/from the browser."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ._shared import wait_locator


def capture_download(
    page: Any,
    action: Callable[[], None],
    *,
    destination: Path | None = None,
    timeout_s: float = 30,
) -> Path:
    """Run `action()`, capture any download it triggers, save to `destination`.

    If `destination` is None, the download is saved to a temp path with the
    suggested filename. Returns the final saved path.
    """
    with page.expect_download(timeout=int(timeout_s * 1000)) as download_info:
        action()
    download = download_info.value
    if destination is None:
        from tempfile import gettempdir

        destination = Path(gettempdir()) / download.suggested_filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(str(destination))
    return destination


def upload(
    page: Any,
    role: str,
    name: str,
    file_paths: str | Path | list[str | Path],
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Attach one or more files to an input[type=file] element."""
    locator = wait_locator(page, role, name, exact=exact, timeout_s=timeout_s, state="attached")
    raw_paths = file_paths if isinstance(file_paths, list) else [file_paths]
    locator.set_input_files([str(path) for path in raw_paths])


def download_resource(context: Any, source_url: str, destination: Path) -> dict[str, Any]:
    """Fetch `source_url` through the browser context and save it to `destination`.

    Uses `context.request.get`, so the browser's auth cookies are reused and a
    resource behind a login is reachable without re-authenticating. Writes the
    response body to `destination` and returns `{"status", "bytes"}`. The caller
    decides what a non-2xx status means.
    """
    response = context.request.get(source_url)
    body = response.body()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(body)
    return {"status": response.status, "bytes": len(body)}
