from __future__ import annotations

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
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222, user_data_dir="/tmp/p")]
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


def test_help_contains_workflow_and_library_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        _run(["--help"])
    captured = capsys.readouterr()
    assert "Common workflow:" in captured.out
    assert "Library mode" in captured.out
    assert "uv tool install" in captured.out


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
