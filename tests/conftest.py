from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from web_view import cdp as cdp_module


@dataclass
class FakeInstance:
    pid: int
    port: int
    user_data_dir: str | None = None
    cmdline: str = ""


def make_fake_page(*, page_url: str = "", page_title: str = "") -> SimpleNamespace:
    return SimpleNamespace(**{"url": page_url, "title": lambda: page_title})


class FakeContext:
    def __init__(self, pages: list[SimpleNamespace]) -> None:
        self.pages = pages


def _make_list_instances(state: dict[str, Any]) -> Any:
    def fake_list_instances() -> list[FakeInstance]:
        return list(state["instances"])

    return fake_list_instances


def _make_stop_chrome(state: dict[str, Any]) -> Any:
    def fake_stop_chrome(*, port: int) -> int:
        state["stopped"].append(port)
        return sum(1 for instance in state["instances"] if instance.port == port)

    return fake_stop_chrome


def _make_start_chrome(state: dict[str, Any]) -> Any:
    def fake_start_chrome(*, port: int, user_data_dir: str | Path, headless: bool = False) -> Any:
        state["started"] = {
            "port": port,
            "user_data_dir": str(user_data_dir),
            "headless": headless,
        }
        return SimpleNamespace(pid=12345)

    return fake_start_chrome


def _make_connect(state: dict[str, Any]) -> Any:
    @contextlib.contextmanager
    def fake_connect(*, port: int) -> Iterator[tuple[Any, FakeContext]]:
        if state["connect_raises"] is not None:
            raise state["connect_raises"]
        yield None, FakeContext(list(state["pages"]))

    return fake_connect


def _make_find_page() -> Any:
    def fake_find_page(context: FakeContext, *, url_contains: str = "") -> SimpleNamespace | None:
        for page in context.pages:
            if url_contains in page.url:
                return page
        return None

    return fake_find_page


def _make_dual_snapshot(state: dict[str, Any]) -> Any:
    def fake_dual_snapshot(page: SimpleNamespace, slug: str, **kwargs: Any) -> tuple[Path, Path]:
        destination_dir = kwargs["dest_dir"]
        index = len(state["snapshots"]) + 1
        prefix = f"{index:02d}-{slug}"
        png_path = destination_dir / f"{prefix}.png"
        aria_path = destination_dir / f"{prefix}.aria.yaml"
        png_path.write_bytes(b"fake-png")
        aria_path.write_text("fake-aria")
        state["snapshots"].append((png_path, aria_path))
        return png_path, aria_path

    return fake_dual_snapshot


def _make_pages_info() -> Any:
    def fake_pages_info(context: FakeContext) -> list[dict[str, str]]:
        return [{"url": page.url, "title": page.title()} for page in context.pages]

    return fake_pages_info


def _make_is_cdp_ready(state: dict[str, Any]) -> Any:
    def fake_is_cdp_ready(port: int, *, timeout_s: int = 15) -> bool:
        return bool(state["ready"])

    return fake_is_cdp_ready


def _make_goto(state: dict[str, Any]) -> Any:
    def fake_goto(page: SimpleNamespace, target_url: str, **_: Any) -> None:
        state["goto_calls"].append((page, target_url))

    return fake_goto


def _make_open_tab(state: dict[str, Any]) -> Any:
    def fake_open_tab(context: FakeContext, target_url: str, **_: Any) -> SimpleNamespace:
        new_page = make_fake_page(page_url=target_url, page_title="")
        context.pages.append(new_page)
        state["open_tab_calls"].append((context, target_url))
        return new_page

    return fake_open_tab


@pytest.fixture
def fake_cdp(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {
        "instances": [],
        "pages": [],
        "stopped": [],
        "started": None,
        "goto_calls": [],
        "open_tab_calls": [],
        "snapshots": [],
        "connect_raises": None,
        "ready": True,
    }
    monkeypatch.setattr(cdp_module, "list_cdp_instances", _make_list_instances(state))
    monkeypatch.setattr(cdp_module, "stop_chrome", _make_stop_chrome(state))
    monkeypatch.setattr(cdp_module, "start_chrome", _make_start_chrome(state))
    monkeypatch.setattr(cdp_module, "connect", _make_connect(state))
    monkeypatch.setattr(cdp_module, "find_page", _make_find_page())
    monkeypatch.setattr(cdp_module, "dual_snapshot", _make_dual_snapshot(state))
    monkeypatch.setattr(cdp_module, "pages_info", _make_pages_info())
    monkeypatch.setattr(cdp_module, "is_cdp_ready", _make_is_cdp_ready(state))
    monkeypatch.setattr(cdp_module, "goto", _make_goto(state))
    monkeypatch.setattr(cdp_module, "open_tab", _make_open_tab(state))
    return state
