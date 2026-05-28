"""Network request/response capture and persistence."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HTTP_ERROR_THRESHOLD = 400


@dataclass
class NetworkEntry:
    request_url: str
    method: str
    status: int | None = None
    status_text: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_post_data: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_mime: str = ""
    response_body: str | bytes | None = None
    response_json: Any = None
    error: str | None = None
    timing_ms: float | None = None

    def is_json(self) -> bool:
        return "application/json" in (self.response_mime or "")


@dataclass
class NetworkRecorder:
    entries: list[NetworkEntry] = field(default_factory=list)
    _by_request: dict[Any, NetworkEntry] = field(default_factory=dict)

    def filter(
        self,
        *,
        url_contains: str | None = None,
        status: int | None = None,
        method: str | None = None,
    ) -> list[NetworkEntry]:
        matches = self.entries
        if url_contains is not None:
            matches = [entry for entry in matches if url_contains in entry.request_url]
        if status is not None:
            matches = [entry for entry in matches if entry.status == status]
        if method is not None:
            matches = [entry for entry in matches if entry.method.upper() == method.upper()]
        return matches

    @property
    def failed(self) -> list[NetworkEntry]:
        return [
            entry
            for entry in self.entries
            if entry.error or (entry.status is not None and entry.status >= HTTP_ERROR_THRESHOLD)
        ]


def _decode_body(entry: NetworkEntry, body: bytes) -> None:
    if entry.is_json():
        try:
            entry.response_json = json.loads(body.decode("utf-8"))
        except Exception:
            entry.response_body = body
        return
    try:
        entry.response_body = body.decode("utf-8")
    except UnicodeDecodeError:
        entry.response_body = body


def _attach_response(entry: NetworkEntry, response: Any, *, capture_bodies: bool) -> None:
    entry.status = response.status
    entry.status_text = response.status_text
    entry.response_headers = dict(response.headers)
    mime_header = entry.response_headers.get("content-type", "")
    entry.response_mime = mime_header.split(";")[0].strip()
    if not capture_bodies:
        return
    try:
        body = response.body()
    except Exception as exception:
        entry.error = f"body fetch failed: {exception}"
        return
    _decode_body(entry, body)


@contextlib.contextmanager
def network_recorder(
    page: Any,
    *,
    url_predicate: Callable[[str], bool] | None = None,
    capture_bodies: bool = True,
) -> Iterator[NetworkRecorder]:
    """Capture every network request/response during the `with` block."""
    recorder = NetworkRecorder()
    predicate = url_predicate or (lambda _candidate_url: True)

    def on_request(request: Any) -> None:
        if not predicate(request.url):
            return
        entry = NetworkEntry(
            request_url=request.url,
            method=request.method,
            request_headers=dict(request.headers),
            request_post_data=request.post_data,
        )
        recorder._by_request[request] = entry
        recorder.entries.append(entry)

    def on_response(response: Any) -> None:
        entry = recorder._by_request.get(response.request)
        if entry is None:
            return
        try:
            _attach_response(entry, response, capture_bodies=capture_bodies)
        except Exception as exception:
            entry.error = f"response capture failed: {exception}"

    def on_request_failed(request: Any) -> None:
        entry = recorder._by_request.get(request)
        if entry is None:
            return
        entry.error = request.failure or "request failed"

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("requestfailed", on_request_failed)
    try:
        yield recorder
    finally:
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)
        page.remove_listener("requestfailed", on_request_failed)


def _serialise_body(entry: NetworkEntry) -> Any:
    if entry.response_json is not None:
        return entry.response_json
    if isinstance(entry.response_body, str):
        return entry.response_body
    if isinstance(entry.response_body, bytes):
        return f"<{len(entry.response_body)} bytes>"
    return None


def dump_network(recorder: NetworkRecorder, destination: Path) -> Path:
    """Persist a NetworkRecorder's entries to JSON for offline inspection."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialisable = [
        {
            "url": entry.request_url,
            "method": entry.method,
            "status": entry.status,
            "status_text": entry.status_text,
            "request_post_data": entry.request_post_data,
            "response_mime": entry.response_mime,
            "response_body": _serialise_body(entry),
            "error": entry.error,
        }
        for entry in recorder.entries
    ]
    destination.write_text(
        json.dumps(serialisable, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination
