"""Inspect a selected DOM region without writing a capture file."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .. import cdp
from ._shared import connected_tab, print_no_frame_found, resolve_target_frame

_MAX_VISIBILITY_MATCHES = 100
_SCRIPT = r"""({selector, kinds, limit}) => {
    let root;
    try { root = document.querySelector(selector); }
    catch (error) { return {error: `Invalid CSS selector: ${error.message}`}; }
    if (!root) return {error: `No element matched selector: ${selector}`};
    const collect = css => [
        ...(root.matches(css) ? [root] : []), ...root.querySelectorAll(css)
    ];
    const result = {};
    if (kinds.includes('visibility')) {
        const matches = [...document.querySelectorAll(selector)];
        result.total = matches.length;
        result.truncated = matches.length > limit;
        result.visibility = matches.slice(0, limit).map(element => {
            const style = getComputedStyle(element);
            const bounds = element.getBoundingClientRect();
            const ancestors = [];
            let ancestor = element.parentElement;
            let ancestor_count = 0;
            while (ancestor) {
                const parent_style = getComputedStyle(ancestor);
                if (ancestor.hasAttribute('hidden') || parent_style.display === 'none' ||
                    parent_style.visibility === 'hidden' ||
                    parent_style.visibility === 'collapse' ||
                    parent_style.opacity === '0') {
                    ancestor_count++;
                    if (ancestors.length < 8) ancestors.push({
                        tag: ancestor.localName, id: ancestor.id || null,
                        hidden_attribute: ancestor.hasAttribute('hidden'),
                        display: parent_style.display, visibility: parent_style.visibility,
                        opacity: parent_style.opacity
                    });
                }
                ancestor = ancestor.parentElement;
            }
            return {
                tag: element.localName, id: element.id || null,
                text: element.matches('input, textarea, select') ? null :
                    (element.textContent ?? '').trim().slice(0, 120),
                hidden_attribute: element.hasAttribute('hidden'),
                display: style.display, visibility: style.visibility, opacity: style.opacity,
                rendered: bounds.width > 0 && bounds.height > 0 &&
                    style.visibility !== 'hidden' && style.visibility !== 'collapse',
                ancestors, ancestors_truncated: ancestor_count > ancestors.length
            };
        });
    }
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


def _limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("limit must be an integer between 1 and 100") from error
    if not 1 <= limit <= _MAX_VISIBILITY_MATCHES:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return limit


def handle(arguments: argparse.Namespace) -> int:
    kinds = [kind for kind in ("text", "links", "fields", "visibility") if getattr(arguments, kind)]
    if not kinds:
        kinds = ["text", "links", "fields"]
    with connected_tab(arguments.port, arguments.tab) as page:
        root = resolve_target_frame(page, arguments.frame) if page is not None else None
        if root is None:
            if page is not None:
                print_no_frame_found(arguments.frame)
            return 1
        options: dict[str, Any] = {"selector": arguments.selector, "kinds": kinds}
        if arguments.visibility:
            options["limit"] = arguments.limit
        result = cdp.evaluate(root, _SCRIPT, options)
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
    parser.add_argument(
        "--visibility",
        action="store_true",
        help="include bounded visibility evidence for elements matching --selector",
    )
    parser.add_argument(
        "--limit",
        type=_limit,
        default=20,
        help="maximum visibility matches (1-100; default 20)",
    )
    parser.add_argument("--port", type=int, default=None, help="CDP port")
    parser.add_argument(
        "--tab", default=None, help="tab index, URL substring, or unique:<substring>"
    )
    parser.add_argument(
        "--frame", default="auto", help="frame index, URL substring, or 'auto' (top frame)"
    )
    parser.set_defaults(func=handle)
