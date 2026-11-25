from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from web_view.cli import _perf
from web_view.cli._perf import _OBSERVER, _REPORT, _capture


@pytest.fixture
def capture_target() -> tuple[MagicMock, MagicMock]:
    page = MagicMock()
    session = page.context.new_cdp_session.return_value
    session.send.return_value = {"identifier": "script"}
    return page, session


def test_capture_sorts_resources_and_detaches(
    capture_target: tuple[MagicMock, MagicMock],
) -> None:
    page, session = capture_target
    page.evaluate.return_value = {"metrics": {"lcp": None, "cls": 0}}
    slow = MagicMock(url="http://localhost/slow.png", resource_type="image", method="GET")
    slow.timing = {"startTime": 10, "responseEnd": 200}
    fast = MagicMock(url="http://localhost/api", resource_type="fetch", method="GET")
    fast.timing = {"startTime": 10, "responseEnd": 20}
    page.goto.side_effect = lambda *args, **kwargs: [
        page.on.call_args.args[1](item) for item in (fast, slow)
    ]
    arguments = argparse.Namespace(url="http://localhost/", reload=False, timeout=3, trace=None)
    report = _capture(page, arguments)
    assert [item["url"] for item in report["resources"]] == [slow.url, fast.url]
    assert report["metrics"] == {"lcp": None, "cls": 0}
    assert session.send.call_args_list[0].args[0] == "Page.enable"
    assert session.send.call_args_list[1].args[0] == "Page.addScriptToEvaluateOnNewDocument"
    page.remove_listener.assert_called_once()
    session.detach.assert_called_once()
    assert any(call.args[0] == "Runtime.evaluate" for call in session.send.call_args_list)


def test_capture_detaches_on_timeout(capture_target: tuple[MagicMock, MagicMock]) -> None:
    page, session = capture_target
    page.reload.side_effect = PlaywrightTimeoutError("timeout")
    arguments = argparse.Namespace(url=None, reload=True, timeout=1, trace="trace.json")
    with pytest.raises(PlaywrightTimeoutError):
        _capture(page, arguments)
    page.remove_listener.assert_called_once()
    session.detach.assert_called_once()
    assert [call.args[0] for call in session.send.call_args_list[-3:]] == [
        "Tracing.end",
        "Page.removeScriptToEvaluateOnNewDocument",
        "Runtime.evaluate",
    ]
    assert session.send.call_args_list[-1].args[1]["timeout"] == 1000
    assert session.send.call_args_list[0].args[0] == "Page.enable"


@pytest.mark.parametrize("reload", [False, True])
def test_navigation_timeout_stops_loading_before_cleanup(
    reload: bool, capture_target: tuple[MagicMock, MagicMock]
) -> None:
    page, session = capture_target
    navigation = page.reload if reload else page.goto
    navigation.side_effect = PlaywrightTimeoutError("original navigation error")
    arguments = argparse.Namespace(
        url="http://localhost/", reload=reload, timeout=0.3, trace="trace.json"
    )
    with pytest.raises(PlaywrightTimeoutError, match="original navigation error"):
        _capture(page, arguments)
    methods = [call.args[0] for call in session.send.call_args_list]
    assert methods.index("Page.stopLoading") < methods.index("Tracing.end")
    assert methods.index("Page.stopLoading") < methods.index(
        "Page.removeScriptToEvaluateOnNewDocument"
    )
    session.detach.assert_called_once()


def test_stop_loading_failure_preserves_navigation_timeout(
    capture_target: tuple[MagicMock, MagicMock],
) -> None:
    page, session = capture_target
    page.goto.side_effect = PlaywrightTimeoutError("original navigation error")
    session.send.side_effect = lambda method, *args: (
        (_ for _ in ()).throw(PlaywrightError("stop failed"))
        if method == "Page.stopLoading"
        else {"identifier": "script"}
    )
    arguments = argparse.Namespace(url="http://localhost/", reload=False, timeout=1, trace=None)
    with pytest.raises(PlaywrightTimeoutError, match="original navigation error"):
        _capture(page, arguments)
    assert "Page.removeScriptToEvaluateOnNewDocument" in [
        call.args[0] for call in session.send.call_args_list
    ]
    session.detach.assert_called_once()


