from __future__ import annotations

import json
from typing import Any

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def test_inspect_targets_region_and_selected_frame(fake_cdp: dict[str, Any], capsys: Any) -> None:
    outer = make_fake_page(page_url="https://example.test")
    inner = make_fake_page(page_url="https://example.test/frame")
    outer.frames = [outer, inner]
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [outer]
    fake_cdp["evaluate_result"] = {"links": [{"text": "Next", "href": "https://example.test/next"}]}
    assert main(["inspect", "--selector", "#main", "--links", "--frame", "1"]) == 0
    call = fake_cdp["evaluate_calls"][0]
    assert call["root"] is inner
    assert call["argument"] == {"selector": "#main", "kinds": ["links"]}
    assert json.loads(capsys.readouterr().out)["links"][0]["text"] == "Next"


def test_inspect_reports_selector_error(fake_cdp: dict[str, Any], capsys: Any) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test")]
    fake_cdp["evaluate_result"] = {"error": "No element matched selector: #missing"}
    assert main(["inspect", "--selector", "#missing"]) == 1
    assert "No element matched" in capsys.readouterr().err
