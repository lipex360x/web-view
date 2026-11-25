"""Capture a single navigation and optional Chrome performance trace."""

from __future__ import annotations

import argparse
import json
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ._shared import connected_tab

_OBSERVER = """(() => {
  const metrics = window.__webViewMetrics = {};
  for (const type of ['largest-contentful-paint', 'layout-shift']) {
    if (!PerformanceObserver.supportedEntryTypes?.includes(type)) continue;
    try {
      const entries = [];
      const observer = new PerformanceObserver(list => entries.push(...list.getEntries()));
      observer.observe({type, buffered: true});
      metrics[type] = {observer, entries};
    } catch (_) {}
  }
})()"""
_CLEANUP = """(() => {
  const metrics = window.__webViewMetrics;
  if (!metrics) return;
  for (const observation of Object.values(metrics)) {
    observation.observer.disconnect();
    observation.entries.length = 0;
  }
  delete window.__webViewMetrics;
})()"""
_REPORT = """() => {
  const navigation = performance.getEntriesByType('navigation')[0];
  const observations = window.__webViewMetrics ?? {};
  const throughLoad = type => {
    const observation = observations[type];
    if (!observation || !navigation || !navigation.loadEventEnd) return null;
    return observation.entries.concat(observation.observer.takeRecords())
      .filter(entry => entry.startTime <= navigation.loadEventEnd);
  };
  const paints = throughLoad('largest-contentful-paint');
  const shifts = throughLoad('layout-shift');
  let cls = shifts ? 0 : null, windowStart = null, lastShift = 0, windowValue = 0;
  for (const entry of shifts ?? []) {
    if (entry.hadRecentInput) continue;
    if (windowStart === null || entry.startTime - lastShift > 1000 ||
        entry.startTime - windowStart > 5000) {
      windowStart = entry.startTime; windowValue = 0;
    }
    lastShift = entry.startTime; windowValue += entry.value;
    cls = Math.max(cls, windowValue);
  }
  return {
    url: location.href,
    navigation: navigation ? {
      time_to_first_byte_ms: navigation.responseStart,
      dom_content_loaded_ms: navigation.domContentLoadedEventEnd,
      load_ms: navigation.loadEventEnd
    } : null,
    metrics: {lcp: paints?.length ? paints[paints.length - 1].startTime : null, cls}
  };
}"""


def _positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be a positive number") from error
    if not 0 < timeout < float("inf"):
        raise argparse.ArgumentTypeError("timeout must be a positive number")
    return timeout


def _resource(request: Any) -> dict[str, Any]:
    timing = request.timing
    start = timing["startTime"]
    end = timing["responseEnd"]
    return {
        "url": request.url,
        "type": request.resource_type,
        "method": request.method,
        "duration_ms": end if end >= 0 and start >= 0 else None,
    }


def _finish_trace(session: Any, page: Any, destination: str) -> None:
    events: list[Any] = []
    complete = {"done": False}
    session.on("Tracing.dataCollected", lambda event: events.extend(event["value"]))
    session.on("Tracing.tracingComplete", lambda event: complete.update(done=True))
    session.send("Tracing.end")
    deadline = time.monotonic() + 10
    while not complete["done"] and time.monotonic() < deadline:
        session.send("Runtime.evaluate", {"expression": "0"})
    if not complete["done"]:
        raise RuntimeError("timed out while collecting the trace")
    Path(destination).write_text(json.dumps({"traceEvents": events}), encoding="utf-8")


def _capture(page: Any, arguments: argparse.Namespace) -> dict[str, Any]:
    session = page.context.new_cdp_session(page)
    requests: list[dict[str, Any]] = []

    def listener(request: Any) -> None:
        requests.append(_resource(request))

    script = None
    tracing = False
    try:
        session.send("Page.enable")
        script = session.send("Page.addScriptToEvaluateOnNewDocument", {"source": _OBSERVER})
        page.on("requestfinished", listener)
        if arguments.trace:
            session.send(
                "Tracing.start",
                {
                    "categories": (
                        "devtools.timeline,blink.user_timing,loading,v8.execute,"
                        "disabled-by-default-devtools.timeline"
                    ),
                    "transferMode": "ReportEvents",
                },
            )
            tracing = True
        try:
            if arguments.reload:
                page.reload(wait_until="load", timeout=arguments.timeout * 1000)
            else:
                page.goto(arguments.url, wait_until="load", timeout=arguments.timeout * 1000)
        except PlaywrightTimeoutError:
            with suppress(PlaywrightError):
                session.send("Page.stopLoading")
            raise
        page.evaluate("() => new Promise(resolve => setTimeout(resolve, 0))")
        report = cast(dict[str, Any], page.evaluate(_REPORT))
        report["resources"] = sorted(
            requests, key=lambda item: item["duration_ms"] or 0, reverse=True
        )
        if tracing:
            tracing = False
            _finish_trace(session, page, arguments.trace)
        return report
    finally:
        with suppress(PlaywrightError):
            page.remove_listener("requestfinished", listener)
        with suppress(PlaywrightError):
            if tracing:
                session.send("Tracing.end")
        if script:
            with suppress(PlaywrightError):
                session.send(
                    "Page.removeScriptToEvaluateOnNewDocument",
                    {"identifier": script["identifier"]},
                )
            with suppress(PlaywrightError):
                session.send("Runtime.evaluate", {"expression": _CLEANUP, "timeout": 1000})
        with suppress(PlaywrightError):
            session.detach()


def handle(arguments: argparse.Namespace) -> int:
    try:
        with connected_tab(arguments.port, arguments.tab) as page:
            if page is None:
                return 1
            report = _capture(page, arguments)
    except PlaywrightTimeoutError:
        print(f"error: navigation timed out after {arguments.timeout:g} seconds", file=sys.stderr)
        return 1
    except (PlaywrightError, OSError, RuntimeError) as error:
        print(f"error: performance capture failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "perf",
        help="capture a page navigation performance report as JSON",
        description=(
            "Capture until the load event. Metrics describe this single local run "
            "and its observed window."
        ),
    )
    navigation = parser.add_mutually_exclusive_group(required=True)
    navigation.add_argument("--url", help="URL to navigate to")
    navigation.add_argument("--reload", action="store_true", help="reload the selected tab")
    parser.add_argument("--port", type=int, default=None, help="CDP port")
    parser.add_argument(
        "--tab", default=None, help="tab index, URL substring, or unique:<substring>"
    )
    parser.add_argument(
        "--timeout",
        type=_positive_timeout,
        default=30,
        help="navigation timeout in seconds; stops selected tab loading on timeout (default: 30)",
    )
    parser.add_argument("--trace", help="write a Chrome DevTools Performance trace to this file")
    parser.set_defaults(func=handle)
