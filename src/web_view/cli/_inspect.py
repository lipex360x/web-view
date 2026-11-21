"""Inspect a selected DOM region without writing a capture file."""

from __future__ import annotations

import argparse
import json
import sys

from .. import cdp
from ._shared import connected_tab, print_no_frame_found, resolve_target_frame

_SCRIPT = r"""({selector, kinds}) => {
    let root;
    try { root = document.querySelector(selector); }
    catch (error) { return {error: `Invalid CSS selector: ${error.message}`}; }
    if (!root) return {error: `No element matched selector: ${selector}`};
    const collect = css => [
        ...(root.matches(css) ? [root] : []), ...root.querySelectorAll(css)
    ];
    const result = {};
    if (kinds.includes('text')) result.text = root.innerText ?? root.textContent ?? '';
    if (kinds.includes('links')) result.links = collect('a[href]').map(link => ({
        text: (link.innerText ?? link.textContent ?? '').trim(), href: link.href
    }));
    if (kinds.includes('fields')) result.fields =
      collect('input, select, textarea, button').map(field => ({
        tag: field.localName,
        type: field.getAttribute('type'),
        name: field.getAttribute('name'),
        id: field.id || null,
        label: Array.from(field.labels ?? [], label => label.innerText.trim()).join(' ') ||
            field.getAttribute('aria-label') || null,
        placeholder: field.getAttribute('placeholder'),
        required: field.required || false,
        disabled: field.disabled || false,
        ...(field.localName === 'input' && field.type === 'file' ? {
            accept: field.getAttribute('accept'), multiple: field.multiple
        } : {})
    }));
    return result;
}"""


def handle(arguments: argparse.Namespace) -> int:
    kinds = [kind for kind in ("text", "links", "fields") if getattr(arguments, kind)]
    if not kinds:
        kinds = ["text", "links", "fields"]
    with connected_tab(arguments.port, arguments.tab) as page:
        root = resolve_target_frame(page, arguments.frame) if page is not None else None
        if root is None:
            if page is not None:
                print_no_frame_found(arguments.frame)
            return 1
        result = cdp.evaluate(root, _SCRIPT, {"selector": arguments.selector, "kinds": kinds})
    if "error" in result:
        print(f"error: {result['error']}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "inspect",
        help="inspect text, links, and fields in a selected DOM region as JSON",
        description="Read a DOM region without creating a snapshot. Field values are excluded.",
    )
    parser.add_argument(
        "--selector", default="body", help="CSS selector for the region (default: body)"
    )
    for kind in ("text", "links", "fields"):
        parser.add_argument(f"--{kind}", action="store_true", help=f"include {kind} in the result")
    parser.add_argument("--port", type=int, default=None, help="CDP port")
    parser.add_argument(
        "--tab", default=None, help="tab index, URL substring, or unique:<substring>"
    )
    parser.add_argument(
        "--frame", default="auto", help="frame index, URL substring, or 'auto' (top frame)"
    )
    parser.set_defaults(func=handle)
