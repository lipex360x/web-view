"""`web-view snap` — ARIA YAML snapshot with optional PNG of a tab."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .. import cdp
from ._shared import resolve_single_port


def handle(arguments: argparse.Namespace) -> int:
    target_port = resolve_single_port(arguments.port)
    if target_port is None:
        return 1
    safe_slug = re.sub(r"[^a-z0-9-]+", "-", arguments.slug.lower()).strip("-")
    if not safe_slug:
        print("slug must contain at least one alphanumeric char", file=sys.stderr)
        return 1
    destination_dir = Path(arguments.destination_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    with cdp.connect(port=target_port) as (_, context):
        page = cdp.find_page(context, url_contains=arguments.url_contains)
        if page is None:
            print(f"no tab containing {arguments.url_contains!r}", file=sys.stderr)
            return 1
        if arguments.image:
            image_path, aria_path = cdp.dual_snapshot(
                page,
                safe_slug,
                dest_dir=destination_dir,
                include_frames=arguments.include_frames,
            )
            print(str(image_path.resolve()))
        else:
            index = cdp.next_index(destination_dir)
            aria_path = destination_dir / f"{index:02d}-{safe_slug}.aria.yaml"
            cdp.aria_snapshot(page, aria_path, include_frames=arguments.include_frames)
    print(str(aria_path.resolve()))
    return 0


EPILOG = """\
Examples:
  web-view snap                              # single instance, auto-slug
  web-view snap homepage                     # YAML only, explicit slug
  web-view snap homepage --image             # YAML plus PNG
  web-view snap login --url-contains login   # pick tab by URL substring
  web-view snap homepage --destination-dir ./captures
  web-view snap --no-frames                  # top frame only (skip iframes)
  web-view snap --port 9333                  # explicit port

Iframe recursion:
  By default the ARIA YAML inlines the tree of every same-origin child
  frame under its `- iframe` node, labelled with the frame URL. Cross-origin
  frames are annotated `- iframe (cross-origin, not captured)`. Pass
  `--no-frames` for the legacy top-frame-only snapshot.

Port selection (same rule as `web-view stop` / `web-view navigate`):
  `--port` is optional when exactly one CDP Chrome is running. With zero
  or 2+ running instances, the command exits with the candidate ports.

Output:
  Default: write NN-<slug>.aria.yaml and print its absolute path.
  With --image: write both NN-<slug>.png and NN-<slug>.aria.yaml,
  printing the PNG path first, then the YAML path. NN is the next free
  integer in the destination directory across both capture types.

    web-view snap --image | head -1 | xargs open

"""


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "snap",
        help="ARIA YAML snapshot with optional PNG of a tab",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "slug",
        nargs="?",
        default="snap",
        help="snapshot name (kebab-case); defaults to 'snap'",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="CDP port (optional when exactly one CDP Chrome is running)",
    )
    parser.add_argument(
        "--url-contains",
        default="",
        help="substring to pick the tab (defaults to first non-helper tab)",
    )
    parser.add_argument(
        "--destination-dir",
        default="./captures",
        help="where to save numbered ARIA YAML and optional PNG files",
    )
    parser.add_argument(
        "--no-frames",
        dest="include_frames",
        action="store_false",
        help="capture the top frame only (do not recurse into same-origin iframes)",
    )
    parser.add_argument(
        "--image",
        action="store_true",
        help="also save a PNG screenshot (default: ARIA YAML only)",
    )
    parser.set_defaults(func=handle, include_frames=True)
