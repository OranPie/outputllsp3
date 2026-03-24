"""Builder export strategy.

Produces the same semantics as the raw export but with module structure and
commentary that makes the file human-editable as a build script.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import _pyrepr, _summary


def builder_lines(doc) -> list[str]:
    """Return source lines for a builder-style export."""
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
    lines.append("# export style: builder")
    lines.append("# note: this is still an exact export, but shaped to be easier to read and edit than the raw dump.")
    lines.append("")
    lines.append("def _set_block(project, block_id, payload):")
    lines.append('    project.sprite["blocks"][block_id] = payload')
    lines.append("")
    lines.append("def build(project, api, ns, enums):")
    lines.append("    project.clear_code()")
    lines.append("")
    lines.append("    # summary")
    lines.append(f"    # variables: {summary['variables']}")
    lines.append(f"    # lists: {summary['lists']}")
    lines.append(f"    # blocks: {summary['blocks']}")
    lines.append(f"    # unique opcodes: {summary['opcode_count']}")
    for proc in summary["procedures"]:
        lines.append(f"    # procedure: {proc['proccode']}")
    lines.append("")
    lines.append("    # high-level hints")
    opcode_counts = summary["opcode_counts"]
    if "flipperevents_whenProgramStarts" in opcode_counts:
        lines.append("    # hint: project has one or more program-start entry stacks")
    if any(op.startswith("procedures_") for op in opcode_counts):
        lines.append("    # hint: project uses custom procedures; see procedure comments above")
    if any(op.startswith("data_") for op in opcode_counts):
        lines.append("    # hint: project uses variables/lists; resources are recreated first, then blocks are restored exactly")
    lines.append("")

    if variables:
        lines.append("    # recreate variables with original ids/names")
        for vid, pair in variables.items():
            lines.append(f"    project.variables[{vid!r}] = {_pyrepr(pair)}")
        lines.append("")
    if lists:
        lines.append("    # recreate lists with original ids/names")
        for lid, pair in lists.items():
            lines.append(f"    project.lists[{lid!r}] = {_pyrepr(pair)}")
        lines.append("")

    lines.append('    project.sprite["blocks"] = OrderedDict()')
    lines.append("")
    top_ids = {bid for bid, block in blocks.items() if block.get("topLevel")}
    proc_proto_ids = {bid for bid, block in blocks.items() if block.get("opcode") == "procedures_prototype"}
    proc_def_ids = {bid for bid, block in blocks.items() if block.get("opcode") == "procedures_definition"}

    nonlocal_lines = lines

    def emit_group(title: str, pred):
        emitted = False
        for bid, block in blocks.items():
            if pred(bid, block):
                nonlocal_lines.append(f"    # {title}" if not emitted else "")
                nonlocal_lines.append(
                    f"    _set_block(project, {bid!r}, "
                    f"json.loads({json.dumps(block, ensure_ascii=False)!r}))"
                )
                emitted = True
        if emitted:
            nonlocal_lines.append("")

    emit_group("top-level blocks", lambda bid, block: bid in top_ids)
    emit_group(
        "procedure definitions and prototypes",
        lambda bid, block: bid in proc_def_ids or bid in proc_proto_ids,
    )
    emit_group(
        "remaining blocks",
        lambda bid, block: bid not in top_ids and bid not in proc_def_ids and bid not in proc_proto_ids,
    )

    lines.append('    project.sprite["comments"] = OrderedDict()')
    if comments:
        lines.append("    # comments")
        for cid, comment in comments.items():
            lines.append(
                f"    project.sprite[\"comments\"][{cid!r}] = "
                f"json.loads({json.dumps(comment, ensure_ascii=False)!r})"
            )
        lines.append("")
    return [line for line in lines if line != ""] + [""]
