"""Run JavaScript in a page or frame and return the result."""

from __future__ import annotations

from typing import Any


def evaluate(root: Any, expression: str) -> Any:
    """Evaluate a JS expression in `root` (a Page or Frame) and return its value.

    `root` may be a Page or a Frame, so the same call reaches into an iframe
    when paired with the CLI's `--frame` resolver. The return value is whatever
    Playwright deserialises from the expression (JSON-compatible types).
    """
    return root.evaluate(expression)
