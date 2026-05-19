"""cdp.py — reusable helpers for driving a Chrome instance over CDP.

Designed to be project-agnostic: nothing here knows about GCP, GWS, or any
specific site. Higher layers (e.g. step_02_create_project.py) compose these
into flow-specific scripts.

================================================================================
GOLDEN RULE: WAIT FOR STATE CHANGES, NEVER FOR TIME
================================================================================

If you're tempted to write `page.wait_for_timeout(ms)`, `time.sleep(seconds)`,
or any fixed-duration delay anywhere in code that uses this library — STOP.
Express the actual state change you're waiting for:

    BAD:                                  GOOD:
    page.wait_for_timeout(5000)           page.locator("h1").wait_for(state="visible")
    time.sleep(2); click_next()           cdp.wait_for_url(page, predicate, timeout_s=30)
    sleep(N) hoping content renders       page.wait_for_load_state("load"|"domcontentloaded")
    poll url with sleep                   page.wait_for_url(predicate)
    sleep(N) hoping network finishes      cdp.network_recorder + wait on the request

Fixed waits are simultaneously too slow (you wait full duration even when ready
in ms) AND too fragile (you guess "enough time" and it breaks under load).
They are the worst of both worlds. Always wait on:

  - URL change            → `page.wait_for_url(predicate)` or `cdp.wait_for_url`
  - Document ready        → `page.wait_for_load_state("load"|"domcontentloaded")`
  - Specific element      → `locator.wait_for(state="visible"|"attached"|"hidden")`
  - Network response      → `page.expect_response(predicate)` or `cdp.network_recorder`
  - Custom JS predicate   → `page.wait_for_function(js_expression)`

`timeout_s=N` on cdp.* helpers is an UPPER BOUND for protection, not a delay —
the call returns the instant the state changes.

================================================================================
OTHER CONVENTIONS
================================================================================

- Every function takes the Playwright object it needs (Page, BrowserContext)
  as the first positional argument — never reads global state.
- URLs are passed as strings; predicates as callables `(url: str) -> bool`.
- Timeouts are in seconds at this API boundary (Playwright uses ms internally;
  we convert).
- All snapshot/screenshot functions take a `dest` path and return it for
  chaining.
- Never trust `context.pages[0]` — Chrome via CDP exposes auxiliary targets
  (RotateCookies, service workers, devtools). Use `find_page(...)` with a
  `url_contains=` or `predicate=` to pick the right tab.
- A "snapshot" is a PAIR: `.png` (visual) + `.aria.yaml` (selectors). Always
  capture both via `dual_snapshot(page, slug, dest_dir=...)` (or the CLI
  wrapper `scripts/snap.py <slug>`). Standalone `screenshot()` or
  `aria_snapshot()` only when you explicitly want one without the other.
- Element interaction helpers (click, fill, check, hover, …) accept either a
  Page or a Locator as the first arg. Use a Locator to scope a query to a
  specific region; this is more reliable than querying from `page` for
  elements inside an aria-modal dialog. Example:

      dialog = page.get_by_role("dialog", name="Add users")
      dialog.wait_for(state="visible")
      cdp.fill(dialog, "textbox", "Text field for emails", "user@x.com")
      cdp.click(dialog, "button", "Save")

================================================================================
TYPICAL USAGE
================================================================================

    import cdp

    with cdp.connect() as (browser, context):
        page = cdp.find_page(context, url_contains="example.com")
        cdp.goto(page, "https://example.com/form")
        page.locator("input[name=email]").wait_for(state="visible")
        cdp.fill(page, "textbox", "Email", "user@x.com")
        cdp.click(page, "button", "Submit")
        cdp.wait_for_url(page, lambda u: "/done" in u, timeout_s=30)
        cdp.dual_snapshot(page, "after-submit", dest_dir=Path("captures"))
"""

from __future__ import annotations

import contextlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

DEFAULT_CDP_PORT = 9222
CDP_URL = f"http://localhost:{DEFAULT_CDP_PORT}"


