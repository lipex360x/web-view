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
