# CLAUDE.md — instructions for AI coding sessions on `web-view`

This file is the project's executable spec for a fresh AI context. Read
it first; the conventions below override any defaults from a global
CLAUDE.md or training data.

## What `web-view` is

A project-agnostic toolkit for driving real Chrome via the Chrome
DevTools Protocol (CDP) on top of Playwright's sync API. Two halves:

- **Library** (`from web_view import cdp`) — every helper for driving
  Chrome (lifecycle, connection, navigation, interaction, files, state,
  snapshots, console, network). ~30 public symbols, organised as a
  package under `src/web_view/cdp/`.
- **CLI** (`web-view <command>` after `uv tool install`) — the
  no-Python convenience layer. Six top-level commands: `start`, `list`,
  `stop`, `navigate`, `snap`, `do` (the last is a parent for ten
  element-interaction verbs).

The library half exists for programmatic use; the CLI exists so the
common "click this thing" loop doesn't need a Python REPL.

## Stack

- Python 3.11+ (`pyproject.toml` declares `requires-python = ">=3.11"`).
- Runtime deps: `playwright>=1.40`.
- Dev deps (`uv sync --extra dev`): `pytest`, `pytest-cov`, `ruff`,
  `mypy`, `pre-commit`.
- Package manager: `uv` (never `pip` directly).
- Tests run via `uv run --extra dev pytest tests/ -q`.

## Layout

```
src/web_view/
  __init__.py            re-exports `cdp` for `from web_view import cdp`
  cdp/                   library half — driving Chrome via CDP
    __init__.py          re-exports the public symbols + the GOLDEN
                         RULE docstring (wait on state, never on time)
    _shared.py           locator + wait helpers, localhost JSON probe,
                         storage-kind guard — reused across modules
    _lifecycle.py        start/stop Chrome, list_cdp_instances,
                         is_cdp_ready
    _connection.py       connect, pages_info, find_page, open/switch/
                         close tab
    _navigation.py       goto, wait_for_url, back/forward/reload
    _interaction.py      click, fill, check, press, hover, dblclick,
                         right_click, scroll_into_view, drag
    _files.py            capture_download, upload
    _state.py            cookies, storage, clipboard
    _snapshots.py        screenshot, aria_snapshot, dual_snapshot,
                         get_html, inspect_element
    _console.py          console event recorder
    _network.py          request/response recorder + dump_network
  cli/                   CLI half — argparse subcommands
    __init__.py          parser builder; registers every subcommand
    _shared.py           cross-subcommand helpers (port resolution,
                         tab resolution, structured error printers)
    _start.py / _list.py / _stop.py / _navigate.py / _snap.py
    _do/                 `web-view do <verb>` — element interaction
      __init__.py        registers the `do` parent + each verb
      _shared.py         addressing + runtime args, ack printer,
                         run_addressed_verb DRY helper
      _click.py / _fill.py / _check.py / _press.py / _hover.py /
      _dblclick.py / _right_click.py / _scroll_into_view.py /
      _upload.py / _drag.py
tests/
  conftest.py            fake_cdp fixture — monkeypatches every cdp.*
                         helper to record calls in a state dict
  test_cli.py            single file covering every CLI subcommand
docs/adr/                Architecture Decision Records
  0001-cli-interaction.md     `web-view do <verb>` design (Mechanism C)
```

Public API is what `web_view.cdp.__all__` exports; everything under a
leading underscore is internal.

## Golden rules

1. **Wait on state changes, never on time.** No `wait_for_timeout`, no
   `time.sleep`, no fixed-duration polling. `timeout_s=N` on `cdp.*`
   helpers is an upper bound — calls return the instant the state
   changes. The cdp package docstring elaborates with anti-patterns.
2. **Never use `context.pages[0]`.** Chrome over CDP exposes auxiliary
   targets (RotateCookies, service workers, devtools). Always use
   `cdp.find_page(context, url_contains=...)` or
   `cdp.find_page(context, predicate=lambda url: ...)`.
3. **Snapshots are pairs.** Every UI state worth saving is captured as
   `NN-slug.png` + `NN-slug.aria.yaml`. Use `cdp.dual_snapshot(...)`.
4. **First positional arg is always the Playwright object.** No
   globals; pass `Page` or `BrowserContext` explicitly.

## Coding rules (from `lipex360x/dev-quality`)

