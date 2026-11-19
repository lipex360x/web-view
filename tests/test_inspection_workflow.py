from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from web_view import cdp
from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def test_evaluate_passes_a_structured_argument() -> None:
    calls: list[tuple[str, object]] = []
    root = SimpleNamespace(
        evaluate=lambda expression, argument: calls.append((expression, argument))
    )
    cdp.evaluate(root, "argument => argument", {"name": "field"})
    assert calls == [("argument => argument", {"name": "field"})]


def test_eval_passes_json_argument(fake_cdp: dict[str, Any]) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test")]
    assert main(["eval", "--js", "argument => argument", "--argument", '{"name":"field"}']) == 0
    assert fake_cdp["evaluate_calls"][0]["argument"] == {"name": "field"}


def test_eval_rejects_invalid_json_before_connecting(fake_cdp: dict[str, Any]) -> None:
    assert main(["eval", "--js", "argument => argument", "--argument", "{"]) == 1
    assert fake_cdp["evaluate_calls"] == []


def test_unique_tab_rejects_ambiguous_match(fake_cdp: dict[str, Any], capsys: Any) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [
        make_fake_page(page_url="https://example.test/first"),
        make_fake_page(page_url="https://example.test/second"),
    ]
    assert main(["eval", "--tab", "unique:example.test", "--js", "document.title"]) == 1
    assert fake_cdp["evaluate_calls"] == []
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_unique_tab_selects_only_match(fake_cdp: dict[str, Any]) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    target = make_fake_page(
        page_url="https://example.test/target", aria_text="- text: selected target"
    )
    fake_cdp["pages"] = [make_fake_page(page_url="https://other.test"), target]
    assert main(["eval", "--tab", "unique:example.test", "--js", "document.title"]) == 0
    assert fake_cdp["evaluate_calls"][0]["root"] is target


def test_snap_supports_tab_selector(fake_cdp: dict[str, Any], tmp_path: Any) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    target = make_fake_page(
        page_url="https://example.test/target", aria_text="- text: selected target"
    )
    fake_cdp["pages"] = [make_fake_page(page_url="https://other.test"), target]
    assert (
        main(["snap", "check", "--tab", "unique:example.test", "--destination-dir", str(tmp_path)])
        == 0
    )
    assert "selected target" in (tmp_path / "01-check.aria.yaml").read_text()
