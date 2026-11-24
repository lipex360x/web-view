from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def setup_page(fake_cdp: dict[str, Any]) -> Any:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    page = make_fake_page(page_url="https://example.test/start")
    fake_cdp["pages"] = [page]
    return page


def test_wait_url_matches_selected_page(fake_cdp: dict[str, Any], capsys: Any) -> None:
    page = setup_page(fake_cdp)
    page.wait_for_url = Mock()
    assert main(["wait", "--url-contains", "/ready", "--timeout", "2"]) == 0
    predicate = page.wait_for_url.call_args.args[0]
    assert predicate("https://example.test/ready")
    assert not predicate("https://example.test/starting")
    assert page.wait_for_url.call_args.kwargs == {"timeout": 2000, "wait_until": "commit"}
    assert "satisfied" in capsys.readouterr().out


@pytest.mark.parametrize("target", ["--selector", "--text"])
@pytest.mark.parametrize("visibility", ["visible", "hidden"])
def test_wait_element_visibility(fake_cdp: dict[str, Any], target: str, visibility: str) -> None:
    page = setup_page(fake_cdp)
    locator = Mock()
    locator.first = locator
    page.locator = Mock(return_value=locator)
    page.get_by_text = Mock(return_value=locator)
    assert main(["wait", target, "Loading", "--state", visibility]) == 0
    if target == "--selector":
        page.locator.assert_called_once_with("Loading")
    else:
        page.get_by_text.assert_called_once_with("Loading", exact=False)
    locator.wait_for.assert_called_once_with(state=visibility, timeout=15000)


@pytest.mark.parametrize(
    ("exception", "message"),
    [
        (PlaywrightTimeoutError("timeout"), "timeout"),
        (PlaywrightError("invalid selector"), "error"),
    ],
)
def test_wait_distinguishes_failure(
    fake_cdp: dict[str, Any], capsys: Any, exception: Exception, message: str
) -> None:
    page = setup_page(fake_cdp)
    page.locator = Mock(side_effect=exception)
    assert main(["wait", "--selector", "["]) == 1
    assert message in capsys.readouterr().err.lower()


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_wait_rejects_unbounded_timeout(timeout: str) -> None:
    with pytest.raises(SystemExit):
        main(["wait", "--text", "Ready", "--timeout", timeout])


def test_wait_rejects_ambiguous_tab(fake_cdp: dict[str, Any], capsys: Any) -> None:
    setup_page(fake_cdp)
    fake_cdp["pages"].append(make_fake_page(page_url="https://example.test/other"))
    assert main(["wait", "--text", "Ready", "--tab", "unique:example.test"]) == 1
    assert "ambiguous" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("target", ["--url-contains", "--selector", "--text"])
def test_wait_rejects_empty_target(target: str) -> None:
    with pytest.raises(SystemExit):
        main(["wait", target, " "])


def test_wait_rejects_element_state_for_url(capsys: Any) -> None:
    assert main(["wait", "--url-contains", "ready", "--state", "hidden"]) == 1
    assert "--state applies only" in capsys.readouterr().err
