"""Run JavaScript in a page or frame and return the result."""

from __future__ import annotations

from typing import Any

_MISSING = object()


def evaluate(root: Any, expression: str, argument: Any = _MISSING) -> Any:
    """Evaluate a JS expression in `root` (a Page or Frame) and return its value.

    `root` may be a Page or a Frame, so the same call reaches into an iframe
    when paired with the CLI's `--frame` resolver. The return value is whatever
    Playwright deserialises from the expression (JSON-compatible types).
    """
    if argument is _MISSING:
        return root.evaluate(expression)
    return root.evaluate(expression, argument)
