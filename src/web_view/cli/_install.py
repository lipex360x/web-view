"""Install assets bundled with web-view."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..skill_installer import install_skill

EPILOG = """\
Examples:
  web-view install skill
  web-view install skill --agent claude --scope local
  web-view install skill --target ~/www/codex/skills --force

Defaults to Codex's global ~/.codex/skills/web-view directory.
--scope local uses ./.codex/skills (or ./.claude/skills).
--target specifies the parent skills directory and overrides scope/agent.
Existing directory symlinks are followed. Existing files require --force,
which saves .bak backups (numbered if necessary) before replacing them.
Refresh the installed skill with this command after upgrading web-view.
"""


def handle(arguments: argparse.Namespace) -> int:
    try:
        path = install_skill(
            agent=arguments.agent,
            scope=arguments.scope,
            target=arguments.target,
            force=arguments.force,
        )
    except OSError as exception:
        print(f"Skill installation failed: {exception}", file=sys.stderr)
        return 1
    print(f"Installed: {path}")
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("install", help="install bundled assets")
    targets = parser.add_subparsers(dest="install_target", required=True, metavar="<target>")
    skill_parser = targets.add_parser(
        "skill",
        help="install the bundled skill for Codex or Claude Code",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    skill_parser.add_argument("--agent", choices=["codex", "claude"], default="codex")
    skill_parser.add_argument("--scope", choices=["local", "global"], default="global")
    skill_parser.add_argument("--target", type=Path, help="parent directory for web-view skill")
    skill_parser.add_argument(
        "--force", action="store_true", help="back up and replace existing files"
    )
    skill_parser.set_defaults(func=handle)
