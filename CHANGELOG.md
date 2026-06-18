# Changelog

All notable changes to this project will be documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`web-view tab new/close/switch`** — tab-lifecycle CLI family under a single `tab` parent. Three verbs graduate from library to CLI: `new` opens a tab (loads `about:blank` by default, or `--url <URL>`); `close --tab <index|substring>` closes a tab (`--tab` is required because closing is destructive, so there is no implicit default); `switch [--tab <index|substring>]` brings a tab to the front (defaults to the first non-helper tab). Every verb accepts `--port` (auto-resolves like `navigate`/`snap`/`stop`) and `--quiet`/`-q`. Tab selection mirrors `navigate` (`--tab` is a 0-based index, negatives allowed, or a URL substring). A thin pass-through over the existing `cdp.open_tab` / `cdp.close_tab` / `cdp.switch_to_tab` helpers. Lands the root command list at 8 (`start | list | stop | navigate | snap | do | resize | tab`), the cap codified in [ADR 0001](docs/adr/0001-cli-interaction.md). The pre-existing `web-view navigate --new-tab` keeps working; `web-view tab new` is the preferred form for new code.

## [0.3.0] — 2026-05-28

### Added

- **`web-view resize --width <W> --height <H>`** — resize the OS Chrome window on a running CDP instance. Uses CDP `Browser.setWindowBounds`. Accepts the standard runtime flags (`--port`, `--tab <index|substring>`, `--quiet`/`-q`) and the resize-specific `--viewport` switch to override only the page viewport (via Playwright `set_viewport_size`) without touching the OS window.
- **`web-view start --window-size WxH`** — initial window size when launching Chrome. Replaces the previously hardcoded `--window-size=1920,1080` Chrome launch flag with one driven from the kwarg. Default unchanged (`1920x1080`).
- **Library helpers** in a new `cdp/_window.py` module:
  - `cdp.set_window_size(page, *, width, height)` — OS-level resize via CDP.
  - `cdp.set_viewport(page, *, width, height)` — page-level viewport override.
- `cdp.start_chrome(*, window_size=(1920, 1080), ...)` — new kwarg threaded through to the Chrome launch flag.

## [0.2.0] — 2026-05-28

### Added

- **`web-view do <verb>`** — element-interaction CLI family. Ten verbs graduate from library to CLI under a single parent: `click`, `fill`, `check`, `press`, `hover`, `dblclick`, `right-click`, `scroll-into-view`, `upload`, `drag`. Element addressing defaults to `--role + --name` (matches the `.aria.yaml` emitted by `web-view snap`); `--selector <css>` is the mutually exclusive escape hatch. Every verb accepts `--port` (auto-resolves like `navigate`/`snap`/`stop`), `--tab <index|substring>` (same semantics as `navigate`), `--timeout <seconds>` (default 15), and `--quiet`/`-q` to silence the success ack. `fill` reads its value from stdin when `--value` is omitted; `press` accepts a comma-separated chord list (`"Control+a,Backspace"`); `drag` uses a `role:name` micro-syntax for `--from`/`--to`. Closes the read-yaml → act loop from `web-view snap` without dropping into a Python REPL. Design recorded in [ADR 0001](docs/adr/0001-cli-interaction.md).
- Shared `cli/_shared.resolve_target_tab(context, selector)` extracted from `cli/_navigate._pick_tab` and reused by every `do <verb>` plus `navigate`.

## [0.1.0] — 2026-05-28

Initial tagged release. Captures the post-refactor stable surface.

### Changed (since last release)

- **`web-view navigate` and `web-view snap`** now treat `--port` as optional, mirroring `web-view stop`. When exactly one CDP Chrome instance is running, the command picks it automatically; with zero or 2+ instances it exits with the same structured error as `stop`, listing the candidate `--port` values. The port-resolution logic is now a single helper (`cli/_shared.resolve_single_port`) reused by all three subcommands.

### Added

- `web-view navigate --url <URL>` loads a URL in an already-running CDP Chrome. Picks the target tab via `--tab <index|substring>` (defaults to the first non-helper tab) or opens a fresh one with `--new-tab`. `--tab` and `--new-tab` are mutually exclusive.
- `web-view start --url <URL>` opens the given URL in the first tab right after Chrome becomes CDP-ready. Omitting the flag preserves the existing `about:blank` behaviour.
- `web-view list` now includes a `TABS` column with a per-tab tree of URLs and titles. Connection failure against a running instance shows `TABS: ?` instead of erroring out.
- `web-view snap` now prints the two output paths (PNG then ARIA YAML) as absolute paths on stdout, enabling shell composition (`web-view snap | head -1 | xargs open`).
- Test suite under `tests/` with full coverage of the new CLI behaviours.

### Changed

- **Library layout** — `web_view.cdp` is now a package split by responsibility: `_lifecycle`, `_connection`, `_navigation`, `_interaction`, `_files`, `_state`, `_snapshots`, `_console`, `_network`, plus a `_shared` module with helpers reused across them (locator + wait, localhost JSON probe, storage-kind guard). The public API is unchanged — `from web_view import cdp; cdp.click(...)` still works for every previous symbol.
- **CLI layout** — `web_view.cli` is now a package: one module per subcommand (`_start`, `_list`, `_stop`, `_navigate`, `_snap`) plus a `_shared` module for error printers and the running-instance guard. Each subcommand owns its own `register(subparsers)` and `EPILOG`.
- **`web-view -h`** follows the git / docker / gh pattern: short top-level listing (commands + library-mode hint, ~20 lines) with details delegated to `web-view <command> -h`. Each subcommand's `-h` carries its own examples, tab-selection cheatsheet (`navigate`), composability notes (`snap`), and `--port` behaviour (`stop`).
- `web-view stop` accepts no `--port` when exactly one CDP Chrome instance is running and stops it; with zero or multiple instances it errors out with explicit guidance.
- `web-view snap` makes the `slug` positional optional (defaults to `snap`) — `web-view snap` now writes `NN-snap.{png,aria.yaml}` using the next free index.
- **API renames** (positional callers unaffected; only kwarg callers need updates):
  - `cdp.goto(page, url=…)` → `cdp.goto(page, target_url=…)`
  - `cdp.open_tab(context, url=…)` → `cdp.open_tab(context, target_url=…)`
  - `cdp.set_cookie(context, …, url=…)` → `cdp.set_cookie(context, …, target_url=…)`
  - `cdp.screenshot(page, dest=…)` → `cdp.screenshot(page, destination=…)`
  - `cdp.aria_snapshot(page, dest=…)` → `cdp.aria_snapshot(page, destination=…)`
  - `cdp.capture_download(page, action, dest=…)` → `cdp.capture_download(page, action, destination=…)`
  - `cdp.dump_network(recorder, dest)` → `cdp.dump_network(recorder, destination)` (also: now returns the destination path, as the type annotation already claimed)
  - `NetworkEntry.url` → `NetworkEntry.request_url`

### Fixed

- `web-view snap` / `web-view stop` / `web-view navigate` against a port with no running CDP Chrome instance now produce a structured error message pointing at `web-view start` and `web-view list` instead of leaking the underlying Playwright traceback.
- `list_cdp_instances` is now split into platform-specific `_list_instances_unix` / `_list_instances_windows` helpers, dropping its previous over-the-limit cyclomatic complexity.
- `cdp` polling now uses `http.client.HTTPConnection` against an explicit `(host, port, path)` triple, replacing the previous `urllib.request.urlopen` call (which triggered linter warnings about unrestricted URL schemes despite always targeting localhost).
