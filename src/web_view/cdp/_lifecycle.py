"""Chrome process lifecycle: start, stop, list running CDP-enabled Chromes.

`start_chrome` launches Chrome with `--remote-debugging-port` on a persistent
profile and returns the spawned `Popen`. `stop_chrome` terminates it by port,
pid, or the `Popen` handle. `list_cdp_instances` enumerates every Chrome on
the host that exposes a `--remote-debugging-port` flag, splitting helper
sub-processes out from the real listeners.

Polling primitives (`is_cdp_ready`, `wait_for_chrome_stopped`) use a single
`poll_localhost_json` probe from `_shared` — they share the same retry shape
but flipped predicates (positive vs. negative).
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._shared import poll_localhost_json

DEFAULT_CDP_PORT = 9222
CDP_URL = f"http://localhost:{DEFAULT_CDP_PORT}"

_REMOTE_PORT_RE = re.compile(r"--remote-debugging-port=(\d+)")
_USER_DATA_DIR_RE = re.compile(r'--user-data-dir=("([^"]+)"|(\S+))')
_HELPER_MARKERS: tuple[str, ...] = (" --type=", "Chrome Helper", "Chromium Helper")
_WMIC_MIN_PARTS = 3
_PS_EXPECTED_PARTS = 2


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


def _poll_until(
    predicate: Any,
    *,
    timeout_s: float,
    sleep_s: float,
) -> bool:
    """Call `predicate()` until it returns True or `timeout_s` elapses."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(sleep_s)
    return False


def is_cdp_ready(port: int, *, timeout_s: int = 15) -> bool:
    """Poll `http://localhost:<port>/json/version` until it responds (or timeout)."""
    return _poll_until(
        lambda: poll_localhost_json(port),
        timeout_s=timeout_s,
        sleep_s=0.5,
    )


def wait_for_chrome_stopped(port: int, *, timeout_s: int = 15) -> bool:
    """Inverse of `is_cdp_ready`: wait until the port stops responding.

    Returns True if Chrome stopped within `timeout_s`, False on timeout.
    """
    return _poll_until(
        lambda: not poll_localhost_json(port),
        timeout_s=timeout_s,
        sleep_s=0.3,
    )


def start_chrome(
    *,
    port: int = DEFAULT_CDP_PORT,
    user_data_dir: str | Path,
    headless: bool = False,
    window_size: tuple[int, int] = (1920, 1080),
    extra_args: list[str] | None = None,
    binary: str | None = None,
) -> subprocess.Popen:
    """Launch Chrome with CDP on `port` and a persistent `user_data_dir`.

    `window_size` is a `(width, height)` tuple forwarded to Chrome's
    `--window-size=W,H` launch flag (default 1920x1080). Use
    `cdp.set_window_size(page, ...)` to resize a running instance.

    Returns the spawned Popen. Chrome runs in its own process group on Unix
    so it survives the Python parent exiting.
    """
    if is_cdp_ready(port, timeout_s=1):
        raise RuntimeError(f"port {port} already has a CDP-listening Chrome")
    width, height = window_size
    command_argv = [
        binary or _resolve_chrome_binary(),
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={user_data_dir}",
        f"--window-size={width},{height}",
    ]
    if headless:
        command_argv.append("--headless=new")
    if extra_args:
        command_argv.extend(extra_args)
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if platform.system() != "Windows":
        popen_kwargs["preexec_fn"] = os.setsid
    process = subprocess.Popen(command_argv, **popen_kwargs)
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


def _build_instance(
    pid: int,
    port_match: re.Match[str],
    user_data_match: re.Match[str] | None,
    cmdline: str,
) -> CdpInstance:
    user_data_dir: str | None = None
    if user_data_match is not None:
        user_data_dir = user_data_match.group(2) or user_data_match.group(3)
    return CdpInstance(
        pid=pid,
        port=int(port_match.group(1)),
        user_data_dir=user_data_dir,
        cmdline=cmdline,
    )


def _list_instances_windows() -> list[CdpInstance]:
    completed = subprocess.run(
        [
            "wmic",
            "process",
            "where",
            "name='chrome.exe'",
            "get",
            "processid,commandline",
            "/format:csv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    results: list[CdpInstance] = []
    for line in completed.stdout.splitlines():
        parts = line.split(",")
        if len(parts) < _WMIC_MIN_PARTS:
            continue
        cmdline = ",".join(parts[1:-1])
        try:
            pid = int(parts[-1].strip())
        except ValueError:
            continue
        port_match = _REMOTE_PORT_RE.search(cmdline)
        if not port_match:
            continue
        user_data_match = _USER_DATA_DIR_RE.search(cmdline)
        results.append(_build_instance(pid, port_match, user_data_match, cmdline))
    return results


def _list_instances_unix() -> list[CdpInstance]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    results: list[CdpInstance] = []
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        port_match = _REMOTE_PORT_RE.search(line)
        if not port_match:
            continue
        if any(marker in line for marker in _HELPER_MARKERS):
            continue
        parts = line.split(None, 1)
        if len(parts) != _PS_EXPECTED_PARTS:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmdline = parts[1]
        user_data_match = _USER_DATA_DIR_RE.search(cmdline)
        results.append(_build_instance(pid, port_match, user_data_match, cmdline))
    return results


def list_cdp_instances() -> list[CdpInstance]:
    """Return every Chrome process currently exposing a --remote-debugging-port.

    Filters out helper sub-processes (renderer/GPU/network) that inherit the
    parent's cmdline. Returns one CdpInstance per real listening Chrome.
    """
    if platform.system() == "Windows":
        return _list_instances_windows()
    return _list_instances_unix()


def _stop_process_handle(process: subprocess.Popen) -> int:
    try:
        if platform.system() == "Windows":
            process.terminate()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        return 1
    except (ProcessLookupError, PermissionError):
        return 0


def _stop_by_pids(target_pids: list[int]) -> int:
    killed = 0
    for target in target_pids:
        try:
            os.kill(target, signal.SIGTERM)
            killed += 1
        except (ProcessLookupError, PermissionError):
            continue
    return killed


def stop_chrome(
    *,
    port: int | None = None,
    pid: int | None = None,
    process: subprocess.Popen | None = None,
) -> int:
    """Terminate Chrome by port, pid, or Popen handle. Returns count killed.

    Exactly one of `port`, `pid`, or `process` must be given.
    """
    given = sum(value is not None for value in (port, pid, process))
    if given != 1:
        raise ValueError("pass exactly one of port=, pid=, process=")

    if process is not None:
        return _stop_process_handle(process)

    if pid is not None:
        target_pids = [pid]
    else:
        target_pids = [instance.pid for instance in list_cdp_instances() if instance.port == port]
    if not target_pids:
        return 0
    return _stop_by_pids(target_pids)
