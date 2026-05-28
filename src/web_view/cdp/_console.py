"""Browser console capture.

`console_recorder(page)` is a context manager that subscribes to the page's
`console` event during the `with` block and yields a `ConsoleRecorder`
whose `events` list grows as messages arrive.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsoleEvent:
    type: str
    text: str
    location: str


@dataclass
class ConsoleRecorder:
    events: list[ConsoleEvent] = field(default_factory=list)

    def by_type(self, *types: str) -> list[ConsoleEvent]:
        return [event for event in self.events if event.type in types]

    @property
    def errors(self) -> list[ConsoleEvent]:
        return self.by_type("error")


def _format_location(message: Any) -> str:
    location = message.location or {}
    return (
        f"{location.get('url', '')}:"
        f"{location.get('lineNumber', '')}:"
        f"{location.get('columnNumber', '')}"
    )


@contextlib.contextmanager
def console_recorder(page: Any) -> Iterator[ConsoleRecorder]:
    """Capture every `console.*` event during the `with` block."""
    recorder = ConsoleRecorder()

    def handler(message: Any) -> None:
        recorder.events.append(
            ConsoleEvent(
                type=message.type,
                text=message.text,
                location=_format_location(message),
            )
        )

    page.on("console", handler)
    try:
        yield recorder
    finally:
        page.remove_listener("console", handler)
