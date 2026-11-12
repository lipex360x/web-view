"""Install the skill bundled with the distribution into an agent's skill directory."""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

_SKILL_FILES = ("SKILL.md", "agents/openai.yaml")


def resolve_skill_dir(*, agent: str, scope: str, target: Path | None = None) -> Path:
    """Resolve a skill root, preserving any existing directory symlinks."""
    if target is not None:
        return target.expanduser().resolve() / "web-view"
    base = Path.cwd() if scope == "local" else Path.home()
    return (base / f".{agent}" / "skills").resolve() / "web-view"


def _backup_file(path: Path) -> None:
    backup = path.with_name(f"{path.name}.bak")
    index = 1
    while backup.exists() or backup.is_symlink():
        backup = path.with_name(f"{path.name}.bak.{index}")
        index += 1
    shutil.copy2(path, backup)


def install_skill(
    *, agent: str, scope: str, target: Path | None = None, force: bool = False
) -> Path:
    """Copy bundled skill files; explicit replacements retain numbered backups."""
    directory = resolve_skill_dir(agent=agent, scope=scope, target=target)
    contents = {
        name: files("web_view.skill").joinpath(name).read_text(encoding="utf-8")
        for name in _SKILL_FILES
    }
    existing = [directory / name for name in contents if (directory / name).exists()]
    if existing and not force:
        raise FileExistsError(f"{existing[0]} already exists (use --force to back up and replace)")
    for path in existing:
        _backup_file(path)
    for name, content in contents.items():
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return directory / "SKILL.md"
