from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from web_view import cdp
from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def prepare_page(fake_cdp: dict[str, Any]) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test")]


@pytest.mark.parametrize("verb", ["click", "fill", "drag"])
def test_action_help_explains_debug_and_unique_selector(capsys: Any, verb: str) -> None:
    with pytest.raises(SystemExit) as result:
        main(["do", verb, "--help"])
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "--debug" in output and "unique:" in output


def test_missing_target_reports_concise_timeout(
    fake_cdp: dict[str, Any], capsys: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp)

    def fail(*arguments: Any, **_keywords: Any) -> None:
        raise PlaywrightTimeoutError(
            "Locator.wait_for: Timeout 1000ms exceeded.\nCall log: details"
        )

    monkeypatch.setattr(cdp, "click", fail)
    assert main(["do", "click", "--role", "button", "--name", "Missing", "--timeout", "1"]) == 1
    output = capsys.readouterr().err
    assert "timeout" in output.lower() and "Missing" in output and "1s" in output
    assert "Traceback" not in output and "Call log" not in output


def test_timeout_debug_preserves_exception(
    fake_cdp: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp)

    def fail(*arguments: Any, **_keywords: Any) -> None:
        raise PlaywrightTimeoutError("detailed timeout")

    monkeypatch.setattr(cdp, "click", fail)
    with pytest.raises(PlaywrightTimeoutError, match="detailed timeout"):
        main(["do", "--debug", "click", "--role", "button", "--name", "Missing"])


def test_unexpected_errors_are_not_hidden(
    fake_cdp: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp)

    def fail(*arguments: Any, **_keywords: Any) -> None:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(cdp, "click", fail)
    with pytest.raises(RuntimeError, match="unexpected failure"):
        main(["do", "click", "--role", "button", "--name", "Missing"])


def test_ambiguous_selection_does_not_run_action(fake_cdp: dict[str, Any], capsys: Any) -> None:
    prepare_page(fake_cdp)
    fake_cdp["pages"].append(make_fake_page(page_url="https://example.test/another"))
    assert (
        main(
            ["do", "click", "--role", "button", "--name", "Missing", "--tab", "unique:example.test"]
        )
        == 1
    )
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_drag_timeout_identifies_both_endpoints(
    fake_cdp: dict[str, Any], capsys: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp)

    def fail(*arguments: Any, **_keywords: Any) -> None:
        raise PlaywrightTimeoutError("Locator.drag_to: Timeout exceeded")

    monkeypatch.setattr(cdp, "drag", fail)
    assert (
        main(["do", "drag", "--from", "button:Source", "--to", "region:Target", "--timeout", "1"])
        == 1
    )
    output = capsys.readouterr().err
    assert "Source" in output and "Target" in output and "1s" in output
    assert "Traceback" not in output
