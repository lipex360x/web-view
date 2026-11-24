from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from pathlib import Path
from threading import Thread
from typing import Any
from wsgiref.simple_server import make_server

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from web_view.cli._wait import _wait_for_condition


@pytest.fixture
def browser_page() -> Iterator[Any]:
    with sync_playwright() as playwright:
        executable = os.environ.get("WEB_VIEW_TEST_CHROME", playwright.chromium.executable_path)
        if not Path(executable).is_file():
            pytest.skip("Chrome is unavailable; set WEB_VIEW_TEST_CHROME to its executable")
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
        try:
            yield browser.new_page()
        finally:
            browser.close()


def arguments(**changes: Any) -> argparse.Namespace:
    values = {"timeout": 2.0, "url_contains": None, "selector": None, "text": None, "state": None}
    values.update(changes)
    return argparse.Namespace(**values)


def test_waits_for_text_changes_and_immediate_conditions(browser_page: Any) -> None:
    browser_page.set_content("<div id='status'>Loading</div>")
    _wait_for_condition(browser_page, arguments(text="Loading"))
    browser_page.evaluate(
        "setTimeout(() => document.querySelector('#status').textContent = 'Ready', 100)"
    )
    _wait_for_condition(browser_page, arguments(text="Loading", state="hidden"))
    _wait_for_condition(browser_page, arguments(text="Ready"))
    _wait_for_condition(browser_page, arguments(selector="#absent", state="hidden"))
    with pytest.raises(PlaywrightTimeoutError):
        _wait_for_condition(browser_page, arguments(text="Never", timeout=0.05))


def test_wait_stays_on_selected_page_during_navigation(browser_page: Any) -> None:
    def application(environment: Any, start_response: Any) -> list[bytes]:
        if environment["PATH_INFO"] == "/redirect":
            start_response("302 Found", [("Location", "/destination")])
            return [b""]
        start_response("200 OK", [("Content-Type", "text/html")])
        return [b"<div>Ready</div>"]

    server = make_server("127.0.0.1", 0, application)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        address = f"http://127.0.0.1:{server.server_port}"
        browser_page.goto(f"{address}/start")
        browser_page.evaluate("setTimeout(() => location.href = '/redirect', 100)")
        _wait_for_condition(browser_page, arguments(url_contains="/destination"))
        assert browser_page.url == f"{address}/destination"
        _wait_for_condition(browser_page, arguments(text="Ready"))
    finally:
        server.shutdown()
        server.server_close()
