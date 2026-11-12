---
name: web-view
description: Open CDP Chrome and browse websites interactively with the local web-view CLI. Use for requests such as "abra o CDP", "abrir o Chrome com CDP", "navegue como usuário", guided browsing, clicking or filling web pages, screenshots, and local browser tests. General web research alone does not require this skill.
---

# web-view

Control Chrome through the local `web-view` CLI using CDP (Chrome DevTools Protocol). Use it for interactive browsing of local or remote websites, user-guided navigation, and browser tests. Follow the current project's instructions about starting applications and changing data; this skill supplies tool usage, not additional authorization.

## User-guided browsing

Treat requests to open or start CDP as requests to open a Chrome instance controlled through `web-view`, even if the user does not name the tool or mention tests. Requests such as "abra o CDP que eu vou te orientando" or "navegue como usuário" should select this skill. A technical discussion about the CDP protocol alone does not imply opening a browser.

For guided browsing, list existing instances first, then reuse a suitable visible Chrome or start one without `--headless`. If a suitable instance already exists, bring its relevant tab to the front with `web-view tab switch`. When no URL is supplied, keep the current page or start at `about:blank`; do not require a URL just to open CDP. Confirm that Chrome is ready and report its port, then wait for the user's next navigation instruction. Keep this instance open across turns, reuse its port and tab, and inspect current state after the user navigates manually. Perform each requested step and report the observed result without inventing further destinations or actions.

## Local installation

- Executable: `/Users/lipex360/.local/bin/web-view`. Examples below use `web-view`; use the absolute path if PATH does not resolve it.
- This guide was checked against version **0.8.0**. Do not run help for every new conversation or every routine command. Consult `web-view <command> -h` (or `web-view do <verb> -h`) for an unfamiliar option, a syntax error, or a version mismatch. Use `web-view --version` when investigating compatibility.
- Install the bundled skill with `web-view install skill` (Codex, global by default). Use `--agent claude`, `--scope local`, or `--target <parent-skills-directory>` when needed. Re-run with `--force` after upgrading to refresh an installed copy; existing files are backed up. Maintain this skill in the web-view repository at `src/web_view/skill/`; installed copies are snapshots.
- CLI installation uses a uv tool environment. Python imports in another interpreter are not automatically available. Prefer the CLI for browser tasks; do not install dependencies just to reproduce CLI functionality.

## Working workflow

1. Run `web-view list` to discover running instances and tabs. It reports PID, CDP port, profile directory, and tab URLs/titles. A `?` tab listing means enumeration failed, not that no tabs exist.
2. Reuse an appropriate instance. If one must be created, `web-view start --port 9333` starts a detached Chrome; `--headless` is available for tasks that do not need a visible window. `--url` sets its initial page and `--window-size 1280x720` sets its initial window size. The default profile is persistent at `~/.cache/web-view/profile`; `--user-data-dir` selects another profile. Use distinct profiles for concurrent instances. Chrome remains running after the command exits.
3. Navigate to the requested URL, capture the page as YAML, and inspect the relevant tree before choosing an interaction target. Request an image only when the task needs visual evidence.
4. Perform the requested action, then verify the expected page state. An interaction's success acknowledgment only proves the action completed; verify its effect with another snapshot or a focused JavaScript query.
5. Report the observed outcome and useful capture paths. Preserve instances and tabs that were already present. Close only resources created for this task when cleanup is appropriate; keep a visible result open when the user needs to inspect it.

Use waits tied to observable state rather than fixed sleeps. Element actions normally wait up to 15 seconds (`--timeout` adjusts this where supported). For asynchronous results, use a bounded sequence of focused state checks and stop with the observed failure if the expected state never appears. Do not blindly retry a submission that may already have succeeded.

## Instance, tab, and frame selection

- With exactly one CDP Chrome, `--port` is optional. With zero or multiple instances, commands requiring an instance fail and show guidance or candidate ports. Use an explicit port when several instances exist or isolation matters.
- Most tab-aware commands accept `--tab`: a zero-based index, negative index counted from the end, or URL substring (first match wins). The default is the first non-helper tab. Verify the target rather than assuming the foreground tab is selected.
- `navigate --new-tab` opens a new tab and is mutually exclusive with `--tab`.
- `snap` uses **`--url-contains`**, not `--tab`, to select a tab.
- Element actions support `--frame auto` (default): search the top frame and same-origin child frames, taking the first match. `--frame 0` selects the top frame; an index or URL substring selects a specific frame. `press` does not accept `--frame`.
- `eval --frame auto` defaults to the top frame; it does not perform the element actions' automatic search. Select the frame explicitly when evaluating inside an iframe.
- Snapshot YAML includes same-origin iframe trees by default. Cross-origin frames are annotated but their contents are not captured. `snap --no-frames` captures only the top frame's tree.

