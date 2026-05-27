# Changelog

All notable changes to this project will be documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `web-view start --url <URL>` opens the given URL in the first tab right after Chrome becomes CDP-ready. Omitting the flag preserves the existing `about:blank` behaviour.
- `web-view list` now includes a `TABS` column with a per-tab tree of URLs and titles. Connection failure against a running instance shows `TABS: ?` instead of erroring out.
- `web-view snap` now prints the two output paths (PNG then ARIA YAML) as absolute paths on stdout, enabling shell composition (`web-view snap | head -1 | xargs open`).
- `web-view -h` now includes a `Common workflow:` block and a `Library mode:` paragraph explaining that `uv tool install` does not expose `from web_view import cdp` to the host Python environment.
- Test suite under `tests/` with full coverage of the new CLI behaviours.

### Changed

- `web-view stop` accepts no `--port` when exactly one CDP Chrome instance is running and stops it; with zero or multiple instances it errors out with explicit guidance.
- `web-view snap` makes the `slug` positional optional (defaults to `snap`) — `web-view snap` now writes `NN-snap.{png,aria.yaml}` using the next free index.

### Fixed

- `web-view snap` / `web-view stop` against a port with no running CDP Chrome instance now produce a structured error message pointing at `web-view start` and `web-view list` instead of leaking the underlying Playwright traceback.
