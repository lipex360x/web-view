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


class FakeLocator:
    def __init__(self, selector: str, *, match_count: int = 0) -> None:
        self.selector = selector
        self.match_count = match_count
        self.actions: list[tuple[str, Any]] = []

    def count(self) -> int:
        return self.match_count

    def click(self, **arguments: Any) -> None:
        self.actions.append(("click", arguments))

    def fill(self, value: str, **arguments: Any) -> None:
        self.actions.append(("fill", {"value": value, **arguments}))

    def check(self, **arguments: Any) -> None:
        self.actions.append(("check", arguments))

    def is_checked(self) -> bool:
        return False

    def hover(self, **arguments: Any) -> None:
        self.actions.append(("hover", arguments))

    def dblclick(self, **arguments: Any) -> None:
        self.actions.append(("dblclick", arguments))

    def scroll_into_view_if_needed(self, **arguments: Any) -> None:
        self.actions.append(("scroll_into_view", arguments))

    def set_input_files(self, file_paths: Any, **arguments: Any) -> None:
        self.actions.append(("upload", {"file_paths": file_paths, **arguments}))

    def drag_to(self, target: Any, **arguments: Any) -> None:
        self.actions.append(("drag_to", {"target": target, **arguments}))


def make_fake_page(
    *,
    page_url: str = "",
    page_title: str = "",
    aria_text: str = "",
    child_frames: list[SimpleNamespace] | None = None,
    frames: list[SimpleNamespace] | None = None,
    present_roles: list[tuple[str, str]] | None = None,
    present_selectors: list[str] | None = None,
) -> SimpleNamespace:
    locator_calls: list[FakeLocator] = []
    keyboard_keys: list[str] = []
    bring_to_front_calls: list[bool] = []
    role_present = present_roles or []
    selector_present = present_selectors or []

    def locator(selector: str) -> FakeLocator:
        match_count = 1 if selector in selector_present else 0
        locator_instance = FakeLocator(selector, match_count=match_count)
        locator_calls.append(locator_instance)
        return locator_instance

    def get_by_role(role: str, name: Any = None, exact: bool = True) -> FakeLocator:
        match_count = 1 if (role, name) in role_present else 0
        return FakeLocator(f"role={role}", match_count=match_count)

    def press_key(key: str) -> None:
        keyboard_keys.append(key)

    def bring_to_front() -> None:
        bring_to_front_calls.append(True)

    return SimpleNamespace(
        url=page_url,
        title=lambda: page_title,
        locator=locator,
        locator_calls=locator_calls,
        get_by_role=get_by_role,
        keyboard=SimpleNamespace(press=press_key),
        keyboard_keys=keyboard_keys,
        bring_to_front=bring_to_front,
        bring_to_front_calls=bring_to_front_calls,
        aria_snapshot=lambda: aria_text,
        child_frames=child_frames or [],
        frames=frames if frames is not None else [],
    )


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
    def fake_start_chrome(
        *,
        port: int,
        user_data_dir: str | Path,
        headless: bool = False,
        window_size: tuple[int, int] = (1920, 1080),
    ) -> Any:
        state["started"] = {
            "port": port,
            "user_data_dir": str(user_data_dir),
            "headless": headless,
            "window_size": window_size,
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
        state["dual_snapshot_calls"].append(kwargs)
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


def _make_close_tab(state: dict[str, Any]) -> Any:
    def fake_close_tab(page: SimpleNamespace) -> None:
        state["close_tab_calls"].append(page)

    return fake_close_tab


def _make_switch_to_tab(state: dict[str, Any]) -> Any:
    def fake_switch_to_tab(context: FakeContext, *, url_contains: str) -> SimpleNamespace:
        for page in context.pages:
            if url_contains in page.url:
                page.bring_to_front()
                state["switch_to_tab_calls"].append((context, url_contains))
                return page
        raise RuntimeError(f"no tab found with url containing {url_contains!r}")

    return fake_switch_to_tab


def _make_evaluate(state: dict[str, Any]) -> Any:
    def fake_evaluate(root: Any, expression: str) -> Any:
        state["evaluate_calls"].append({"root": root, "expression": expression})
        return state["evaluate_result"]

    return fake_evaluate


def _make_download_resource(state: dict[str, Any]) -> Any:
    def fake_download_resource(context: Any, source_url: str, destination: Path) -> dict[str, Any]:
        state["download_resource_calls"].append(
            {"context": context, "source_url": source_url, "destination": destination}
        )
        return state["download_result"]

    return fake_download_resource


def _make_interaction_recorder(state: dict[str, Any], verb: str) -> Any:
    def fake_recorder(*positional: Any, **keyword: Any) -> None:
        state[f"{verb}_calls"].append({"positional": positional, "keyword": keyword})

    return fake_recorder


_INTERACTION_VERBS = (
    "click",
    "fill",
    "check",
    "press",
    "hover",
    "dblclick",
    "right_click",
    "scroll_into_view",
    "upload",
    "drag",
)

_WINDOW_VERBS = ("set_window_size", "set_viewport")


@pytest.fixture
def fake_cdp(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {
        "instances": [],
        "pages": [],
        "stopped": [],
        "started": None,
        "goto_calls": [],
        "open_tab_calls": [],
        "close_tab_calls": [],
        "switch_to_tab_calls": [],
        "snapshots": [],
        "dual_snapshot_calls": [],
        "evaluate_calls": [],
        "evaluate_result": None,
        "download_resource_calls": [],
        "download_result": {"status": 200, "bytes": 1024},
        "connect_raises": None,
        "ready": True,
    }
    for verb in _INTERACTION_VERBS:
        state[f"{verb}_calls"] = []
    for verb in _WINDOW_VERBS:
        state[f"{verb}_calls"] = []
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
    monkeypatch.setattr(cdp_module, "close_tab", _make_close_tab(state))
    monkeypatch.setattr(cdp_module, "switch_to_tab", _make_switch_to_tab(state))
    monkeypatch.setattr(cdp_module, "evaluate", _make_evaluate(state), raising=False)
    monkeypatch.setattr(
        cdp_module, "download_resource", _make_download_resource(state), raising=False
    )
    for verb in _INTERACTION_VERBS:
        monkeypatch.setattr(cdp_module, verb, _make_interaction_recorder(state, verb))
    for verb in _WINDOW_VERBS:
        monkeypatch.setattr(
            cdp_module, verb, _make_interaction_recorder(state, verb), raising=False
        )
    return state
