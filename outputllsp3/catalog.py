"""Block-template registry built from a Scratch ``strings.json`` definitions file.

The catalog maps Scratch opcodes to human-readable labels and menu definitions.
It is used primarily for documentation helpers and the strict-verified opcode
mode; normal code generation does not require it.

Public API
----------
- ``BlockTemplate``  – dataclass holding the opcode, label, and argument slots
  for one block type.
- ``BlockCatalog(strings_path)``  – loads ``strings.json`` and builds the
  registry; exposes ``get(opcode)``, ``to_dict()``, and ``__iter__()``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_\-]+)\}")

CORE_OPCODE_TEXT = {
    "data_variable": "{VARIABLE}",
    "data_setvariableto": "set {VARIABLE} to {VALUE}",
    "data_changevariableby": "change {VARIABLE} by {VALUE}",
    "argument_reporter_string_number": "{VALUE}",
    "control_if": "if {CONDITION} then",
    "control_repeat_until": "repeat until {CONDITION}",
    "control_wait": "wait {DURATION} seconds",
    "operator_add": "{NUM1} + {NUM2}",
    "operator_subtract": "{NUM1} - {NUM2}",
    "operator_multiply": "{NUM1} * {NUM2}",
    "operator_divide": "{NUM1} / {NUM2}",
    "operator_lt": "{OPERAND1} < {OPERAND2}",
    "operator_gt": "{OPERAND1} > {OPERAND2}",
    "operator_equals": "{OPERAND1} = {OPERAND2}",
    "operator_or": "{OPERAND1} or {OPERAND2}",
    "operator_and": "{OPERAND1} and {OPERAND2}",
    "operator_mathop": "{OPERATOR} {NUM}",
    "procedures_definition": "define",
    "procedures_prototype": "prototype",
    "procedures_call": "call",
    "data_addtolist": "add {ITEM} to {LIST}",
    "data_deletealloflist": "delete all of {LIST}",
    "data_lengthoflist": "length of {LIST}",
    "data_itemoflist": "item {INDEX} of {LIST}",
    "data_replaceitemoflist": "replace item {INDEX} of {LIST} with {ITEM}",
    "data_listcontainsitem": "{LIST} contains {ITEM}",
    "data_listcontents": "{LIST}",
}


@dataclass(frozen=True)
class BlockTemplate:
    opcode: str
    text: str
    placeholders: list[str]
    prefix: str


class BlockCatalog:
    def __init__(self, strings_path: str | Path):
        raw = json.loads(Path(strings_path).read_text(encoding="utf-8"))
        lang = raw.get("en-us", raw)
        self.registry: dict[str, BlockTemplate] = {}
        for opcode, text in lang.items():
            self.registry[opcode] = BlockTemplate(
                opcode=opcode,
                text=text,
                placeholders=PLACEHOLDER_RE.findall(text),
                prefix=opcode.split("_", 1)[0],
            )
        for opcode, text in CORE_OPCODE_TEXT.items():
            self.registry.setdefault(
                opcode,
                BlockTemplate(opcode, text, PLACEHOLDER_RE.findall(text), opcode.split("_", 1)[0]),
            )

    def __contains__(self, opcode: str) -> bool:
        return opcode in self.registry

    def __getitem__(self, opcode: str) -> BlockTemplate:
        return self.registry[opcode]

    def all(self) -> list[BlockTemplate]:
        return [self.registry[k] for k in sorted(self.registry)]

    def to_dict(self) -> dict[str, Any]:
        return {
            k: {"text": v.text, "placeholders": v.placeholders, "prefix": v.prefix}
            for k, v in sorted(self.registry.items())
        }
