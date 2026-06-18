from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def _run(arguments: list[str]) -> int:
    return main(arguments)


def _seed_frames(
    fake_cdp: dict[str, Any],
    *,
    button: tuple[str, str] = ("button", "ENTER"),
) -> tuple[SimpleNamespace, SimpleNamespace]:
    outer = make_fake_page(page_url="file:///course/index.html")
    inner = make_fake_page(
        page_url="file:///course/index_lms.html",
        present_roles=[button],
    )
    outer.frames = [outer, inner]
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [outer]
    return outer, inner


def test_do_click_frame_by_index_targets_that_frame(fake_cdp: dict[str, Any]) -> None:
    _outer, inner = _seed_frames(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "ENTER", "--frame", "1"])
    assert exit_code == 0
    assert fake_cdp["click_calls"][0]["positional"][0] is inner


def test_do_click_frame_by_url_substring_targets_that_frame(fake_cdp: dict[str, Any]) -> None:
    _outer, inner = _seed_frames(fake_cdp)
    exit_code = _run(
        ["do", "click", "--role", "button", "--name", "ENTER", "--frame", "index_lms"]
    )
    assert exit_code == 0
    assert fake_cdp["click_calls"][0]["positional"][0] is inner


def test_do_click_frame_auto_resolves_to_frame_holding_element(fake_cdp: dict[str, Any]) -> None:
    _outer, inner = _seed_frames(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "ENTER"])
    assert exit_code == 0
    assert len(fake_cdp["click_calls"]) == 1
    assert fake_cdp["click_calls"][0]["positional"][0] is inner


def test_do_click_without_frames_targets_top_page(fake_cdp: dict[str, Any]) -> None:
    page = make_fake_page(page_url="https://x.test")
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [page]
    exit_code = _run(["do", "click", "--role", "button", "--name", "Go"])
    assert exit_code == 0
    assert fake_cdp["click_calls"][0]["positional"][0] is page


def test_do_click_frame_index_out_of_range_errors(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_frames(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "ENTER", "--frame", "9"])
    assert exit_code == 1
    assert fake_cdp["click_calls"] == []
    assert "9" in capsys.readouterr().err


def test_do_click_frame_substring_no_match_errors(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_frames(fake_cdp)
    exit_code = _run(
        ["do", "click", "--role", "button", "--name", "ENTER", "--frame", "nope"]
    )
    assert exit_code == 1
    assert fake_cdp["click_calls"] == []
    assert "nope" in capsys.readouterr().err


def test_do_fill_frame_by_index_targets_that_frame(fake_cdp: dict[str, Any]) -> None:
    _outer, inner = _seed_frames(fake_cdp, button=("textbox", "Answer"))
    exit_code = _run(
        [
            "do",
            "fill",
            "--role",
            "textbox",
            "--name",
            "Answer",
            "--value",
            "42",
            "--frame",
            "1",
        ]
    )
    assert exit_code == 0
    assert fake_cdp["fill_calls"][0]["positional"][0] is inner


def test_do_drag_frame_by_index_targets_that_frame(fake_cdp: dict[str, Any]) -> None:
    _outer, inner = _seed_frames(fake_cdp)
    exit_code = _run(
        ["do", "drag", "--from", "button:Item", "--to", "region:Trash", "--frame", "1"]
    )
    assert exit_code == 0
    assert fake_cdp["drag_calls"][0]["positional"][0] is inner


def test_do_help_documents_frame(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["do", "--help"])
    assert "--frame" in capsys.readouterr().out


def test_do_click_help_documents_frame(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["do", "click", "--help"])
    assert "--frame" in capsys.readouterr().out