def test_report_timeout_does_not_stop_navigation(
    capture_target: tuple[MagicMock, MagicMock],
) -> None:
    page, session = capture_target
    page.evaluate.side_effect = PlaywrightTimeoutError("report timeout")
    arguments = argparse.Namespace(url="http://localhost/", reload=False, timeout=1, trace=None)
    with pytest.raises(PlaywrightTimeoutError, match="report timeout"):
        _capture(page, arguments)
    assert "Page.stopLoading" not in [call.args[0] for call in session.send.call_args_list]


def test_cleanup_disconnects_observers_and_releases_entries() -> None:
    executable = shutil.which("node")
    if not executable:
        pytest.skip("Node.js is unavailable")
    script = f"""
      global.window = global;
      global.observers = [];
      global.PerformanceObserver = class {{
        static supportedEntryTypes = ['largest-contentful-paint', 'layout-shift'];
        constructor(callback) {{ this.callback = callback; this.disconnected = false; }}
        observe() {{ global.observers.push(this); }}
        disconnect() {{ this.disconnected = true; }}
      }};
      {_OBSERVER};
      const metrics = window.__webViewMetrics;
      observers[0].callback({{getEntries: () => [{{startTime: 1}}]}});
      {_perf._CLEANUP};
      console.log(JSON.stringify({{
        disconnected: observers.every(observer => observer.disconnected),
        released: !window.__webViewMetrics &&
          metrics['largest-contentful-paint'].entries.length === 0
      }}));
    """
    result = subprocess.run([executable, "-e", script], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == {"disconnected": True, "released": True}


@pytest.mark.parametrize("error_type", [PlaywrightTimeoutError, PlaywrightError])
def test_cleanup_failure_preserves_navigation_error(
    error_type: type[PlaywrightError], capture_target: tuple[MagicMock, MagicMock]
) -> None:
    page, session = capture_target
    session.send.side_effect = lambda method, *args: (
        {"identifier": "script"}
        if method.startswith("Page.")
        else (_ for _ in ()).throw(PlaywrightTimeoutError("context disappeared"))
    )
    session.detach.side_effect = PlaywrightTimeoutError("tab disappeared")
    page.reload.side_effect = error_type("original navigation error")
    arguments = argparse.Namespace(url=None, reload=True, timeout=1, trace=None)
    with pytest.raises(error_type, match="original navigation error"):
        _capture(page, arguments)
    session.detach.assert_called_once()


def run_observations(setup: str, observations: str) -> dict[str, object]:
    executable = shutil.which("node")
    if not executable:
        pytest.skip("Node.js is unavailable")
    script = f"""
      global.window = global;
      global.location = {{href: 'http://localhost/'}};
      global.performance = {{getEntriesByType: () => [{{loadEventEnd: 100}}]}};
      {setup}
      {_OBSERVER};
      {observations}
      console.log(JSON.stringify(({_REPORT})().metrics));
    """
    result = subprocess.run([executable, "-e", script], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_metrics_use_supported_entries_through_load() -> None:
    metrics = run_observations(
        """global.observers = {};
        global.PerformanceObserver = class {
          static supportedEntryTypes = ['largest-contentful-paint', 'layout-shift'];
          constructor(callback) { this.callback = callback; }
          observe(options) { global.observers[options.type] = this; }
          takeRecords() { return this.pending || []; }
        };""",
        """const paint = global.observers['largest-contentful-paint'];
        paint.callback({getEntries: () => [{startTime: 80}, {startTime: 110}]});
        const shift = global.observers['layout-shift'];
        shift.callback({getEntries: () => [
          {startTime: 50, value: 0.1, hadRecentInput: false},
          {startTime: 60, value: 0.5, hadRecentInput: true},
          {startTime: 120, value: 0.8, hadRecentInput: false}
        ]});
        shift.pending = [{startTime: 90, value: 0.2, hadRecentInput: false}];""",
    )
    assert metrics["lcp"] == 80
    assert metrics["cls"] == pytest.approx(0.3)


def test_unsupported_layout_shift_is_null() -> None:
    metrics = run_observations(
        """global.PerformanceObserver = class {
          static supportedEntryTypes = [];
          observe() {}
        };""",
        "",
    )
    assert metrics == {"lcp": None, "cls": None}
