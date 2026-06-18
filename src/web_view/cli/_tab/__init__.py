"""`web-view tab` — tab lifecycle subcommands.

Each verb (`new`, `close`, `switch`) lives in its own module and shares
the runtime helpers in `_shared.py`. The library half already exposes
`cdp.open_tab` / `cdp.close_tab` / `cdp.switch_to_tab`; these verbs are a
thin CLI pass-through.
"""

from __future__ import annotations

import argparse

from . import _close, _new, _switch

EPILOG = """\
Common options (every verb):
  --port <N>      optional when exactly one CDP Chrome is running
  --quiet / -q    suppress the success ack on stdout

Tab selection (`close` requires --tab; `switch` defaults to the first
non-helper tab; `new` takes no --tab):
  --tab N             by index (0-based; negatives count from the end)
  --tab <substring>   by URL substring (first match wins)

Port selection follows `web-view navigate` semantics. See
`web-view tab <verb> -h` for per-verb examples.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "tab",
        help="manage tabs (new, close, switch)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    verb_parsers = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")
    _new.register(verb_parsers)
    _close.register(verb_parsers)
    _switch.register(verb_parsers)
