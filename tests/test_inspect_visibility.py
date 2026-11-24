from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import sync_playwright

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def test_visibility_targets_selected_tab_and_bounded_matches(
    fake_cdp: dict[str, Any], capsys: Any
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test")]
    expected = {"visibility": [{"tag": "button", "text": "Hidden"}], "total": 2, "truncated": True}
    fake_cdp["evaluate_result"] = expected
    assert main(["inspect", "--selector", "button", "--visibility", "--limit", "1"]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert fake_cdp["evaluate_calls"][0]["argument"] == {
        "selector": "button",
        "kinds": ["visibility"],
        "limit": 1,
    }


@pytest.mark.parametrize("limit", ["0", "-1", "101", "invalid"])
def test_visibility_rejects_invalid_limit(limit: str) -> None:
    with pytest.raises(SystemExit):
        main(["inspect", "--visibility", "--limit", limit])


def test_visibility_evidence_in_real_browser() -> None:
    from web_view.cli._inspect import _SCRIPT

    with sync_playwright() as playwright:
        executable = os.environ.get("WEB_VIEW_TEST_CHROME", playwright.chromium.executable_path)
        if not Path(executable).is_file():
            pytest.skip("Chrome is unavailable; set WEB_VIEW_TEST_CHROME to its executable")
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
        try:
            page = browser.new_page()
            page.set_content(
                "<button>Visible</button><button hidden>Hidden</button>"
                "<div style='display:none'><button>Ancestor</button></div>"
                "<button style='visibility:hidden'>CSS</button>"
            )
            result: Any = page.evaluate(
                _SCRIPT, {"selector": "button", "kinds": ["visibility"], "limit": 4}
            )
            assert result["total"] == 4 and not result["truncated"]
            visible, hidden, ancestor, css = result["visibility"]
            assert visible["text"] == "Visible" and visible["rendered"]
            assert not hidden["rendered"] and hidden["hidden_attribute"]
            assert not ancestor["rendered"] and any(
                item["display"] == "none" for item in ancestor["ancestors"]
            )
            assert not css["rendered"] and css["visibility"] == "hidden"
            limited: Any = page.evaluate(
                _SCRIPT, {"selector": "button", "kinds": ["visibility"], "limit": 1}
            )
            assert (
                limited["total"] == 4 and limited["truncated"] and len(limited["visibility"]) == 1
            )
            missing: Any = page.evaluate(
                _SCRIPT, {"selector": ".missing", "kinds": ["visibility"], "limit": 1}
            )
            assert "error" in missing
            page.set_content("<textarea>private value</textarea>")
            field: Any = page.evaluate(
                _SCRIPT, {"selector": "textarea", "kinds": ["visibility"], "limit": 1}
            )
            assert field["visibility"][0]["text"] is None
        finally:
            browser.close()