def _resolve_chrome_binary() -> str:
    """Locate the system Chrome / Chromium binary cross-platform."""
    system = platform.system()
    if system == "Darwin":
        candidate = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if Path(candidate).exists():
            return candidate
    if system == "Windows":
        for candidate in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ):
            if Path(candidate).exists():
                return candidate
    for name in ("google-chrome", "chromium-browser", "chromium", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(
        "Chrome not found. Install Google Chrome or Chromium and ensure it's on PATH."
    )


def is_cdp_ready(port: int, *, timeout_s: int = 15) -> bool:
    """Poll `http://localhost:<port>/json/version` until it responds (or timeout)."""
    deadline = time.time() + timeout_s
    url = f"http://localhost:{port}/json/version"
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def wait_for_chrome_stopped(port: int, *, timeout_s: int = 15) -> bool:
    """Inverse of `is_cdp_ready`: wait until the port is no longer responding.

    Returns True if Chrome has actually stopped within `timeout_s`, False on
    timeout. Polls the actual state and returns the instant it changes.
    """
    deadline = time.time() + timeout_s
    url = f"http://localhost:{port}/json/version"
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).read()
            time.sleep(0.3)
        except Exception:
            return True
    return False


def start_chrome(
    *,
    port: int = DEFAULT_CDP_PORT,
    user_data_dir: str | Path,
    headless: bool = False,
    extra_args: list[str] | None = None,
    binary: str | None = None,
) -> subprocess.Popen:
    """Launch Chrome with CDP on `port` and a persistent `user_data_dir`.

    Returns the spawned Popen. Chrome runs in its own process group on Unix
    so it survives the Python parent exiting.
    """
    if is_cdp_ready(port, timeout_s=1):
        raise RuntimeError(f"port {port} already has a CDP-listening Chrome")
    cmd = [
        binary or _resolve_chrome_binary(),
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={user_data_dir}",
        "--window-size=1920,1080",
    ]
    if headless:
        cmd.append("--headless=new")
    if extra_args:
        cmd.extend(extra_args)
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if platform.system() != "Windows":
        popen_kwargs["preexec_fn"] = os.setsid
    process = subprocess.Popen(cmd, **popen_kwargs)
    if not is_cdp_ready(port, timeout_s=15):
        process.terminate()
        raise RuntimeError(f"Chrome on port {port} did not become CDP-ready in 15s")
    return process


@dataclass
class CdpInstance:
    pid: int
    port: int
    user_data_dir: str | None
    cmdline: str


def list_cdp_instances() -> list[CdpInstance]:
    """Return every Chrome process currently exposing a --remote-debugging-port.

    Filters out helper sub-processes (renderer/GPU/network) that inherit the
    parent's cmdline. Returns one CdpInstance per real listening Chrome.
    """
    system = platform.system()
    results: list[CdpInstance] = []
    rdp_re = re.compile(r"--remote-debugging-port=(\d+)")
    udd_re = re.compile(r'--user-data-dir=("([^"]+)"|(\S+))')
    helper_markers = (" --type=", "Chrome Helper", "Chromium Helper")

    if system == "Windows":
        cp = subprocess.run(
            ["wmic", "process", "where",
             "name='chrome.exe'", "get", "processid,commandline", "/format:csv"],
            capture_output=True, text=True, check=False,
        )
        for line in cp.stdout.splitlines():
            parts = line.split(",")
            if len(parts) < 3:
                continue
            cmdline = ",".join(parts[1:-1])
            try:
                pid = int(parts[-1].strip())
            except ValueError:
                continue
            rdp = rdp_re.search(cmdline)
            if not rdp:
                continue
            udd = udd_re.search(cmdline)
            results.append(CdpInstance(
                pid=pid, port=int(rdp.group(1)),
                user_data_dir=(udd.group(2) or udd.group(3)) if udd else None,
                cmdline=cmdline,
            ))
        return results

    cp = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        capture_output=True, text=True, check=False,
    )
    for line in cp.stdout.splitlines():
        line = line.strip()
        rdp = rdp_re.search(line)
        if not rdp:
            continue
        if any(marker in line for marker in helper_markers):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmdline = parts[1]
        udd = udd_re.search(cmdline)
        results.append(CdpInstance(
            pid=pid, port=int(rdp.group(1)),
            user_data_dir=(udd.group(2) or udd.group(3)) if udd else None,
            cmdline=cmdline,
        ))
    return results


