"""Raw export strategy.

Produces a minimal faithful reconstruction; each block becomes a direct
``project.sprite["blocks"][id] = json.loads(...)`` assignment.  Each line
carries an inline opcode comment for orientation.  Suitable for automated
round-trip testing.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import _pyrepr, _summary, _block_hint
from .builder import _opcode_label  # reuse the shared label lookup


def raw_lines(doc, style: str) -> list[str]:
    """Return source lines for a raw-style export."""
    sprite = doc.sprite
    blocks = sprite.get("blocks", {})
    variables = sprite.get("variables", {})
    lists = sprite.get("lists", {})
    comments = sprite.get("comments", {})
    summary = _summary(doc)

    lines: list[str] = []
    lines.append(f'# Source:  {Path(doc.path).name}')
    lines.append(f'# Style:   {style}  (exact-reconstruction — each block is a JSON assignment)')
    lines.append('# Tip:     for a fully readable decompilation use --style python-first')
    lines.append('')
    lines.append('from collections import OrderedDict')
    lines.append('import json')
    lines.append('')

    # Summary
    stats: list[str] = [f'blocks: {summary["blocks"]}']
    if summary['variables']:
        stats.append(f'variables: {summary["variables"]}')
    if summary['lists']:
        stats.append(f'lists: {summary["lists"]}')
    lines.append('# ' + ' | '.join(stats))
    for proc in summary['procedures']:
        lines.append(f'#   procedure: {proc["proccode"]}')
    lines.append(f'# {summary["opcode_count"]} unique opcodes')
    lines.append('')

    lines.append('def build(project, api, ns, enums):')
    lines.append('    project.clear_code()')
    lines.append('')

    if variables:
        lines.append('    # ── Variables ' + '─' * 62)
        for vid, pair in variables.items():
            name, val = pair[0], pair[1]
            if isinstance(val, str):
                lit = f"'{val}'" if "'" not in val else repr(val)
            else:
                lit = repr(val)
            lines.append(f'    project.variables[{vid!r}] = [{name!r}, {lit}]'
                         f'  # {name} = {lit}')
        lines.append('')
    if lists:
        lines.append('    # ── Lists ' + '─' * 65)
        for lid, pair in lists.items():
            name = pair[0]
            lines.append(f'    project.lists[{lid!r}] = [{name!r}, []]  # {name}')
        lines.append('')

    lines.append('    # ── Blocks (exact reconstruction) ' + '─' * 42)
    lines.append('    project.sprite["blocks"] = OrderedDict()')
    for bid, block in blocks.items():
        payload = json.dumps(block, ensure_ascii=False)
        opcode = block.get('opcode', '?')
        label = _opcode_label(opcode)
        comment = _block_hint(opcode, block, label)
        lines.append(
            f'    project.sprite["blocks"][{bid!r}] = json.loads({payload!r})'
            f'  # {comment}'
        )
    lines.append('')
    lines.append('    # ── Comments ' + '─' * 63)
    lines.append('    project.sprite["comments"] = OrderedDict()')
    for cid, comment in comments.items():
        payload = json.dumps(comment, ensure_ascii=False)
        lines.append(
            f'    project.sprite["comments"][{cid!r}] = json.loads({payload!r})'
        )
    lines.append('')
    return lines
