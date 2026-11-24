from __future__ import annotations

from typing import Any

import pytest

from web_view import cdp
from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def prepare_page(fake_cdp: dict[str, Any], tree: str) -> None:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(page_url="https://example.test", aria_text=tree)]


def test_stdout_prints_snapshot_without_writing_files(
    fake_cdp: dict[str, Any], capsys: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp, '- button "Continue"')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cdp, "aria_snapshot", lambda page, **options: page.aria_snapshot())
    assert main(["snap", "--stdout"]) == 0
    assert capsys.readouterr().out == '- button "Continue"\n'
    assert list(tmp_path.iterdir()) == []


def test_stdout_explicitly_marks_truncation(
    fake_cdp: dict[str, Any], capsys: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp, '- button "One"\n- button "Two"')
    monkeypatch.setattr(cdp, "aria_snapshot", lambda page, **options: page.aria_snapshot())
    assert main(["snap", "--stdout", "--max-chars", "14"]) == 0
    output = capsys.readouterr()
    assert 'button "One"' in output.out
    assert "truncated" in output.out.lower()
    assert "truncated" in output.err.lower()


@pytest.mark.parametrize("limit", ["0", "14"])
def test_stdout_preserves_complete_snapshot_at_boundary(
    fake_cdp: dict[str, Any], capsys: Any, monkeypatch: pytest.MonkeyPatch, limit: str
) -> None:
    prepare_page(fake_cdp, '- button "One"')
    monkeypatch.setattr(cdp, "aria_snapshot", lambda page, **options: page.aria_snapshot())
    assert main(["snap", "--stdout", "--max-chars", limit]) == 0
    output = capsys.readouterr()
    assert output.out == '- button "One"\n' and not output.err


def test_stdout_rejects_ambiguous_tabs(fake_cdp: dict[str, Any], capsys: Any) -> None:
    prepare_page(fake_cdp, "- button")
    fake_cdp["pages"].append(make_fake_page(page_url="https://example.test/other"))
    assert main(["snap", "--stdout", "--tab", "unique:example.test"]) == 1
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_stdout_respects_no_frames_and_unique_tab(
    fake_cdp: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_page(fake_cdp, "- button")
    calls: list[tuple[Any, bool]] = []

    def snapshot(page: Any, *, include_frames: bool) -> str:
        calls.append((page, include_frames))
        return "- button"

    monkeypatch.setattr(cdp, "aria_snapshot", snapshot)
    assert main(["snap", "--stdout", "--no-frames", "--tab", "unique:example.test"]) == 0
    assert calls == [(fake_cdp["pages"][0], False)]


def test_stdout_and_image_are_incompatible() -> None:
    with pytest.raises(SystemExit):
        main(["snap", "--stdout", "--image"])


def test_max_chars_requires_stdout(capsys: Any) -> None:
    assert main(["snap", "--max-chars", "50"]) == 1
    assert "requires --stdout" in capsys.readouterr().err


@pytest.mark.parametrize("limit", ["-1", "invalid"])
def test_stdout_rejects_invalid_limit(limit: str) -> None:
    with pytest.raises(SystemExit):
        main(["snap", "--stdout", "--max-chars", limit])
