from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from web_view import cdp
from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


def _run(arguments: list[str]) -> int:
    return main(arguments)


def _seed_single(fake_cdp: dict[str, Any], *, page_url: str = "https://x.test") -> SimpleNamespace:
    page = make_fake_page(page_url=page_url)
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [page]
    return page


def test_evaluate_runs_expression_on_root() -> None:
    calls: list[str] = []
    root = SimpleNamespace(evaluate=lambda expression: calls.append(expression) or ["a", "b"])
    result = cdp.evaluate(root, "document.title")
    assert result == ["a", "b"]
    assert calls == ["document.title"]


def _fake_context(status: int, body: bytes, urls: list[str]) -> SimpleNamespace:
    response = SimpleNamespace(status=status, body=lambda: body)

    def get(source_url: str) -> SimpleNamespace:
        urls.append(source_url)
        return response

    return SimpleNamespace(request=SimpleNamespace(get=get))


def test_download_resource_writes_body_and_reports(tmp_path: Path) -> None:
    urls: list[str] = []
    context = _fake_context(200, b"video-bytes", urls)
    destination = tmp_path / "clip.mp4"
    result = cdp.download_resource(context, "https://host/clip.mp4", destination)
    assert urls == ["https://host/clip.mp4"]
    assert destination.read_bytes() == b"video-bytes"
    assert result == {"status": 200, "bytes": len(b"video-bytes")}


def test_download_resource_reports_non_2xx_status(tmp_path: Path) -> None:
    context = _fake_context(404, b"not found", [])
    result = cdp.download_resource(context, "https://host/missing", tmp_path / "x")
    assert result["status"] == 404


def test_evaluate_and_download_resource_exported() -> None:
    assert "evaluate" in cdp.__all__
    assert "download_resource" in cdp.__all__


def test_eval_prints_json_result(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single(fake_cdp)
    fake_cdp["evaluate_result"] = ["https://host/a.mp4", "https://host/b.mp4"]
    exit_code = _run(["eval", "--js", "[...document.querySelectorAll('video')].map(v=>v.src)"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == json.dumps(
        ["https://host/a.mp4", "https://host/b.mp4"]
    )


def test_eval_honours_frame(fake_cdp: dict[str, Any]) -> None:
    outer = make_fake_page(page_url="file:///course/index.html")
    inner = make_fake_page(page_url="file:///course/index_lms.html")
    outer.frames = [outer, inner]
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [outer]
    fake_cdp["evaluate_result"] = 42
    exit_code = _run(["eval", "--js", "1+1", "--frame", "index_lms"])
    assert exit_code == 0
    assert fake_cdp["evaluate_calls"][0]["root"] is inner


def test_eval_non_serialisable_result_errors(
    fake_cdp: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single(fake_cdp)
    fake_cdp["evaluate_result"] = object()
    exit_code = _run(["eval", "--js", "window"])
    assert exit_code == 1
    assert capsys.readouterr().err.strip() != ""


def test_download_reports_status_and_bytes(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single(fake_cdp)
    fake_cdp["download_result"] = {"status": 200, "bytes": 2048}
    exit_code = _run(
        ["download", "--url", "https://host/clip.mp4", "--out", str(tmp_path / "clip.mp4")]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "200" in output
    assert "2048" in output
    call = fake_cdp["download_resource_calls"][0]
    assert call["source_url"] == "https://host/clip.mp4"


def test_download_non_2xx_exits_1(
    fake_cdp: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_single(fake_cdp)
    fake_cdp["download_result"] = {"status": 404, "bytes": 12}
    exit_code = _run(["download", "--url", "https://host/missing", "--out", str(tmp_path / "x")])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "404" in captured.out + captured.err


def test_eval_help_documents_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["eval", "--help"])
    output = capsys.readouterr().out
    assert "--js" in output
    assert "--frame" in output


def test_download_help_documents_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["download", "--help"])
    output = capsys.readouterr().out
    assert "--url" in output
    assert "--out" in output


def test_root_help_lists_eval_and_download(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run(["--help"])
    output = capsys.readouterr().out
    assert "eval" in output
    assert "download" in output