def stop_chrome(
    *,
    port: int | None = None,
    pid: int | None = None,
    process: subprocess.Popen | None = None,
) -> int:
    """Terminate Chrome by port, pid, or Popen handle. Returns count killed.

    Exactly one of `port`, `pid`, or `process` must be given.
    """
    given = sum(x is not None for x in (port, pid, process))
    if given != 1:
        raise ValueError("pass exactly one of port=, pid=, process=")

    if process is not None:
        try:
            if platform.system() == "Windows":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            return 1
        except (ProcessLookupError, PermissionError):
            return 0

    target_pids: list[int] = []
    if pid is not None:
        target_pids = [pid]
    elif port is not None:
        target_pids = [inst.pid for inst in list_cdp_instances() if inst.port == port]
    if not target_pids:
        return 0

    killed = 0
    for target in target_pids:
        try:
            os.kill(target, signal.SIGTERM)
            killed += 1
        except (ProcessLookupError, PermissionError):
            continue
    return killed


@contextlib.contextmanager
def connect(
    cdp_url: str | None = None,
    *,
    port: int | None = None,
) -> Iterator[tuple[Any, Any]]:
    """Open a Playwright connection to a running Chrome.

    Priority for picking the target:
      1. `port=N` → `http://localhost:N`
      2. `cdp_url="http://host:port"` → explicit URL
      3. neither → CDP_URL default (port 9222).

    Yields `(browser, context)`. Use `find_page(context, …)` to pick a tab.
    Chrome keeps running after this context exits.
    """
    if port is not None:
        cdp_url = f"http://localhost:{port}"
    elif cdp_url is None:
        cdp_url = CDP_URL

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        if not browser.contexts:
            raise RuntimeError(f"no contexts on CDP at {cdp_url}")
        yield browser, browser.contexts[0]


def pages_info(context: Any) -> list[dict[str, str]]:
    """Return a list of `{url, title}` dicts for every page in the context."""
    info: list[dict[str, str]] = []
    for page in context.pages:
        try:
            info.append({"url": page.url, "title": page.title()})
        except Exception:
            info.append({"url": getattr(page, "url", ""), "title": ""})
    return info


def find_page(
    context: Any,
    *,
    url_contains: str | None = None,
    predicate: Callable[[str], bool] | None = None,
) -> Any:
    """Return the first page matching `url_contains` or `predicate`.

    If both are given, `predicate` wins. If neither matches, returns None.
    """
    if url_contains is None and predicate is None:
        raise ValueError("pass either url_contains or predicate")
    check = predicate or (lambda url: url_contains in url)
    for page in context.pages:
        try:
            if check(page.url):
                return page
        except Exception:
            continue
    return None


def open_tab(context: Any, url: str, *, wait_until: str = "domcontentloaded") -> Any:
    """Open a new tab and navigate to `url`. Returns the new Page."""
    page = context.new_page()
    page.goto(url, wait_until=wait_until)
    return page


def switch_to_tab(context: Any, *, url_contains: str) -> Any:
    """Bring the tab whose URL contains `url_contains` to the front. Returns it."""
    page = find_page(context, url_contains=url_contains)
    if page is None:
        raise RuntimeError(f"no tab found with url containing {url_contains!r}")
    page.bring_to_front()
    return page


def close_tab(page: Any) -> None:
    page.close()


def goto(page: Any, url: str, *, wait_until: str = "domcontentloaded") -> None:
    """Navigate `page` to `url`. Thin wrapper that sets a sane default wait."""
    page.goto(url, wait_until=wait_until)


def wait_for_url(
    page: Any,
    predicate: Callable[[str], bool],
    *,
    timeout_s: float = 60,
) -> str:
    """Wait until `predicate(page.url)` is true. Event-driven (no polling).

    Returns the URL once matched. Raises on timeout.
    """
    page.wait_for_url(predicate, timeout=int(timeout_s * 1000))
    return page.url


def _locator_by_role(root: Any, role: str, name: Any, *, exact: bool) -> Any:
    if isinstance(name, re.Pattern):
        return root.get_by_role(role, name=name)
    return root.get_by_role(role, name=name, exact=exact)


def click(
    root: Any,
    role: str,
    name: Any,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Click the element with accessible role + name.

    `root` may be a Page or a Locator (use a Locator to scope to a region).
    `name` may be a string (matched exactly when `exact=True`) or a regex.
    """
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state="visible", timeout=int(timeout_s * 1000))
    locator.click()


def fill(
    root: Any,
    role: str,
    name: Any,
    value: str,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Fill the input with accessible role + name. Clears existing content first."""
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state="visible", timeout=int(timeout_s * 1000))
    locator.fill(value)


