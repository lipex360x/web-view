# web-view

[![Release](https://img.shields.io/github/v/release/lipex360x/web-view?label=release)](https://github.com/lipex360x/web-view/releases)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Project-agnostic toolkit for driving Chrome via the Chrome DevTools Protocol on top of Playwright's sync API. Wait on state, never on time.

> [!IMPORTANT]
> **Wait on state changes, never on time.** No `wait_for_timeout`, no `time.sleep`. `timeout_s=N` is always an upper bound — the call returns the instant the state changes.

## Contents

- [Why](#why)
- [Installation](#installation)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Library reference](#library-reference)
- [Conventions](#conventions)
- [Real-world recipes](#real-world-recipes)
- [Cross-platform notes](#cross-platform-notes)
- [Development](#development)
- [Project links](#project-links)
- [Acknowledgements](#acknowledgements)

---

## Why

Most browser automation tutorials sprinkle `sleep(2)` everywhere, then break under load. `web-view` enforces a different discipline:

- **Wait on the actual signal**: URL change, document ready, element visibility, network response, custom JS predicate.
- **Pick the right tab**: `context.pages[0]` under CDP can return `RotateCookies`, service workers, or devtools targets. Always use `find_page()` with a predicate.
- **Scope queries to a region**: pass a `Locator` (not a `Page`) for elements inside modals, where the same role+name appears elsewhere on the page.
- **Snapshot in pairs**: every UI state worth saving is captured as `NN-slug.png` (visual) + `NN-slug.aria.yaml` (selectors). Reproducible and diff-friendly.

## Installation

### As a CLI tool (recommended for ad-hoc use)

```bash
uv tool install git+https://github.com/lipex360x/web-view
```

This puts a `web-view` command on your `PATH`. Verify:

```bash
web-view --help
```

You also need the system Chrome (the CDP launcher talks to your real Chrome, not a Playwright-bundled one):

- **macOS**: <https://www.google.com/chrome/>
- **Linux**: `apt install google-chrome-stable` / `dnf install google-chrome` / etc.
- **Windows**: <https://www.google.com/chrome/>

And the Playwright Python binding (the library itself uses it internally):

```bash
uv tool install --with playwright git+https://github.com/lipex360x/web-view
```

### As a library inside another project

Add to your `pyproject.toml`:

```toml
dependencies = [
  "web-view @ git+https://github.com/lipex360x/web-view",
  "playwright>=1.40",
]
```

Or with `uv`:

```bash
uv add git+https://github.com/lipex360x/web-view
```

Then import:

```python
from web_view import cdp

with cdp.connect() as (browser, context):
    page = cdp.find_page(context, url_contains="example.com")
    cdp.click(page, "button", "Submit")
```

### One-off run (no install)

```bash
uv run --with git+https://github.com/lipex360x/web-view web-view list
```

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Quick start

### 1. Start a CDP Chrome

```bash
web-view start --port 9222 --user-data-dir ~/.cache/web-view/profile \
  --url file:///path/to/index.html
```

This launches your real Chrome with `--remote-debugging-port=9222` and a persistent profile (so cookies, logins, extensions survive across runs). The optional `--url` flag opens that URL in the first tab right after Chrome becomes CDP-ready. You can also do this manually:

```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/.cache/web-view/profile
```

Browse to whatever site you're researching. Log in, navigate, click around. Your session is now live and addressable from Python.

### 2. List what's running

```bash
web-view list
```

```
    PID   PORT  USER_DATA_DIR                              TABS
  41822   9222  /Users/you/.cache/web-view/profile         2
                                                            ├─ file:///path/to/index.html  "Home"
                                                            └─ chrome://newtab
```

Each running instance is queried over CDP for its open tabs. If the instance refuses the short-lived connection (mid-shutdown, busy), the `TABS` column shows `?` instead of erroring out.

### 3. Snapshot any tab

```bash
web-view snap homepage --url-contains example.com --destination-dir ./captures
```

You get `captures/01-homepage.png` + `captures/01-homepage.aria.yaml`. The PNG is for humans (review what you saw). The ARIA YAML is for selectors — it dumps the accessibility tree so you can find any element by `role` + accessible `name` without hunting for CSS selectors.

The command prints the two absolute paths to stdout (PNG first, ARIA YAML second), so you can pipe them straight into other tools:

```bash
$ web-view snap homepage --url-contains example.com
/Users/you/captures/01-homepage.png
/Users/you/captures/01-homepage.aria.yaml

$ web-view snap | head -1 | xargs open   # auto-slug + open the PNG
```

The slug is optional: `web-view snap` (no positional) writes `NN-snap.{png,aria.yaml}` using the next free index.

### 4. Click, fill, and press without leaving the shell

`web-view snap` emits selectors as `role + name` pairs in the YAML — `web-view do <verb>` speaks the same vocabulary, so the read-yaml → act loop never needs a Python REPL:

```bash
web-view snap login                                       # captures 01-login.aria.yaml
# In the YAML: `- button "Sign in"`, `- textbox "Email"`
web-view do fill --role textbox --name "Email" --value "alice@example.com"
web-view do fill --role textbox --name "Password" --value "secret"
web-view do click --role button --name "Sign in"
web-view snap after-login                                 # captures the new state
```

Every interaction verb (`click`, `fill`, `check`, `press`, `hover`, `dblclick`, `right-click`, `scroll-into-view`, `upload`, `drag`) accepts the same options: `--port`/`--tab` for instance + tab targeting, `--timeout` for the upper bound on element waits, `--quiet`/`-q` to silence the one-line success ack. CSS-first workflows use `--selector <css>` instead of `--role/--name`. See `web-view do -h` for the verb list and `web-view do <verb> -h` for per-command details.

### 5. Open, snapshot, and close tabs

```bash
web-view tab new --url https://example.com   # opens a fresh tab on the URL
web-view snap example --url-contains example.com
web-view tab close --tab example.com         # close it again when done
```

`tab close` requires `--tab` on purpose (closing is destructive). `tab switch [--tab <index|substring>]` brings a background tab to the front; with no `--tab` it focuses the first non-helper tab.

### 6. Drive it from Python

```python
from web_view import cdp

with cdp.connect(port=9222) as (browser, context):
    page = cdp.find_page(context, url_contains="example.com")
    cdp.goto(page, "https://example.com/products")

    cdp.fill(page, "textbox", "Search", "wireless mouse")
    cdp.press(page, "Enter")

    cdp.wait_for_url(page, lambda url: "/results" in url, timeout_s=10)
    cdp.dual_snapshot(page, "search-results", dest_dir="./captures")
```

### 7. Stop the Chrome you started

```bash
web-view stop --port 9222
```

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## CLI reference

```
web-view --version | -v           # print the installed version and exit
web-view start    [--port 9222] [--user-data-dir DIR] [--headless] [--url URL]
                  [--window-size WxH]              # default 1920x1080
web-view list
web-view navigate --url URL [--port 9222] [--tab <index|substring> | --new-tab]
web-view stop     [--port PORT]   # omit --port when exactly one instance is running
web-view snap     [slug]          # slug defaults to "snap"
                  [--port 9222] [--url-contains STR] [--destination-dir DIR]
web-view do       <verb>          # click | fill | check | press | hover | dblclick |
                                  # right-click | scroll-into-view | upload | drag
                  [--role R --name N | --selector CSS]
                  [--port P] [--tab T] [--timeout S] [--quiet]
web-view resize   --width W --height H              # OS window (default)
                  [--viewport]                      # page viewport only
                  [--port P] [--tab T] [--quiet]
web-view tab      <verb>          # new | close | switch
                  new    [--url URL]               # opens about:blank by default
                  close  --tab <index|substring>   # --tab required (destructive)
                  switch [--tab <index|substring>] # defaults to first non-helper tab
                  [--port P] [--quiet]
```

`web-view navigate` reuses an existing CDP Chrome. Without `--tab` / `--new-tab` it targets the first non-helper tab (the same tab `start --url` would touch). `--tab` accepts either a 0-based index (negatives count from the end) or a URL substring; `--new-tab` opens a fresh tab instead. The two flags are mutually exclusive.

`web-view snap` prints two absolute paths to stdout (PNG then ARIA YAML) so the call is composable with `head`, `xargs`, etc. Missing pre-conditions (no CDP Chrome on the given port, multiple instances when `--port` is omitted) produce structured guidance on stderr instead of raw Playwright tracebacks — this applies to `snap`, `stop`, `navigate`, and every `do <verb>`.

`web-view do <verb>` is the no-Python convenience layer over the library's interaction helpers. Element addressing defaults to `--role + --name` (the same vocabulary `web-view snap` writes into the ARIA YAML); `--selector <css>` is the mutually exclusive escape hatch for CSS-first workflows. Per-verb specifics: `fill` reads stdin when `--value` is omitted (`web-view do fill --role textbox --name Body < message.txt`); `press` accepts a comma-separated chord list (`--keys "Control+a,Backspace"`); `drag` uses a `role:name` micro-syntax (`--from "button:Item" --to "region:Trash"`); `upload` requires `--file <path>`. Every verb prints a one-line success ack on stdout (silenced with `--quiet`).

`web-view resize` resizes a running Chrome window. Default mode targets the OS-level window (Chrome physically grows or shrinks on the desktop) via CDP `Browser.setWindowBounds`. `--viewport` switches to a page-only viewport override — useful for responsive-layout testing without disturbing the window manager. The initial size is controlled by `web-view start --window-size WxH` (default `1920x1080`).

`web-view tab <verb>` manages the tab lifecycle as a thin pass-through to the library's `cdp.open_tab` / `cdp.close_tab` / `cdp.switch_to_tab` helpers. `tab new` opens a fresh tab (`about:blank` unless `--url` is given) and is the preferred form for new code over `navigate --new-tab` (which keeps working). `tab close` requires `--tab` on purpose: closing is destructive, so there is no implicit "first tab" default that could discard a logged-in session by accident. `tab switch` is non-destructive and therefore defaults to the first non-helper tab when `--tab` is omitted. Tab selection mirrors `navigate`: a 0-based index (negatives count from the end) or a URL substring.

For programmatic use, the CLI is just a wrapper — everything is exposed via `from web_view import cdp`.

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Library reference

> [Chrome lifecycle](#chrome-lifecycle) · [Connect + tab selection](#connect--tab-selection) · [Navigation + waiting](#navigation--waiting) · [Element interaction](#element-interaction-by-aria-role--name) · [Downloads + uploads](#downloads--uploads) · [Cookies + storage + clipboard](#cookies--storage--clipboard) · [Snapshots + inspection](#snapshots--inspection) · [Recording console + network](#recording-console--network)

### Chrome lifecycle

```python
cdp.start_chrome(*, port=9222, user_data_dir, headless=False, extra_args=None, binary=None) -> Popen
cdp.is_cdp_ready(port, *, timeout_s=15) -> bool
cdp.wait_for_chrome_stopped(port, *, timeout_s=15) -> bool
cdp.stop_chrome(*, port=None, pid=None, process=None) -> int      # exactly one of the three
cdp.list_cdp_instances() -> list[CdpInstance]                      # cross-platform
```

`CdpInstance` is a dataclass with `pid`, `port`, `user_data_dir`, `cmdline`. The `list_cdp_instances()` function filters out Chrome helper processes (renderer, GPU, network) that inherit the parent's `--remote-debugging-port=` cmdline.

### Connect + tab selection

```python
with cdp.connect(port=9222) as (browser, context):    # context manager
    pages = cdp.pages_info(context)                    # [{"url": ..., "title": ...}, ...]

    # Pick a tab. Never use context.pages[0] — it can be RotateCookies.
    page = cdp.find_page(context, url_contains="example.com")
    page = cdp.find_page(context, predicate=lambda url: "checkout" in url and "/v2/" in url)

    new = cdp.open_tab(context, "https://example.com/other")
    page = cdp.switch_to_tab(context, url_contains="example.com/other")
    cdp.close_tab(page)
```

### Navigation + waiting

```python
cdp.goto(page, target_url, *, wait_until="domcontentloaded")
cdp.wait_for_url(page, predicate, *, timeout_s=60) -> str
cdp.back(page) / cdp.forward(page) / cdp.reload(page)
```

`predicate` is a `Callable[[str], bool]` — receives the current URL, returns True when you're ready to proceed. The call returns the matched URL instantly when the predicate flips true.

### Element interaction (by ARIA role + name)

All interaction helpers take `(root, role, name, *, exact=True, timeout_s=15)`. `root` can be a `Page` (whole page) or a `Locator` (scoped to a region — essential for modal dialogs):

```python
cdp.click(root, role, name)
cdp.fill(root, role, name, value)
cdp.check(root, role, name)               # idempotent — won't toggle if already checked
cdp.press(page, "Enter", "Tab")
cdp.scroll_into_view(root, role, name)
cdp.hover(root, role, name)
cdp.dblclick(root, role, name)
cdp.right_click(root, role, name)
cdp.drag(page, source=("button", "Item A"), target=("region", "Trash"))

cdp.set_window_size(page, width=1280, height=720)   # OS window via CDP
cdp.set_viewport(page, width=1280, height=720)      # page-rendering viewport only
```

`name` accepts a string (exact match by default) or a `re.Pattern` (use regex when the accessible name has trailing whitespace, multi-language strings, or partial matches).

**Scoping example** — when a "Save" button appears both in the page and a confirmation dialog:

```python
dialog = page.get_by_role("dialog", name="Add users")
dialog.wait_for(state="visible")
cdp.fill(dialog, "textbox", "Email", "user@example.com")
cdp.click(dialog, "button", "Save")
```

### Downloads + uploads

```python
saved = cdp.capture_download(
    page,
    action=lambda: cdp.click(page, "button", "Download report"),
    destination=Path("./downloads/report.pdf"),
    timeout_s=30,
)

cdp.upload(page, "button", "Choose file", ["/path/to/file.pdf"])
```

### Cookies + storage + clipboard

```python
cookies = cdp.get_cookies(context, urls=["https://example.com"])
cdp.set_cookie(context, name="session", value="abc", target_url="https://example.com")
cdp.clear_cookies(context)

ls = cdp.get_storage(page, kind="local")
cdp.set_storage_item(page, "k", "v", kind="session")
cdp.clear_storage(page, kind="local")

text = cdp.read_clipboard(page)            # needs clipboard-read permission
cdp.write_clipboard(page, "hello")
```

### Snapshots + inspection

```python
png_path, aria_path = cdp.dual_snapshot(page, "checkout", dest_dir=Path("./captures"))
# captures/01-checkout.png  +  captures/01-checkout.aria.yaml

cdp.screenshot(page, Path("./captures/full.png"), full_page=True)
yaml_text = cdp.aria_snapshot(page, destination=Path("./captures/page.aria.yaml"))

html = cdp.get_html(page)                                       # full document
html = cdp.get_html(page, locator=page.get_by_role("main"))     # one element

details = cdp.inspect_element(page, "button", "Submit")
# {"outer_html": ..., "tag": "button", "id": ..., "classes": [...], "attrs": {...},
#  "bounding_box": {x, y, width, height}, "is_visible": True, "is_enabled": True}
```

The numeric prefix `NN-` in dual snapshots is auto-assigned by scanning the destination directory — your snapshots end up in capture order.

### Recording console + network

```python
with cdp.console_recorder(page) as recorder:
    cdp.click(page, "button", "Submit")
    cdp.wait_for_url(page, lambda url: "/done" in url)

print([event.text for event in recorder.errors])

with cdp.network_recorder(page, url_predicate=lambda url: "/api/" in url) as recorder:
    cdp.click(page, "button", "Load more")
    cdp.wait_for_url(page, lambda url: "/results" in url)

for entry in recorder.filter(method="POST", status=200):
    print(entry.request_url, entry.response_json)

cdp.dump_network(recorder, Path("./captures/network.json"))
```

`NetworkRecorder` automatically parses JSON response bodies. `entry.response_json` is the parsed object; `entry.response_body` is the raw text/bytes fallback. `recorder.failed` returns entries that errored or returned 4xx/5xx.

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Conventions

| Rule | Why |
|---|---|
| First arg is always the Playwright object | Never reads global state. Easy to test and compose. |
| URLs as strings, predicates as `Callable[[str], bool]` | Predicates beat substring matches for anything non-trivial. |
| Timeouts in seconds at the API boundary | Playwright uses ms internally; this converts. |
| Snapshots are pairs (`.png` + `.aria.yaml`) | PNG for review, ARIA YAML for stable selectors. |
| Element helpers accept `Page` OR `Locator` as `root` | Scope to a region for modal dialogs. |

### Anti-patterns and replacements

| Anti-pattern | Replacement |
|---|---|
| `page.wait_for_timeout(5000)` | `page.locator("h1").wait_for(state="visible")` |
| `time.sleep(2); click_next()` | `cdp.wait_for_url(page, predicate, timeout_s=30)` |
| `sleep(N)` hoping content renders | `page.wait_for_load_state("load")` |
| Polling URL with `sleep` | `page.wait_for_url(predicate)` |
| `sleep(N)` waiting for network | `cdp.network_recorder` + wait on the request |

Fixed waits are simultaneously **too slow** (you wait the full duration even when ready in milliseconds) AND **too fragile** (you guess "enough time" and it breaks under load).

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Real-world recipes

### Drive a multi-step form

```python
from pathlib import Path
from web_view import cdp

with cdp.connect() as (browser, context):
    page = cdp.find_page(context, url_contains="example.com/signup")

    cdp.fill(page, "textbox", "Email", "alice@example.com")
    cdp.fill(page, "textbox", "Password", "••••••••")
    cdp.check(page, "checkbox", "I agree to the terms")
    cdp.click(page, "button", "Continue")

    cdp.wait_for_url(page, lambda url: "/verify" in url, timeout_s=15)
    cdp.dual_snapshot(page, "after-signup", dest_dir=Path("./captures"))
```

### Capture an XHR response after clicking

```python
from web_view import cdp

with cdp.connect() as (_, context):
    page = cdp.find_page(context, url_contains="dashboard")
    with cdp.network_recorder(page, url_predicate=lambda url: "/api/orders" in url) as recorder:
        cdp.click(page, "button", "Refresh")
        cdp.wait_for_url(page, lambda url: "/dashboard" in url)

    orders = next(
        (entry.response_json for entry in recorder.entries if entry.is_json()),
        None,
    )
    print(orders)
```

### Manual login, then automate

A common pattern for research: open Chrome headed, log in manually (handle 2FA, CAPTCHAs, etc.), then attach a Python script to the live session.

```bash
# Terminal 1
web-view start --port 9222
# Now log into the target site in the visible Chrome window.

# Terminal 2 (after you're logged in)
python my_script.py
```

In `my_script.py`:

```python
from web_view import cdp

with cdp.connect(port=9222) as (_, context):
    page = cdp.find_page(context, url_contains="target-site.com")
    ...
```

### Iterate selector authoring against a live page

```python
from web_view import cdp

with cdp.connect() as (_, context):
    page = cdp.find_page(context, url_contains="target.com")

    # Dump the role/name tree to YAML for offline browsing.
    cdp.aria_snapshot(page, destination=Path("./scratch/tree.yaml"))

    # Inspect a candidate element.
    print(cdp.inspect_element(page, "link", "Sign in"))
```

Open `scratch/tree.yaml` in your editor — every element shows up as `- role "name"`. Pick the one you want, write the selector, re-run.

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Cross-platform notes

- **Chrome path** is auto-detected via `_resolve_chrome_binary()`:
  - macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
  - Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe` (and `(x86)`)
  - Linux: `which google-chrome | chromium-browser | chromium | chrome`
  - Override via `cdp.start_chrome(binary="/custom/path")`.
- **Process control** uses `pkill`/`os.killpg` on Unix and `taskkill`/`process.terminate()` on Windows. No manual platform branching needed in your code.
- **User profile dir**: pick anywhere persistent. `~/.cache/web-view/profile` is the CLI default. Keep one per research project to avoid cross-contaminating logins.

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Development

Clone, install in editable mode, hook up `dev-quality`:

```bash
git clone https://github.com/lipex360x/web-view
cd web-view
uv sync --extra dev
uv run pre-commit install
```

The pre-commit config uses [`dev-quality`](https://github.com/lipex360x/dev-quality) `v0.15.3` — same `check-all` (abbreviation linter, comment linter, complexity / size caps, ruff check, ruff format) that drives the rest of the `lipex360x` ecosystem. Run it manually with:

```bash
uv run pre-commit run --all-files
```

Tests:

```bash
uv run pytest
```

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Project links

- **Releases & changelog:** <https://github.com/lipex360x/web-view/releases>
- **Design decisions (ADRs):** [`docs/adr/`](docs/adr/) — start with [`0001-cli-interaction.md`](docs/adr/0001-cli-interaction.md) (records the `web-view do <verb>` family design).
- **Issue tracker:** <https://github.com/lipex360x/web-view/issues>
- **AI contributor guide:** [`CLAUDE.md`](CLAUDE.md) — the executable spec a fresh AI session should read before touching the repo.

<div align="right"><a href="#contents">↑ Back to top</a></div>

---

## Acknowledgements

`web-view` was extracted from the [`claude-brain`](https://github.com/lipex360x/claude-brain) repo where it grew up driving the GCP Console headed-Chrome bootstrap for the GWS integration. The discipline of "wait on state, never on time" came from too many flaky `sleep(2)` debugging sessions on that flow.

<div align="right"><a href="#contents">↑ Back to top</a></div>

## License

MIT — see [LICENSE](LICENSE).
