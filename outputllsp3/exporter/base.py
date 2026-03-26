"""Shared helpers for all export strategies.

This module provides utility functions used by all three export strategies
(raw, builder, python-first) and the ``export_llsp3_to_python`` entry point.
"""
from __future__ import annotations

import json
import keyword
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _pyrepr(obj: Any) -> str:
    return repr(obj)


# ── Pretty block formatting ───────────────────────────────────────────────────

_BLOCK_KEY_ORDER = ('opcode', 'inputs', 'fields', 'next', 'parent',
                    'shadow', 'topLevel', 'mutation', 'x', 'y')


def _val_repr(v: object) -> str:
    """Format a JSON-compatible value as a Python literal (True/False/None)."""
    if v is None:
        return 'None'
    if isinstance(v, bool):
        return 'True' if v else 'False'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, list):
        return '[' + ', '.join(_val_repr(x) for x in v) + ']'
    if isinstance(v, dict):
        if not v:
            return '{}'
        parts = ', '.join(f'{k!r}: {_val_repr(vv)}' for k, vv in v.items())
        return '{' + parts + '}'
    return repr(v)


def _fmt_block_dict(block: dict, indent: str = '    ') -> str:
    """Format a Scratch block as a readable multi-line Python dict literal.

    Skips noise-free defaults (shadow=False, topLevel=False, comment=None)
    so only meaningful fields are shown.
    """
    pad = indent + '    '
    lines = ['{']
    ordered = [k for k in _BLOCK_KEY_ORDER if k in block] + \
              [k for k in block if k not in _BLOCK_KEY_ORDER]
    for key in ordered:
        val = block[key]
        # Omit low-value defaults to reduce visual noise
        if key == 'shadow' and val is False:
            continue
        if key == 'topLevel' and val is False:
            continue
        if key == 'comment' and val is None:
            continue
        if key == 'mutation' and not val:
            continue
        lines.append(f"{pad}'{key}': {_val_repr(val)},")
    lines.append(f'{indent}}}')
    return '\n'.join(lines)


def _block_hint(opcode: str, block: dict, label: str) -> str:
    """Build a rich comment like 'motor: run (direction)  [DIRECTION=clockwise]'."""
    fields = block.get('fields', {})
    hints = []
    for k, v in fields.items():
        if not (isinstance(v, list) and v and v[0] is not None):
            continue
        # Shorten verbose SPIKE field keys: 'field_flippermotor_menu_foo' → 'foo'
        short_k = k
        if short_k.startswith('field_'):
            short_k = short_k[6:]
        # Strip known namespace prefixes
        for prefix in (
            'flippermotor_', 'flippermove_', 'flippermoremove_',
            'flippermoremotor_', 'flippersensors_', 'flipperevents_',
            'flipperlight_', 'flippersound_', 'flippermore_',
            'flippermoresensors_', 'flippermusic_', 'flipperoperator_',
            'flippercontrol_', 'horizontalmotor_', 'horizontalmove_',
            'horizontalevents_',
        ):
            if short_k.startswith(prefix):
                short_k = short_k[len(prefix):]
                break
        # Strip inner _menu_ sub-prefix
        if '_menu_' in short_k:
            short_k = short_k.split('_menu_')[-1]
        hints.append(f'{short_k}={v[0]}')
    if hints:
        return f'{label}  [{", ".join(hints)}]'
    return label


def _collect_stack_bids(root_bid: str, blocks: dict) -> list[str]:
    """BFS from *root_bid* collecting every block ID that belongs to this stack.

    Follows both ``next`` links (linear body) and input sub-stacks
    (``SUBSTACK``, ``SUBSTACK2``, loop bodies, etc.) so the entire tree is
    captured.  Returns IDs in encounter order (root first).
    """
    result: list[str] = []
    queue = [root_bid]
    seen: set[str] = set()
    while queue:
        cur = queue.pop(0)
        if cur not in blocks or cur in seen:
            continue
        seen.add(cur)
        result.append(cur)
        nxt = blocks[cur].get('next')
        if nxt:
            queue.append(nxt)
        for inp_val in blocks[cur].get('inputs', {}).values():
            if isinstance(inp_val, list):
                for item in inp_val:
                    if isinstance(item, str) and item in blocks and item not in seen:
                        queue.append(item)
    return result


