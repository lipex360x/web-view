# ADR 0001 — CLI for element interaction

- **Status:** accepted
- **Date:** 2026-05-28
- **Decision owner:** @lipex360x
- **Issue:** [#4](https://github.com/lipex360x/web-view/issues/4)
- **Supersedes:** —
- **Superseded by:** —

## Context

`web-view` today is a "lifecycle + capture" CLI: `start`, `list`, `stop`,
`navigate`, `snap`. The library half (`from web_view import cdp`) exposes
~30 helpers — including the full interaction set (`click`, `fill`,
`check`, `press`, `hover`, `dblclick`, `right_click`, `scroll_into_view`,
`upload`, `drag`) — but the CLI half does not bridge to them. Any
"click this thing" workflow forces the user into a Python REPL or a
one-off script, even though the `.aria.yaml` emitted by `web-view snap`
already speaks the exact `role + name` vocabulary the library needs.

The recently-shipped CLI refactor (PR #2) consolidated `web-view -h` into
the market-standard terse top-level pattern (git / docker / gh: short
root listing, details in per-command `-h`). Adding a new command family
must not undo that decision.

This ADR resolves the design forks raised in issue #4 and produces the
acceptance criteria that Phase B will implement against.

## Decision

**Adopt Mechanism C — group interaction commands under a single `do`
subcommand.**

```
web-view do click       --role button   --name "Next slide"
web-view do fill        --role textbox  --name "Email" --value "user@x.com"
web-view do check       --role checkbox --name "Remember me"
web-view do press       --keys "Control+a,Backspace"
web-view do hover       --role button   --name "Tooltip target"
web-view do dblclick    --role link     --name "Open"
web-view do right-click --role cell     --name "Cell A1"
web-view do scroll-into-view --role region --name "Footer"
web-view do upload      --role button   --name "Choose file" --file ./report.pdf
web-view do drag        --from "button:Item" --to "region:Trash"
```

`web-view -h` gains exactly one line (`do`). Discovery of the
interaction set happens via `web-view do -h`. Each `do <verb>` carries
its own EPILOG with examples, port/tab notes, and error-contract
documentation, mirroring the existing pattern in `_navigate.py` /
`_snap.py`.

CLI-to-library name mapping uses kebab-case in the CLI when the library
name uses snake_case (`right_click` → `right-click`,
`scroll_into_view` → `scroll-into-view`). Single-word library names
stay unchanged (`dblclick` is kept as a single token to match the
library and the broader Playwright / web-dev vocabulary).

## Rejected alternatives

- **A — Flat MVP (3 commands).** Rejected: forces a REPL escape for
  hover / drag / upload workflows even though the library already
  exposes them. Drops too much value to be worth the ~3-line root-`-h`
  savings over C.
- **B — Flat 10 commands.** Rejected: takes root `-h` from 5 to 15
  commands, undoing the terse-top-level decision from PR #2. The
  benchmark CLIs (git / docker / gh / kubectl) all group at this
  cardinality.
- **D — Single `act` with positional verb.** Rejected: functionally
  equivalent to C but loses the `do <verb> -h` discovery surface
  (positional choices don't get their own subparser help) and reads
  more awkwardly (`web-view act click` vs `web-view do click`).

## Resolved open questions

1. **Scope cutoff.** All ten interaction helpers graduate from library
   to CLI under `do`: `click`, `fill`, `check`, `press`, `hover`,
   `dblclick`, `right-click`, `scroll-into-view`, `upload`, `drag`.
   `evaluate` is explicitly deferred (see #8).

2. **Element addressing.** Default to `--role <role> --name <name>`,
   matching the `.aria.yaml` vocabulary. Add `--selector <css>` as an
   explicit escape hatch for CSS-first workflows. The three flags are
   mutually exclusive at the `--selector` boundary: either
   `--role/--name` OR `--selector`, never both. No auto-detection —
   explicit beats magic.

3. **`--value` for `fill`.** Primary path is `--value <text>`. When
   `--value` is omitted, read the value from stdin until EOF. This
   covers long strings (`web-view do fill --role textbox --name Email <
   message.txt`) without introducing a separate `--value-file` flag.

4. **`press` key syntax.** Comma-separated chord list:
   `--keys "Control+a,Backspace,Meta+v"`. Each comma-delimited segment
   maps to one varargs entry passed to `cdp.press(page, *keys)`. Spaces
   around commas are tolerated and stripped.

5. **Output on success.** One-line ack on stdout:
   - `clicked: button "Next slide"`
   - `filled: textbox "Email" (12 chars)`
   - `pressed: Control+a, Backspace`
   - `hovered: button "Tooltip target"`
   - Identifier in the ack is `<role> "<name>"` when role+name was used,
     or `selector="..."` when `--selector` was used.

   Add `--quiet` (alias `-q`) to suppress the ack for pipe-friendly use.
   No `--json` in MVP — wait for a real consumer to ask.

6. **Element waiting.** Expose `--timeout <seconds>` on every
   interaction command, default 15 (matches `cdp.wait_locator` /
   `cdp.click` defaults). The `state` parameter is fixed at `visible`
   for CLI use — advanced states (`attached`, `hidden`, `stable`) stay
   library-only. On timeout, the CLI prints
   `timeout: <verb> on <role> "<name>" after Ns` to stderr and exits
   non-zero.

7. **`--tab` integration.** Every `do <verb>` accepts the same
   `--tab <index|substring>` semantics as `web-view navigate`. The
   helper currently inlined in `cli/_navigate._pick_tab` moves to
   `cli/_shared.resolve_target_tab(context, selector)` and is reused
   by both `navigate` and every `do <verb>`. Default (no `--tab`) picks
   the first non-helper tab, same as `navigate`.

8. **`evaluate`.** Deferred to a follow-up issue. Reasoning: it
   requires library work first (`cdp.evaluate(page, script, *,
   arg=None)` doesn't exist yet) plus its own design pass for
   JSON-serialisation contract and JS-input encoding (`--script`,
   `--script-file`, stdin precedence). Bundling it here would double
   the surface and the test matrix.

9. **`-h` bloat policy.** Codify the rule we are exercising here:
   *when a command family reaches ≥3 related verbs, group them under a
   parent subcommand*. Root `web-view -h` caps at 8 commands; further
   families (e.g. `inspect` for `get-html` / `inspect-element` /
   storage queries, `record` for `console` / `network` capture) follow
   the same `<family> <verb>` pattern. This policy supersedes the
   ad-hoc choices made before PR #2.

## Acceptance criteria (for Phase B)

> These items are the spec Phase B (`feat/cli-interaction-4`)
> implements against. Phase B follows project TDD: write the failing
> tests first, implement the minimum, refactor only if needed. Tick
> each item below by editing the corresponding issue body
> (`gh issue edit 4`) as the implementing commit lands.

- [ ] `web-view do click --role <role> --name <name>` invokes
      `cdp.click(page, role, name)` against the resolved tab.
- [ ] `web-view do fill --role textbox --name <name> --value <text>`
      invokes `cdp.fill(page, "textbox", name, text)`.
- [ ] `web-view do fill` reads the value from stdin when `--value` is
      omitted (until EOF).
- [ ] `web-view do check --role checkbox --name <name>` invokes
      `cdp.check`.
- [ ] `web-view do press --keys "Control+a,Backspace"` splits on commas
      and invokes `cdp.press(page, "Control+a", "Backspace")`.
- [ ] `web-view do hover` / `dblclick` / `right-click` /
      `scroll-into-view` each pass through to their `cdp.*`
      counterpart.
- [ ] `web-view do upload --role button --name <name> --file <path>`
      invokes `cdp.upload(page, "button", name, path)`. `--file` is
      required.
- [ ] `web-view do drag --from "<role>:<name>" --to "<role>:<name>"`
      invokes `cdp.drag(page, source_locator=..., target_locator=...)`.
      The `<role>:<name>` micro-syntax is documented in the EPILOG.
- [ ] Every `do <verb>` accepts `--selector <css>` as a mutually
      exclusive alternative to `--role/--name`; passing both errors out
      with a clear message.
- [ ] Every `do <verb>` accepts `--tab <index|substring>` with the
      same semantics as `web-view navigate`.
- [ ] Every `do <verb>` accepts `--port <N>` and treats it as optional
      (auto-resolve via `resolve_single_port`, same as
      `navigate`/`snap`/`stop`).
- [ ] Every `do <verb>` accepts `--timeout <seconds>`, default 15.
- [ ] Success prints `<verb>: <identifier>` on stdout (one line);
      `--quiet`/`-q` suppresses it.
- [ ] Missing tab / element / timeout produce structured errors on
      stderr (not Playwright tracebacks) and exit non-zero.
- [ ] `web-view -h` still lists exactly 6 top-level commands:
      `start | list | stop | navigate | snap | do`.
- [ ] `web-view do -h` lists every interaction subcommand with help
      strings and an EPILOG that points to the per-verb help.
- [ ] Each `web-view do <verb> -h` carries its own EPILOG (Examples,
      Port selection, Tab selection, Element addressing, Error
      contract) following the existing `_navigate.py` template.
- [ ] `cli/_shared.resolve_target_tab(context, selector)` extracted
      from `_navigate._pick_tab`; both `navigate` and every `do <verb>`
      call it.
- [ ] Tests added in `tests/test_cli.py` using the existing `fake_cdp`
      fixture — one happy-path test per verb plus error-path tests
      (missing tab, missing element, timeout, mutually-exclusive
      `--role/--name` + `--selector`, stdin-fed `fill`).
- [ ] CHANGELOG `[Unreleased]` entry under `Added` for the `do`
      family.
- [ ] README CLI reference gains a "click + snap loop" example and a
      list of `do <verb>` commands; the quick-start block stays terse.
- [ ] `evaluate` is **not** added — confirmed deferred to a follow-up
      issue.
- [ ] All quality gates pass: `uv run --extra dev pytest tests/ -q`,
      `check-all .`, `uv run ruff format src/ tests/`, `uv run
      web-view --help` (sanity check the terse root).

## Consequences

**Positive.**

- Root `-h` stays at 6 commands (gain of 1 line for the entire
  interaction family) — preserves the PR #2 terseness goal.
- Establishes a clean precedent for future command families
  (`inspect`, `record`) so the next "where does this go?" question
  answers itself.
- `do <verb>` reads naturally as English ("do click", "do fill"),
  matching how the user describes the action in conversation.
- The `role + name` default closes the `snap` → act loop: the user
  reads a name from the `.aria.yaml` and plugs it into the next
  command without translation.

**Negative.**

- Slightly more typing on the most common path (`web-view do click`
  vs `web-view click`). Mitigated by shell aliases for power users.
- `do <verb>` is a two-word subcommand pattern not heavily exercised
  by the benchmark CLIs (git has `git remote add` but the second word
  is a noun-modifier; kubectl uses it but is resource-oriented). New
  ground for this project — accept and document.

**Follow-ups.**

- Issue for `evaluate` (`web-view do evaluate`) tracking the library
  work, JSON-serialisation contract, and JS-input encoding. To be
  filed after Phase B lands.
- Possible future family migrations under the `-h` bloat policy:
  `inspect get-html` / `inspect element` / `inspect storage`, and
  `record console` / `record network`. Out of scope for this ADR;
  noted so the next family knows where to land.
