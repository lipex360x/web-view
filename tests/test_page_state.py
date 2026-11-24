from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Error as PlaywrightError

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


@pytest.mark.parametrize("readiness", ["loading", "interactive", "complete"])
def test_page_state_reports_document_state(
    fake_cdp: dict[str, Any], capsys: Any, readiness: str
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test/final")]
    expected = {"url": "https://example.test/final", "title": "Example", "readyState": readiness}
    fake_cdp["evaluate_result"] = expected
    assert main(["state"]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert fake_cdp["evaluate_calls"][0]["argument"] == 0


def test_page_state_requests_bounded_optional_text(fake_cdp: dict[str, Any], capsys: Any) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test")]
    fake_cdp["evaluate_result"] = {
        "url": "https://example.test",
        "title": "",
        "readyState": "complete",
        "text": "Ready",
    }
    assert main(["state", "--text-limit", "5"]) == 0
    assert json.loads(capsys.readouterr().out)["text"] == "Ready"
    assert fake_cdp["evaluate_calls"][0]["argument"] == 5


def test_page_state_rejects_ambiguous_tab(fake_cdp: dict[str, Any], capsys: Any) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [
        make_fake_page(page_url="https://example.test/one"),
        make_fake_page(page_url="https://example.test/two"),
    ]
    assert main(["state", "--tab", "unique:example.test"]) == 1
    assert "ambiguous" in capsys.readouterr().err.lower()
    assert fake_cdp["evaluate_calls"] == []


@pytest.mark.parametrize("limit", ["-1", "10001", "invalid"])
def test_page_state_rejects_invalid_text_limit(fake_cdp: dict[str, Any], limit: str) -> None:
    with pytest.raises(SystemExit):
        main(["state", "--text-limit", limit])
    assert fake_cdp["evaluate_calls"] == []


def test_page_state_reports_navigation_error(
    fake_cdp: dict[str, Any], capsys: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from web_view import cdp

    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test")]

    def fail_evaluate(*arguments: Any) -> None:
        raise PlaywrightError("document changed during navigation")

    monkeypatch.setattr(cdp, "evaluate", fail_evaluate)
    assert main(["state"]) == 1
    assert "document changed during navigation" in capsys.readouterr().err
