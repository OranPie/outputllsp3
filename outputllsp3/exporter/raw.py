"""Raw export strategy.

Produces a minimal faithful reconstruction; each block becomes a direct
``project.sprite["blocks"][id] = json.loads(...)`` assignment.  Each line
carries an inline opcode comment for orientation.  Suitable for automated
round-trip testing.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import _pyrepr, _summary
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
    lines.append("from collections import OrderedDict")
    lines.append("import json")
    lines.append("")
    lines.append(f"# exported from: {Path(doc.path).name}")
    lines.append(f"# export style: {style}")
    lines.append("# note: exact-reconstruction export — each block is a verbatim JSON assignment.")
    lines.append("#       opcode names are shown as inline comments for readability.")
    lines.append("")
    lines.append("def build(project, api, ns, enums):")
    lines.append("    project.clear_code()")
    lines.append("")
    lines.append("    # summary")
    lines.append(f"    # variables: {summary['variables']}")
    lines.append(f"    # lists:     {summary['lists']}")
    lines.append(f"    # blocks:    {summary['blocks']}")
    lines.append(f"    # opcodes:   {summary['opcode_count']} unique")
    for proc in summary["procedures"]:
        lines.append(f"    # procedure: {proc['proccode']}")
    for top in summary["top_levels"]:
        lines.append(f"    # top-level: {top['opcode']} @ ({top['x']}, {top['y']})")
    lines.append("")

    if variables:
        lines.append("    # variables")
        for vid, pair in variables.items():
            lines.append(f"    project.variables[{vid!r}] = {_pyrepr(pair)}  # name: {pair[0]!r}")
        lines.append("")
    if lists:
        lines.append("    # lists")
        for lid, pair in lists.items():
            lines.append(f"    project.lists[{lid!r}] = {_pyrepr(pair)}  # name: {pair[0]!r}")
        lines.append("")

    lines.append("    # blocks (exact reconstruction)")
    lines.append('    project.sprite["blocks"] = OrderedDict()')
    for bid, block in blocks.items():
        payload = json.dumps(block, ensure_ascii=False)
        label = _opcode_label(block.get("opcode", "?"))
        lines.append(f"    project.sprite[\"blocks\"][{bid!r}] = json.loads({payload!r})  # {label}")
    lines.append("")
    lines.append('    # comments')
    lines.append('    project.sprite["comments"] = OrderedDict()')
    for cid, comment in comments.items():
        payload = json.dumps(comment, ensure_ascii=False)
        lines.append(f"    project.sprite[\"comments\"][{cid!r}] = json.loads({payload!r})")
    lines.append("")
    return lines