## Capture and inspect

```bash
web-view navigate --url http://localhost:3000 --port 9333 --new-tab
web-view snap initial-page --port 9333 --url-contains localhost:3000 --destination-dir /tmp/web-view-captures
```

`snap` writes only `NN-<slug>.aria.yaml` by default and prints its absolute path. Read this YAML first for roles, accessible names, text, and exposed states. This is normally sufficient for guided browsing, forms, and checking accessible messages without image analysis. Inspect only the relevant portions of large trees.

Add `--image` when the user requests a screenshot or the task depends on layout, spacing, colors, overlap, clipping, image/canvas content, or information missing from the accessibility tree:

```bash
web-view snap visual-check --image --port 9333 --destination-dir /tmp/web-view-captures
```

With `--image`, the command writes both `NN-<slug>.png` and `NN-<slug>.aria.yaml` with a shared prefix and prints absolute paths in PNG-then-YAML order. View the PNG with the available image-viewing tool only when visual inspection is needed. Use a descriptive kebab-case slug and an explicit destination appropriate to the project. Both modes share numbering, and iframe options apply to YAML in either mode. If the user requests YAML-only analysis, explain any visual uncertainty rather than silently loading an image.

Prefer ARIA role/name targets taken from the current snapshot. Use CSS selectors when accessible targeting is missing or ambiguous. `--selector` is mutually exclusive with `--role`/`--name`. If an element is missing, check the selected tab, frame, and current page state before changing selectors.

## Interactions

```bash
web-view do click --role button --name "Sign in" --port 9333
web-view do fill --role textbox --name "Email" --value "user@example.com" --port 9333
web-view do check --role checkbox --name "Remember me" --port 9333
web-view do press --keys "Enter" --port 9333
web-view do hover --selector "#menu" --port 9333
web-view do scroll-into-view --selector "#footer" --port 9333
```

Other available verbs are `dblclick`, `right-click`, `upload`, and `drag`; read their per-verb help when needed for additional arguments. Common element-action options include `--port`, `--tab`, `--frame`, `--timeout`, and `--quiet`/`-q`. `scroll-into-view` ignores the timeout option; `press` and `drag` have different targeting arguments from ordinary element actions.

`fill --value` supplies text inline. Omitting it reads stdin until EOF, which is useful for multiline content. `press --keys` takes comma-separated keystrokes with `+` for chords, such as `"Control+a,Backspace"` or macOS `"Meta+a,Backspace"`. Keyboard actions affect the focused element, so establish focus first when necessary.

## Focused JavaScript checks

```bash
web-view eval --js 'document.title' --port 9333
web-view eval --js '({url: location.href, ready: document.readyState})' --port 9333
web-view eval --js-file /tmp/check-page.js --port 9333 --frame 0
```

`eval` accepts exactly one source: `--js '<expression>'`, `--js -` (stdin), or `--js-file <path>`. It prints JSON and fails if the result cannot be serialized. Return plain values or objects rather than DOM nodes. Prefer normal UI interactions for user-flow tests; use evaluation for focused inspection or behavior the task actually requires. For complex expressions, use a file or a safely quoted heredoc to avoid shell expansion. Do not dump cookies, browser storage, or unrelated page data.

## Windows, tabs, downloads, and cleanup

```bash
web-view resize --width 390 --height 844 --viewport --port 9333
web-view tab new --port 9333
web-view tab switch --tab localhost:3000 --port 9333
web-view tab close --tab localhost:3000 --port 9333
web-view download --url 'https://example.com/report.pdf' --out /tmp/report.pdf --port 9333
web-view stop --port 9333
```

- `resize` normally changes the visible OS window; `--viewport` changes only the page viewport and is useful for responsive checks. The viewport override lasts until document reload, so apply it after navigation when testing the current page.
- `tab new` opens `about:blank` by default; `tab close` requires `--tab`; `tab switch` brings the chosen tab to the front.
- `download` reuses the browser context's cookies. It prints HTTP status and saved byte count; a non-2xx status is an error. Use it only for resources within the user's requested task.
- `stop` terminates the chosen Chrome instance. Target an explicit port during cleanup to avoid stopping another task's browser.