def check(
    root: Any,
    role: str,
    name: Any,
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Tick a checkbox / radio / switch with accessible name. Idempotent."""
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state="visible", timeout=int(timeout_s * 1000))
    if not locator.is_checked():
        locator.check()


def press(page: Any, *keys: str) -> None:
    """Send keyboard key(s). Single key or chord, e.g. press(page, "Control+a")."""
    for key in keys:
        page.keyboard.press(key)


def scroll_into_view(root: Any, role: str, name: str, *, exact: bool = True) -> None:
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.scroll_into_view_if_needed()


def hover(root: Any, role: str, name: str, *, exact: bool = True, timeout_s: float = 15) -> None:
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state="visible", timeout=int(timeout_s * 1000))
    locator.hover()


def dblclick(root: Any, role: str, name: str, *, exact: bool = True, timeout_s: float = 15) -> None:
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state="visible", timeout=int(timeout_s * 1000))
    locator.dblclick()


def right_click(root: Any, role: str, name: str, *, exact: bool = True, timeout_s: float = 15) -> None:
    locator = _locator_by_role(root, role, name, exact=exact)
    locator.wait_for(state="visible", timeout=int(timeout_s * 1000))
    locator.click(button="right")


def drag(
    page: Any,
    *,
    source: tuple[str, str],
    target: tuple[str, str],
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Drag the source element onto the target. Both as (role, name) pairs."""
    src = _locator_by_role(page, source[0], source[1], exact=exact)
    dst = _locator_by_role(page, target[0], target[1], exact=exact)
    src.wait_for(state="visible", timeout=int(timeout_s * 1000))
    dst.wait_for(state="visible", timeout=int(timeout_s * 1000))
    src.drag_to(dst)


def back(page: Any, *, wait_until: str = "domcontentloaded") -> None:
    page.go_back(wait_until=wait_until)


def forward(page: Any, *, wait_until: str = "domcontentloaded") -> None:
    page.go_forward(wait_until=wait_until)


def reload(page: Any, *, wait_until: str = "domcontentloaded") -> None:
    page.reload(wait_until=wait_until)


def capture_download(
    page: Any,
    action: Callable[[], None],
    *,
    dest: Path | None = None,
    timeout_s: float = 30,
) -> Path:
    """Run `action()`, capture any download it triggers, save to `dest`.

    If `dest` is None, the download is saved to a temp path with the
    suggested filename. Returns the final saved path.
    """
    with page.expect_download(timeout=int(timeout_s * 1000)) as info:
        action()
    download = info.value
    if dest is None:
        from tempfile import gettempdir
        dest = Path(gettempdir()) / download.suggested_filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(str(dest))
    return dest


def upload(
    page: Any,
    role: str,
    name: str,
    file_paths: str | Path | list[str | Path],
    *,
    exact: bool = True,
    timeout_s: float = 15,
) -> None:
    """Attach one or more files to an input[type=file] element."""
    locator = _locator_by_role(page, role, name, exact=exact)
    locator.wait_for(state="attached", timeout=int(timeout_s * 1000))
    paths = [str(p) for p in (file_paths if isinstance(file_paths, list) else [file_paths])]
    locator.set_input_files(paths)


def get_cookies(context: Any, *, urls: list[str] | None = None) -> list[dict[str, Any]]:
    """Return the context's cookies, optionally filtered to `urls`."""
    if urls:
        return list(context.cookies(urls))
    return list(context.cookies())


def set_cookie(
    context: Any,
    *,
    name: str,
    value: str,
    url: str | None = None,
    domain: str | None = None,
    path: str = "/",
    expires: float | None = None,
    http_only: bool = False,
    secure: bool = False,
    same_site: str | None = None,
) -> None:
    """Add a single cookie. Either `url` or (`domain` + `path`) must be set."""
    cookie: dict[str, Any] = {"name": name, "value": value, "path": path}
    if url is not None:
        cookie["url"] = url
    if domain is not None:
        cookie["domain"] = domain
    if expires is not None:
        cookie["expires"] = expires
    if http_only:
        cookie["httpOnly"] = True
    if secure:
        cookie["secure"] = True
    if same_site is not None:
        cookie["sameSite"] = same_site
    context.add_cookies([cookie])


def clear_cookies(context: Any) -> None:
    context.clear_cookies()


def get_storage(page: Any, *, kind: str = "local") -> dict[str, str]:
    """Dump localStorage (kind='local') or sessionStorage (kind='session')."""
    if kind not in ("local", "session"):
        raise ValueError("kind must be 'local' or 'session'")
    store = f"{kind}Storage"
    return page.evaluate(
        f"() => {{ const out = {{}}; for (let i = 0; i < {store}.length; i++) "
        f"{{ const k = {store}.key(i); out[k] = {store}.getItem(k); }} return out; }}"
    )


def set_storage_item(page: Any, key: str, value: str, *, kind: str = "local") -> None:
    if kind not in ("local", "session"):
        raise ValueError("kind must be 'local' or 'session'")
    page.evaluate(
        f"([k, v]) => {kind}Storage.setItem(k, v)",
        [key, value],
    )


def clear_storage(page: Any, *, kind: str = "local") -> None:
    if kind not in ("local", "session"):
        raise ValueError("kind must be 'local' or 'session'")
    page.evaluate(f"() => {kind}Storage.clear()")


def read_clipboard(page: Any) -> str:
    """Read the OS clipboard from the page context.

    Requires `clipboard-read` permission on the BrowserContext.
    """
    return page.evaluate("() => navigator.clipboard.readText()")


def write_clipboard(page: Any, text: str) -> None:
    """Write `text` to the OS clipboard from the page context."""
    page.evaluate("(t) => navigator.clipboard.writeText(t)", text)


def screenshot(page: Any, dest: Path, *, full_page: bool = True) -> Path:
    """Save a PNG screenshot of `page` to `dest`. Returns `dest`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(dest), full_page=full_page)
    return dest


def aria_snapshot(page: Any, dest: Path | None = None) -> str:
    """Return Playwright's ARIA snapshot (YAML). Optionally write to `dest`."""
    text = page.aria_snapshot()
    if dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text + "\n", encoding="utf-8")
    return text


