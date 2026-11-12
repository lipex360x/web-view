from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from web_view.cli import main

from .conftest import FakeInstance, make_fake_page


@pytest.fixture
def snapshot_page(fake_cdp: dict[str, Any]) -> dict[str, Any]:
    fake_cdp["instances"] = [FakeInstance(pid=111, port=9222)]
    fake_cdp["pages"] = [make_fake_page(aria_text='- button "Continue"')]
    return fake_cdp


def test_image_flag_preserves_pair_and_output_order(
    snapshot_page: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["snap", "page", "--image", "--destination-dir", str(tmp_path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [str(tmp_path / "01-page.png"), str(tmp_path / "01-page.aria.yaml")]
    assert all(Path(line).is_file() for line in lines)


def test_yaml_capture_increments_after_existing_image_and_normalizes_slug(
    snapshot_page: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "03-old.png").write_bytes(b"preserve")
    for number in (4, 5):
        assert main(["snap", "My State!", "--destination-dir", str(tmp_path)]) == 0
        path = tmp_path / f"{number:02d}-my-state.aria.yaml"
        assert path.read_text() == '- button "Continue"\n'
    assert snapshot_page["dual_snapshot_calls"] == []
    assert len(list(tmp_path.glob("*.png"))) == 1


@pytest.mark.parametrize("image", [False, True])
def test_invalid_snapshot_slug_reports_error(
    snapshot_page: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str], image: bool
) -> None:
    arguments = ["snap", "!!!", "--destination-dir", str(tmp_path)]
    if image:
        arguments.append("--image")
    assert main(arguments) == 1
    assert "slug" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("scope", ["local", "global"])
def test_install_skill_scopes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, agent: str, scope: str
) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    home.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setattr(Path, "home", lambda: home)
    assert main(["install", "skill", "--agent", agent, "--scope", scope]) == 0
    base = project if scope == "local" else home
    installed = base / f".{agent}" / "skills" / "web-view"
    assert "name: web-view" in (installed / "SKILL.md").read_text()
    assert "allow_implicit_invocation: true" in (installed / "agents/openai.yaml").read_text()


def test_install_skill_custom_target_refuses_overwrite_and_force_preserves_backups(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arguments = ["install", "skill", "--target", str(tmp_path)]
    assert main(arguments) == 0
    installed = tmp_path / "web-view"
    document = installed / "SKILL.md"
    document.write_text("user version")
    assert main(arguments) == 1
    assert "--force" in capsys.readouterr().err
    assert document.read_text() == "user version"
    assert main([*arguments, "--force"]) == 0
    assert (installed / "SKILL.md.bak").read_text() == "user version"
    document.write_text("second user version")
    assert main([*arguments, "--force"]) == 0
    assert (installed / "SKILL.md.bak.1").read_text() == "second user version"
    assert (installed / "SKILL.md.bak").read_text() == "user version"


def test_install_skill_uses_existing_parent_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configuration = tmp_path / "configuration"
    configuration.mkdir()
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex/skills").symlink_to(configuration, target_is_directory=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    assert main(["install", "skill"]) == 0
    assert (configuration / "web-view/SKILL.md").is_file()
    assert (home / ".codex/skills").is_symlink()
