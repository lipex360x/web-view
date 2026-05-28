# Changelog

All notable changes to this project will be documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