def _linear_chain_labels(root_bid: str, blocks: dict, label_fn, max_steps: int = 6) -> tuple[list[str], int]:
    """Follow ``next`` links from *root_bid*, collecting opcode labels.

    Returns ``(label_list, total_depth)`` where *label_list* contains at most
    *max_steps* labels and *total_depth* is the true chain length.
    """
    parts: list[str] = []
    cur: str | None = root_bid
    seen: set[str] = set()
    while cur and cur not in seen and cur in blocks:
        seen.add(cur)
        if len(parts) < max_steps:
            parts.append(label_fn(blocks[cur].get('opcode', '?')))
        cur = blocks[cur].get('next')
    return parts, len(seen)


def _build_stack_groups(blocks: dict) -> list[tuple[str | None, list[str]]]:
    """Group block IDs by their top-level root block.

    Returns a list of ``(root_bid, [bid, ...])`` pairs — one per top-level
    block.  An extra ``(None, [orphan_ids])`` entry is appended for any block
    that is not reachable from any top-level root.
    """
    top_ids = [bid for bid, b in blocks.items() if b.get('topLevel')]
    owned: set[str] = set()
    groups: list[tuple[str | None, list[str]]] = []
    for root in top_ids:
        group = _collect_stack_bids(root, blocks)
        owned.update(group)
        groups.append((root, group))
    orphans = [bid for bid in blocks if bid not in owned]
    if orphans:
        groups.append((None, orphans))
    return groups


def _summary(doc) -> dict[str, Any]:
    blocks = doc.blocks
    opcode_counts = Counter(b.get("opcode") for b in blocks.values())
    procedures: list[dict[str, Any]] = []
    top_levels: list[dict[str, Any]] = []
    for bid, block in blocks.items():
        if block.get("opcode") == "procedures_prototype":
            procedures.append({
                "id": bid,
                "proccode": block.get("mutation", {}).get("proccode", ""),
                "argnames": (
                    json.loads(block.get("mutation", {}).get("argumentnames", "[]"))
                    if block.get("mutation") else []
                ),
            })
        if block.get("topLevel"):
            top_levels.append({
                "id": bid,
                "opcode": block.get("opcode"),
                "x": block.get("x"),
                "y": block.get("y"),
            })
    return {
        "variables": len(doc.variables),
        "lists": len(doc.sprite.get("lists", {})),
        "blocks": len(blocks),
        "opcode_count": len(opcode_counts),
        "top_levels": top_levels,
        "procedures": procedures,
        "opcode_counts": dict(sorted(opcode_counts.items())),
    }


def _sanitize(name: str, fallback: str = "v") -> str:
    # Allow Unicode letters/digits — Python 3 identifiers support them.
    # Non-word characters (including ASCII punctuation) become underscores.
    name = re.sub(r"[^\w]+", "_", name, flags=re.UNICODE).strip("_") or fallback
    if name[0].isdigit():
        name = "_" + name
    if keyword.iskeyword(name):
        name += "_"
    return name


def _extract_literal(inp):
    if (
        isinstance(inp, list) and inp and inp[0] == 1
        and len(inp) > 1 and isinstance(inp[1], list) and len(inp[1]) == 2
    ):
        return inp[1][1]
    return None


def _value_ref(inp):
    if isinstance(inp, list) and inp:
        if inp[0] in (2, 3) and len(inp) > 1 and isinstance(inp[1], str):
            return inp[1]
        if inp[0] == 1 and len(inp) > 1 and isinstance(inp[1], str):
            return inp[1]
    return None
