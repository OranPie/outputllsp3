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
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or fallback
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
