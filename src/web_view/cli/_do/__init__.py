"""`web-view do` — element interaction subcommands.

Each verb (`click`, `fill`, `check`, `press`, `hover`, `dblclick`,
`right-click`, `scroll-into-view`, `upload`, `drag`) lives in its own
module and shares the addressing + runtime helpers in `_shared.py`.
"""

from __future__ import annotations

import argparse

from . import (
    _check,
    _click,
    _dblclick,
    _drag,
    _fill,
    _hover,
    _press,
    _right_click,
    _scroll_into_view,
    _upload,
)

EPILOG = """\
Element addressing (every verb except `press` and `drag`):
  --role <role> --name <name>     ARIA-based (matches `web-view snap` YAML)
  --selector <css>                CSS selector escape hatch
                                  (mutually exclusive with --role/--name)

Common options:
  --port <N>      optional when exactly one CDP Chrome is running
  --tab <T>       index (0-based, negatives allowed) or URL substring
  --frame <F>     index (0 is the top frame), URL substring, or 'auto'
  --timeout <s>   upper bound in seconds (default 15; ignored by scroll-into-view)
  --quiet / -q    suppress the success ack on stdout

Frame targeting (all verbs except `press`):
  --frame auto    search the top frame and every same-origin frame, first
                  hit wins. This is the default, so an in-frame element is
                  found without naming the frame.
  --frame 1       index into the page's frame list (0 is the top frame)
  --frame lms     first frame whose URL contains 'lms'

  web-view do click --role button --name "ENTER"            # auto-find frame
  web-view do click --role radio --name "Option B" --frame index_lms

See `web-view do <verb> -h` for per-verb examples.
"""


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "do",
        help="act on elements in a tab (click, fill, press, hover, …)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    verb_parsers = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")
    _click.register(verb_parsers)
    _fill.register(verb_parsers)
    _check.register(verb_parsers)
    _press.register(verb_parsers)
    _hover.register(verb_parsers)
    _dblclick.register(verb_parsers)
    _right_click.register(verb_parsers)
    _scroll_into_view.register(verb_parsers)
    _upload.register(verb_parsers)
    _drag.register(verb_parsers)
