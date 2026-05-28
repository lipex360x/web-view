from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def _run(arguments: list[str]) -> int:
    return main(arguments)


def test_snap_auto_slug_writes_snap_files(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="file:///index.html", page_title="Home")]
    exit_code = _run(["snap", "--port", "9222", "--destination-dir", str(tmp_path)])
    assert exit_code == 0
    files = sorted(tmp_path.iterdir())
    names = [item.name for item in files]
    assert any(name.endswith("-snap.png") for name in names)
    assert any(name.endswith("-snap.aria.yaml") for name in names)


def test_snap_explicit_slug_still_works(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="file:///x.html", page_title="X")]
    exit_code = _run(["snap", "my-state", "--port", "9222", "--destination-dir", str(tmp_path)])
    assert exit_code == 0
    names = [item.name for item in tmp_path.iterdir()]
    assert any("my-state" in name for name in names)


def test_snap_prints_absolute_paths_to_stdout(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="file:///index.html", page_title="Home")]
    exit_code = _run(["snap", "page", "--port", "9222", "--destination-dir", str(tmp_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 2
    png_line, aria_line = lines
    assert png_line.endswith(".png")
    assert aria_line.endswith(".aria.yaml")
    assert Path(png_line).is_absolute()
    assert Path(aria_line).is_absolute()


def test_stop_without_port_stops_single_instance(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9333)]
    exit_code = _run(["stop"])
    assert exit_code == 0
    assert fake_cdp["stopped"] == [9333]


def test_stop_without_port_errors_when_zero(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = _run(["stop"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instances running" in captured.err
    assert "web-view start" in captured.err


def test_stop_without_port_errors_when_multiple(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [
        FakeInstance(pid=111, port=9222),
        FakeInstance(pid=222, port=9223),
    ]
    exit_code = _run(["stop"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "2 CDP Chrome instances running" in captured.err
    assert "--port 9222" in captured.err
    assert "--port 9223" in captured.err
    assert fake_cdp["stopped"] == []


def test_stop_with_explicit_port_unchanged(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9999)]
    exit_code = _run(["stop", "--port", "9999"])
    assert exit_code == 0
    assert fake_cdp["stopped"] == [9999]


def test_stop_missing_instance_on_explicit_port_structured_error(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["stop", "--port", "9222"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instance on port 9222" in captured.err
    assert "web-view start --port 9222" in captured.err
    assert "web-view list" in captured.err


def test_snap_missing_instance_on_explicit_port_structured_error(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["snap", "x", "--port", "9222", "--destination-dir", str(tmp_path)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instance on port 9222" in captured.err


def test_list_shows_tab_count_and_urls(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [
        FakeInstance(pid=111, port=9222, user_data_dir="~/.cache/web-view/profile")
    ]
    fake_cdp["pages"] = [
        make_fake_page(page_url="file:///index.html", page_title="Poster"),
        make_fake_page(page_url="chrome://newtab", page_title=""),
    ]
    exit_code = _run(["list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    output = captured.out
    assert "TABS" in output
    assert "2" in output
    assert "file:///index.html" in output
    assert "chrome://newtab" in output
    assert "Poster" in output


def test_list_tab_connection_failure_shows_question_mark(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["connect_raises"] = RuntimeError("boom")
    exit_code = _run(["list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_list_empty_state(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = _run(["list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "no CDP Chrome instances" in captured.out


def test_root_help_is_terse_and_lists_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["--help"])
    captured = capsys.readouterr()
    output = captured.out
    assert "web-view <command> -h" in output
    for command in ("start", "list", "stop", "navigate", "snap"):
        assert command in output
    assert "Library mode" in output
    assert "uv tool install" in output


def test_root_help_omits_per_command_detail(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["--help"])
    captured = capsys.readouterr()
    assert "Tab selection" not in captured.out
    assert "--new-tab" not in captured.out
    assert "--url-contains" not in captured.out


def test_start_url_flag_navigates_first_tab(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
) -> None:
    fake_cdp["pages"] = [make_fake_page(page_url="about:blank", page_title="")]
    exit_code = _run(
        [
            "start",
            "--port",
            "9444",
            "--user-data-dir",
            str(tmp_path / "profile"),
            "--headless",
            "--url",
            "file:///foo.html",
        ]
    )
    assert exit_code == 0
    assert fake_cdp["started"]["port"] == 9444
    assert len(fake_cdp["goto_calls"]) == 1
    target_page, target_url = fake_cdp["goto_calls"][0]
    assert target_url == "file:///foo.html"


def test_navigate_without_port_uses_single_running_instance(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9444)]
    first = make_fake_page(page_url="about:blank", page_title="")
    fake_cdp["pages"] = [first]
    exit_code = _run(["navigate", "--url", "https://foo.test"])
    assert exit_code == 0
    assert fake_cdp["goto_calls"] == [(first, "https://foo.test")]


def test_navigate_without_port_errors_when_zero(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["navigate", "--url", "https://foo.test"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instances running" in captured.err
    assert fake_cdp["goto_calls"] == []


def test_navigate_without_port_errors_when_multiple(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [
        FakeInstance(pid=111, port=9222),
        FakeInstance(pid=222, port=9223),
    ]
    exit_code = _run(["navigate", "--url", "https://foo.test"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "2 CDP Chrome instances running" in captured.err
    assert "--port 9222" in captured.err
    assert "--port 9223" in captured.err
    assert fake_cdp["goto_calls"] == []


def test_snap_without_port_uses_single_running_instance(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9444)]
    fake_cdp["pages"] = [make_fake_page(page_url="file:///index.html", page_title="Home")]
    exit_code = _run(["snap", "--destination-dir", str(tmp_path)])
    assert exit_code == 0
    names = [item.name for item in tmp_path.iterdir()]
    assert any(name.endswith("-snap.png") for name in names)


def test_snap_without_port_errors_when_zero(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["snap", "--destination-dir", str(tmp_path)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instances running" in captured.err


def test_snap_without_port_errors_when_multiple(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_cdp["instances"] = [
        FakeInstance(pid=111, port=9222),
        FakeInstance(pid=222, port=9223),
    ]
    exit_code = _run(["snap", "--destination-dir", str(tmp_path)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "2 CDP Chrome instances running" in captured.err
    assert "--port 9222" in captured.err


def test_navigate_default_uses_first_tab(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    first = make_fake_page(page_url="about:blank", page_title="")
    second = make_fake_page(page_url="https://example.com", page_title="Example")
    fake_cdp["pages"] = [first, second]
    exit_code = _run(["navigate", "--url", "https://foo.test", "--port", "9222"])
    assert exit_code == 0
    assert fake_cdp["goto_calls"] == [(first, "https://foo.test")]
    assert fake_cdp["open_tab_calls"] == []


def test_navigate_tab_by_index(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    first = make_fake_page(page_url="about:blank", page_title="")
    second = make_fake_page(page_url="https://example.com", page_title="Example")
    fake_cdp["pages"] = [first, second]
    exit_code = _run(["navigate", "--url", "https://foo.test", "--tab", "1"])
    assert exit_code == 0
    assert fake_cdp["goto_calls"] == [(second, "https://foo.test")]


def test_navigate_tab_by_substring(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    first = make_fake_page(page_url="about:blank", page_title="")
    second = make_fake_page(page_url="https://github.com/x/y", page_title="GH")
    fake_cdp["pages"] = [first, second]
    exit_code = _run(["navigate", "--url", "https://foo.test", "--tab", "github.com"])
    assert exit_code == 0
    assert fake_cdp["goto_calls"] == [(second, "https://foo.test")]


def test_navigate_new_tab_opens_fresh_tab(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    existing = make_fake_page(page_url="https://example.com", page_title="Example")
    fake_cdp["pages"] = [existing]
    exit_code = _run(["navigate", "--url", "https://foo.test", "--new-tab"])
    assert exit_code == 0
    assert fake_cdp["goto_calls"] == []
    assert len(fake_cdp["open_tab_calls"]) == 1
    _, opened_url = fake_cdp["open_tab_calls"][0]
    assert opened_url == "https://foo.test"


def test_navigate_tab_and_new_tab_are_mutually_exclusive(
    fake_cdp: dict[str, Any],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    with pytest.raises(SystemExit):
        _run(["navigate", "--url", "https://foo.test", "--tab", "0", "--new-tab"])


def test_navigate_unknown_tab_substring_errors(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.com", page_title="Example")]
    exit_code = _run(["navigate", "--url", "https://foo.test", "--tab", "github.com"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No tab matched 'github.com'" in captured.err
    assert "web-view list" in captured.err
    assert fake_cdp["goto_calls"] == []


def test_navigate_out_of_range_index_errors(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="about:blank", page_title="")]
    exit_code = _run(["navigate", "--url", "https://foo.test", "--tab", "5"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No tab matched '5'" in captured.err
    assert fake_cdp["goto_calls"] == []


def test_navigate_missing_instance_on_port_structured_error(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["navigate", "--url", "https://foo.test", "--port", "9222"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instance on port 9222" in captured.err
    assert "web-view start --port 9222" in captured.err
    assert "web-view list" in captured.err


def test_navigate_help_shows_tab_selection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["navigate", "--help"])
    captured = capsys.readouterr()
    output = captured.out
    assert "Tab selection" in output
    assert "--new-tab" in output
    assert "--tab N" in output


def test_snap_help_shows_examples_and_composability(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["snap", "--help"])
    captured = capsys.readouterr()
    output = captured.out
    assert "--url-contains" in output
    assert "xargs" in output


def test_stop_help_explains_port_optionality(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["stop", "--help"])
    captured = capsys.readouterr()
    assert "exactly one CDP Chrome is running" in captured.out


def test_start_without_url_does_not_navigate(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
) -> None:
    fake_cdp["pages"] = [make_fake_page(page_url="about:blank", page_title="")]
    exit_code = _run(
        [
            "start",
            "--port",
            "9445",
            "--user-data-dir",
            str(tmp_path / "profile"),
            "--headless",
        ]
    )
    assert exit_code == 0
    assert fake_cdp["goto_calls"] == []


def _seed_single_instance(fake_cdp: dict[str, Any], *, page_url: str = "https://x.test") -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url=page_url, page_title="X")]


def test_do_click_invokes_cdp_click_with_role_and_name(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "Next slide"])
    assert exit_code == 0
    assert len(fake_cdp["click_calls"]) == 1
    call = fake_cdp["click_calls"][0]
    assert call["positional"][1] == "button"
    assert call["positional"][2] == "Next slide"


def test_do_fill_invokes_cdp_fill_with_value(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(
        ["do", "fill", "--role", "textbox", "--name", "Email", "--value", "user@example.com"]
    )
    assert exit_code == 0
    call = fake_cdp["fill_calls"][0]
    assert call["positional"][1] == "textbox"
    assert call["positional"][2] == "Email"
    assert call["positional"][3] == "user@example.com"


def test_do_fill_reads_stdin_when_value_omitted(
    fake_cdp: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_single_instance(fake_cdp)
    monkeypatch.setattr("sys.stdin", io.StringIO("multi\nline\nvalue"))
    exit_code = _run(["do", "fill", "--role", "textbox", "--name", "Body"])
    assert exit_code == 0
    call = fake_cdp["fill_calls"][0]
    assert call["positional"][3] == "multi\nline\nvalue"


def test_do_check_invokes_cdp_check(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "check", "--role", "checkbox", "--name", "Remember me"])
    assert exit_code == 0
    call = fake_cdp["check_calls"][0]
    assert call["positional"][1] == "checkbox"
    assert call["positional"][2] == "Remember me"


def test_do_press_splits_keys_on_commas(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "press", "--keys", "Control+a,Backspace,Meta+v"])
    assert exit_code == 0
    call = fake_cdp["press_calls"][0]
    keys = call["positional"][1:]
    assert keys == ("Control+a", "Backspace", "Meta+v")


def test_do_press_tolerates_spaces_around_commas(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "press", "--keys", "Control+a , Backspace"])
    assert exit_code == 0
    keys = fake_cdp["press_calls"][0]["positional"][1:]
    assert keys == ("Control+a", "Backspace")


def test_do_hover_invokes_cdp_hover(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "hover", "--role", "button", "--name", "Tip"])
    assert exit_code == 0
    call = fake_cdp["hover_calls"][0]
    assert call["positional"][1] == "button"
    assert call["positional"][2] == "Tip"


def test_do_dblclick_invokes_cdp_dblclick(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "dblclick", "--role", "link", "--name", "Open"])
    assert exit_code == 0
    call = fake_cdp["dblclick_calls"][0]
    assert call["positional"][1] == "link"
    assert call["positional"][2] == "Open"


def test_do_right_click_invokes_cdp_right_click(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "right-click", "--role", "cell", "--name", "A1"])
    assert exit_code == 0
    call = fake_cdp["right_click_calls"][0]
    assert call["positional"][1] == "cell"
    assert call["positional"][2] == "A1"


def test_do_scroll_into_view_invokes_cdp_scroll_into_view(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "scroll-into-view", "--role", "region", "--name", "Footer"])
    assert exit_code == 0
    call = fake_cdp["scroll_into_view_calls"][0]
    assert call["positional"][1] == "region"
    assert call["positional"][2] == "Footer"


def test_do_upload_invokes_cdp_upload_with_file(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
) -> None:
    _seed_single_instance(fake_cdp)
    report_path = tmp_path / "report.pdf"
    report_path.write_bytes(b"pdf")
    exit_code = _run(
        [
            "do",
            "upload",
            "--role",
            "button",
            "--name",
            "Choose file",
            "--file",
            str(report_path),
        ]
    )
    assert exit_code == 0
    call = fake_cdp["upload_calls"][0]
    assert call["positional"][1] == "button"
    assert call["positional"][2] == "Choose file"
    assert call["positional"][3] == str(report_path)


def test_do_upload_requires_file_flag(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single_instance(fake_cdp)
    with pytest.raises(SystemExit):
        _run(["do", "upload", "--role", "button", "--name", "Pick"])


def test_do_drag_parses_from_to_micro_syntax(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "drag", "--from", "button:Item", "--to", "region:Trash"])
    assert exit_code == 0
    call = fake_cdp["drag_calls"][0]
    assert call["keyword"]["source"] == ("button", "Item")
    assert call["keyword"]["target"] == ("region", "Trash")


def test_do_click_with_selector_uses_locator_path(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--selector", "[data-testid=submit]"])
    assert exit_code == 0
    assert fake_cdp["click_calls"] == []
    page = fake_cdp["pages"][0]
    assert page.locator_calls
    assert page.locator_calls[0].selector == "[data-testid=submit]"
    assert page.locator_calls[0].actions[0][0] == "click"


def test_do_click_rejects_role_and_selector_together(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(
        [
            "do",
            "click",
            "--role",
            "button",
            "--name",
            "X",
            "--selector",
            "[data-testid=x]",
        ]
    )
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "mutually exclusive" in captured.err or "exclusive" in captured.err


def test_do_click_requires_addressing(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "--role" in captured.err or "--selector" in captured.err


def test_do_click_tab_by_index(fake_cdp: dict[str, Any]) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    second_page = make_fake_page(page_url="https://second.test", page_title="2nd")
    fake_cdp["pages"] = [
        make_fake_page(page_url="https://first.test", page_title="1st"),
        second_page,
    ]
    exit_code = _run(["do", "click", "--tab", "1", "--role", "button", "--name", "Go"])
    assert exit_code == 0
    call = fake_cdp["click_calls"][0]
    assert call["positional"][0] is second_page


def test_do_click_tab_by_substring(fake_cdp: dict[str, Any]) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    classmark_page = make_fake_page(page_url="https://classmark.test", page_title="C")
    fake_cdp["pages"] = [
        make_fake_page(page_url="https://other.test", page_title="O"),
        classmark_page,
    ]
    exit_code = _run(["do", "click", "--tab", "classmark", "--role", "button", "--name", "Go"])
    assert exit_code == 0
    assert fake_cdp["click_calls"][0]["positional"][0] is classmark_page


def test_do_click_port_optional_auto_resolves(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "Go"])
    assert exit_code == 0
    assert len(fake_cdp["click_calls"]) == 1


def test_do_click_zero_instances_structured_error(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["do", "click", "--role", "button", "--name", "Go"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instances running" in captured.err
    assert fake_cdp["click_calls"] == []


def test_do_click_accepts_custom_timeout(fake_cdp: dict[str, Any]) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "Go", "--timeout", "30"])
    assert exit_code == 0
    call = fake_cdp["click_calls"][0]
    assert call["keyword"]["timeout_s"] == 30


def test_do_click_prints_one_line_ack(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "Next slide"])
    assert exit_code == 0
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert lines == ['clicked: button "Next slide"']


def test_do_click_quiet_suppresses_ack(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--role", "button", "--name", "Next slide", "--quiet"])
    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_do_click_with_selector_ack_uses_selector(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single_instance(fake_cdp)
    exit_code = _run(["do", "click", "--selector", "[data-testid=submit]"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "[data-testid=submit]" in captured.out


def test_do_click_missing_tab_substring_structured_error(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://other.test", page_title="O")]
    exit_code = _run(
        ["do", "click", "--tab", "missing-substring", "--role", "button", "--name", "Go"]
    )
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No tab matched" in captured.err
    assert fake_cdp["click_calls"] == []


def test_do_click_explicit_port_no_instance_structured_error(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_cdp["instances"] = []
    exit_code = _run(["do", "click", "--port", "9222", "--role", "button", "--name", "Go"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "No CDP Chrome instance on port 9222" in captured.err


def test_root_help_lists_do_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["--help"])
    captured = capsys.readouterr()
    assert "do" in captured.out


def test_do_help_lists_all_verbs(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["do", "--help"])
    captured = capsys.readouterr()
    output = captured.out
    for verb in (
        "click",
        "fill",
        "check",
        "press",
        "hover",
        "dblclick",
        "right-click",
        "scroll-into-view",
        "upload",
        "drag",
    ):
        assert verb in output


def test_do_click_help_has_examples_epilog(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["do", "click", "--help"])
    captured = capsys.readouterr()
    assert "Examples" in captured.out
