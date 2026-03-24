"""Raw export strategy.

Produces a minimal faithful reconstruction; each block becomes a direct
``project.sprite["blocks"][id] = json.loads(...)`` assignment.  Each line
carries an inline opcode comment for orientation.  Suitable for automated
round-trip testing.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import _pyrepr, _summary, _block_hint, _build_stack_groups, _linear_chain_labels
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
    lines.append('')

    stack_groups = _build_stack_groups(blocks)
    total_stacks = len(stack_groups)

    for stack_idx, (root_bid, group_bids) in enumerate(stack_groups, 1):
        if root_bid is None:
            lines.append('    # ── Orphaned blocks ' + '─' * 54)
            for bid in group_bids:
                block = blocks[bid]
                payload = json.dumps(block, ensure_ascii=False)
                opcode = block.get('opcode', '?')
                label = _opcode_label(opcode)
                comment = _block_hint(opcode, block, label)
                lines.append(
                    f'    project.sprite["blocks"][{bid!r}] = json.loads({payload!r})'
                    f'  # {comment}'
                )
            lines.append('')
            continue

        root_block = blocks[root_bid]
        root_op = root_block.get('opcode', '?')
        root_label = _opcode_label(root_op)

        # Section header
        is_proc = root_op == 'procedures_definition'
        if is_proc:
            proto_id = (root_block.get('inputs', {}).get('custom_block', [None, None]) or [None, None])[1]
            proccode = ''
            if proto_id and proto_id in blocks:
                proccode = blocks[proto_id].get('mutation', {}).get('proccode', '')
            section = f'procedure: {proccode}' if proccode else 'procedure definition'
        else:
            section = f'stack {stack_idx}/{total_stacks}: {root_label}'

        bar_len = max(2, 72 - len(section))
        lines.append(f'    # ══ {section} {"═" * bar_len}')

        # Chain summary
        chain_labels, chain_depth = _linear_chain_labels(root_bid, blocks, _opcode_label, max_steps=5)
        chain_str = ' → '.join(chain_labels)
        if chain_depth > len(chain_labels):
            chain_str += f' → … ({chain_depth} blocks total)'
        else:
            noun = 'block' if chain_depth == 1 else 'blocks'
            chain_str += f'  ({chain_depth} {noun})'
        lines.append(f'    #   {chain_str}')
        lines.append('')

        for bid in group_bids:
            block = blocks[bid]
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