def next_index(dest_dir: Path) -> int:
    """Return the next numeric prefix to use for files in `dest_dir`."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    used: list[int] = []
    for entry in dest_dir.iterdir():
        match = re.match(r"^(\d+)-", entry.name)
        if match:
            used.append(int(match.group(1)))
    return (max(used) + 1) if used else 1


def dual_snapshot(
    page: Any,
    slug: str,
    *,
    dest_dir: Path,
    index: int | None = None,
) -> tuple[Path, Path]:
    """Canonical snapshot: save NN-<slug>.png + NN-<slug>.aria.yaml.

    The PNG captures what the user sees; the ARIA YAML captures the role/name
    tree Playwright queries against — together they form a reproducible record
    of "where we were", suitable for human review, selector authoring, and
    regression diffing.

    Returns (png_path, aria_path). `index` auto-assigned if None.
    """
    safe = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    if not safe:
        raise ValueError("slug must contain at least one alphanumeric char")
    idx = next_index(dest_dir) if index is None else index
    png_path = dest_dir / f"{idx:02d}-{safe}.png"
    aria_path = dest_dir / f"{idx:02d}-{safe}.aria.yaml"
    screenshot(page, png_path)
    aria_snapshot(page, aria_path)
    return png_path, aria_path


def get_html(page: Any, *, locator: Any = None) -> str:
    """Return full-page HTML, or the outer HTML of a specific locator."""
    if locator is None:
        return page.content()
    return locator.evaluate("element => element.outerHTML")


def inspect_element(
    page: Any,
    role: str,
    name: str,
    *,
    exact: bool = True,
) -> dict[str, Any]:
    """Return a structured snapshot of a single element: html, attrs, bbox."""
    locator = _locator_by_role(page, role, name, exact=exact)
    locator.wait_for(state="attached", timeout=5000)
    return {
        "outer_html": locator.evaluate("e => e.outerHTML"),
        "tag": locator.evaluate("e => e.tagName.toLowerCase()"),
        "id": locator.evaluate("e => e.id || null"),
        "classes": locator.evaluate("e => Array.from(e.classList)"),
        "attrs": locator.evaluate(
            "e => Object.fromEntries(Array.from(e.attributes).map(a => [a.name, a.value]))"
        ),
        "bounding_box": locator.bounding_box(),
        "is_visible": locator.is_visible(),
        "is_enabled": locator.is_enabled(),
    }


@dataclass
class ConsoleEvent:
    type: str
    text: str
    location: str


@dataclass
class ConsoleRecorder:
    events: list[ConsoleEvent] = field(default_factory=list)

    def by_type(self, *types: str) -> list[ConsoleEvent]:
        return [e for e in self.events if e.type in types]

    @property
    def errors(self) -> list[ConsoleEvent]:
        return self.by_type("error")


@contextlib.contextmanager
def console_recorder(page: Any) -> Iterator[ConsoleRecorder]:
    """Capture every `console.*` event during the `with` block."""
    recorder = ConsoleRecorder()

    def handler(message: Any) -> None:
        loc = message.location or {}
        recorder.events.append(
            ConsoleEvent(
                type=message.type,
                text=message.text,
                location=f"{loc.get('url','')}:{loc.get('lineNumber','')}:{loc.get('columnNumber','')}",
            )
        )

    page.on("console", handler)
    try:
        yield recorder
    finally:
        page.remove_listener("console", handler)


@dataclass
class NetworkEntry:
    url: str
    method: str
    status: int | None = None
    status_text: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_post_data: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_mime: str = ""
    response_body: str | bytes | None = None
    response_json: Any = None
    error: str | None = None
    timing_ms: float | None = None

    def is_json(self) -> bool:
        return "application/json" in (self.response_mime or "")


@dataclass
class NetworkRecorder:
    entries: list[NetworkEntry] = field(default_factory=list)
    _by_request: dict[Any, NetworkEntry] = field(default_factory=dict)

    def filter(
        self,
        *,
        url_contains: str | None = None,
        status: int | None = None,
        method: str | None = None,
    ) -> list[NetworkEntry]:
        out = self.entries
        if url_contains is not None:
            out = [e for e in out if url_contains in e.url]
        if status is not None:
            out = [e for e in out if e.status == status]
        if method is not None:
            out = [e for e in out if e.method.upper() == method.upper()]
        return out

    @property
    def failed(self) -> list[NetworkEntry]:
        return [e for e in self.entries if e.error or (e.status and e.status >= 400)]


@contextlib.contextmanager
def network_recorder(
    page: Any,
    *,
    url_predicate: Callable[[str], bool] | None = None,
    capture_bodies: bool = True,
) -> Iterator[NetworkRecorder]:
    """Capture every network request/response during the `with` block."""
    recorder = NetworkRecorder()
    predicate = url_predicate or (lambda _u: True)

    def on_request(request: Any) -> None:
        if not predicate(request.url):
            return
        entry = NetworkEntry(
            url=request.url,
            method=request.method,
            request_headers=dict(request.headers),
            request_post_data=request.post_data,
        )
        recorder._by_request[request] = entry
        recorder.entries.append(entry)

    def on_response(response: Any) -> None:
        entry = recorder._by_request.get(response.request)
        if entry is None:
            return
        try:
            entry.status = response.status
            entry.status_text = response.status_text
            entry.response_headers = dict(response.headers)
            entry.response_mime = entry.response_headers.get("content-type", "").split(";")[0].strip()
            if capture_bodies:
                try:
                    body = response.body()
                except Exception as exc:
                    entry.error = f"body fetch failed: {exc}"
                    return
                if entry.is_json():
                    try:
                        entry.response_json = json.loads(body.decode("utf-8"))
                    except Exception:
                        entry.response_body = body
                else:
                    try:
                        entry.response_body = body.decode("utf-8")
                    except UnicodeDecodeError:
                        entry.response_body = body
        except Exception as exc:
            entry.error = f"response capture failed: {exc}"

    def on_request_failed(request: Any) -> None:
        entry = recorder._by_request.get(request)
        if entry is None:
            return
        entry.error = request.failure or "request failed"

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("requestfailed", on_request_failed)
    try:
        yield recorder
    finally:
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)
        page.remove_listener("requestfailed", on_request_failed)


def dump_network(recorder: NetworkRecorder, dest: Path) -> Path:
    """Persist a NetworkRecorder's entries to JSON for offline inspection."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    serialisable = []
    for entry in recorder.entries:
        body: Any = entry.response_json
        if body is None and isinstance(entry.response_body, str):
            body = entry.response_body
        elif body is None and isinstance(entry.response_body, bytes):
            body = f"<{len(entry.response_body)} bytes>"
        serialisable.append({
            "url": entry.url,
            "method": entry.method,
            "status": entry.status,
            "status_text": entry.status_text,
            "request_post_data": entry.request_post_data,
            "response_mime": entry.response_mime,
            "response_body": body,
            "error": entry.error,
        })
    dest.write_text(
        json.dumps(serialisable, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return dest
