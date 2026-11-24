from __future__ import annotations

from typing import Any

import pytest

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def test_unique_selector_focuses_the_only_match(fake_cdp: dict[str, Any]) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    target = make_fake_page(page_url="https://example.test/target")
    fake_cdp["pages"] = [make_fake_page(page_url="https://other.test"), target]
    assert main(["tab", "switch", "--tab", "unique:example.test"]) == 0
    assert target.bring_to_front_calls == [True]


@pytest.mark.parametrize("selector", ["unique:missing", "unique:example.test", "unique:"])
def test_unique_selector_never_focuses_on_invalid_match(
    fake_cdp: dict[str, Any], capsys: Any, selector: str
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    pages = [
        make_fake_page(page_url="https://example.test/one"),
        make_fake_page(page_url="https://example.test/two"),
    ]
    fake_cdp["pages"] = pages
    assert main(["tab", "switch", "--tab", selector]) == 1
    assert all(not page.bring_to_front_calls for page in pages)
    error = capsys.readouterr().err.lower()
    assert "unique" in error
    if selector == "unique:example.test":
        assert "ambiguous" in error
    if selector == "unique:":
        assert "nonempty" in error