The pre-commit hook runs `check-all` from
[`lipex360x/dev-quality`](https://github.com/lipex360x/dev-quality)
`v0.15.3`. The rules:

- **No abbreviations in identifiers.** Denylist includes `cmd`, `ctx`,
  `dest`, `src`, `idx`, `info`, `exc`, `url`, `var`, `cfg`, and ~70
  others. Use the full word: `command`, `context`, `destination`,
  `source`, `index`, `information`, `exception`, `URL`, `variable`,
  `config`. Allowlist for short names: `i`, `j`, `k`, `_`, `id`, `ok`.
- **No comments in source files.** Module/class/function docstrings
  are fine. No inline `#` comments (except shebangs in scripts). If you
  feel a comment is needed, rename or extract a function instead.
- **No `# noqa` / `# nosec` annotations.** Fix the root cause; don't
  silence the linter.
- **File size:** ≤ 800 lines (production), ≤ 1500 lines (tests).
- **Function size:** ≤ 100 lines.
- **Cyclomatic complexity:** ≤ 6 for Bash; ruff's `C901` for Python.
- **Line length:** 120 chars (configured at 100 in
  `pyproject.toml [tool.ruff]`).

Run the gates manually:

```bash
uv run --extra dev pytest tests/ -q       # unit tests, must be all green
uv run --extra dev ruff check src/ tests/ # lint
uv run --extra dev ruff format src/ tests/ # formatter
check-all .                                # dev-quality umbrella
```

## TDD — non-negotiable

For every new feature or bug fix:

1. **Red** — write the failing test first in `tests/test_cli.py`
   (extend the `fake_cdp` fixture in `tests/conftest.py` if new
   `cdp.*` helpers need stubbing). Run pytest; the new test must fail
   for the expected reason (assertion mismatch, not import error).
   Commit: `test: <slug> (failing)`.
2. **Green** — implement the minimum code to make the new tests pass.
   No extra features. Run pytest; all green. Commit: `feat: <slug>` or
   `fix: <slug>`.
3. **Refactor** — only if duplication or clarity loss appeared. Tests
   do not change. Commit: `refactor: <slug>` (skip entirely if no
   refactor is warranted — don't commit empty cleanups).

Run the full quality gate between phases.

## Workflow for feature / fix work

1. **Branch off main.** `git checkout main && git pull && git checkout
   -b <type>/<slug>-<issue-number>`. Prefixes: `feat/`, `fix/`,
   `chore/`, `design/` (for ADR-only PRs against `needs-design`
   issues).
2. **TDD.** Red → green → refactor as above.
3. **Docs.** Update `CHANGELOG.md` `[Unreleased]` section. Update
   `README.md` if the public surface (CLI flags, API) changed. Update
   `docs/adr/` if a design decision merits its own ADR.
4. **Version bump.** If the work qualifies for a release (see
   "Tag versioning" below), bump `pyproject.toml` `version` in the same
   PR. Otherwise leave it.
5. **PR.** Title: `<type>: <subject>`. Body: summary, what's in the
   PR, test plan. Use `Closes #N` if the PR fully resolves the issue;
   `Refs #N` for partial / design-only.
6. **Merge.** Squash-merge via `gh pr merge <N> --squash
   --delete-branch`. After merge, sync local main:
   `git checkout main && git pull`.
7. **Tag (if qualifying).** See "Tag versioning".
8. **Upgrade the local installed CLI.** Always run:
   ```bash
   uv tool upgrade web-view
   ```
   This pulls the new `main` (or tag) and rebuilds the CLI on `PATH`.
   *This is the standard closure step at the end of every PR that
   merges to main.* Verify with `web-view -h` showing the expected
   surface.
9. **Tick the issue body.** For issues with checkbox-style AC, edit
   the body to tick the completed items (`gh issue edit <N>` with the
   updated body). A merged PR with unticked AC is a process violation.

## Tag versioning

The project follows semver and uses annotated git tags:

- **patch** (`v0.x.y` → `v0.x.(y+1)`) — bug fixes, no public surface
  change.
- **minor** (`v0.x.y` → `v0.(x+1).0`) — additive public surface (new
  CLI command, new library helper). Backward-compatible.
- **major** (`v0.y.z` → `v1.0.0`) — breaking changes. Don't do this
  casually; document the migration path.

Tag commands:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "..." --notes "..."
```

Do not tag intermediate states. Tag only after the AC for the
qualifying issue are all ticked and the closure ritual is complete.

## Issue conventions

- **Labels:** `bug`, `enhancement`, `polish`, `needs-design`. The
  `needs-design` label means no AC yet — a design pass produces an ADR
  in `docs/adr/`, then the issue body gets the AC populated and the
  label is swapped to `enhancement` before Phase B starts.
- **Two-phase issues** (any `needs-design` issue) close via Phase B,
  not Phase A. The ADR PR uses `Refs #N`; the implementation PR uses
  `Closes #N`.
- **Branch suggestion** in every issue body uses
  `<type>/<slug>-<issue-number>`.

## GitHub Project board

Board #16 ([`web-view`](https://github.com/users/lipex360x/projects/16))
tracks the work. Status options:

- **Backlog** — not started yet
- **Design** — needs an ADR / design pass before implementation
- **In progress** — branch open / PR in flight
- **Done** — merged or closed

Add new issues / PRs with `gh project item-add 16 --owner lipex360x
--url <url>`, then `gh project item-edit ... --field-id ...
--single-select-option-id ...`.

## Key locations

| What | Where |
|---|---|
| ADRs | `docs/adr/` |
| Public API exports | `src/web_view/cdp/__init__.py` `__all__` |
| CLI parser builder | `src/web_view/cli/__init__.py` |
| Test fixtures | `tests/conftest.py` (`fake_cdp`) |
| Pre-commit config | `.pre-commit-config.yaml` |
| Release tags | <https://github.com/lipex360x/web-view/releases> |
| Project board | <https://github.com/users/lipex360x/projects/16> |

## When NOT to act autonomously

Confirm with the user before:

- **Force-pushing**, `git reset --hard`, deleting branches that aren't
  yours.
- **Tagging** or **publishing a release** unless the user explicitly
  asked or the closure ritual unambiguously qualifies.
- **Reordering / rewriting commits** on a shared branch.
- **Editing `CLAUDE.md`** (this file) — it's the executable spec; the
  user owns it.
- **Closing issues** outside the natural PR-merge auto-close.
