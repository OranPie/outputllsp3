"""Verified-opcode registry extracted from a reference LLSP3 project.

The schema registry provides the canonical list of opcodes that are known to
be accepted by the LEGO SPIKE app.  Used by ``LLSP3Project.set_strict_verified``
to raise early if an unrecognised opcode is used in generated projects.

Public API
----------
- ``OpcodeSchema``        – dataclass holding the full opcode-to-metadata mapping.
- ``SchemaRegistry``      – in-memory registry; use ``bundled_schema()`` for the
  cached singleton built from the bundled ``block_reference.llsp3``.
- ``bundled_schema()``    – ``@lru_cache`` factory returning the singleton instance.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import importlib.resources as ir


@dataclass
class MenuSchema:
    opcode: str
    field_key: str | None
    default_value: Any | None = None


@dataclass
class OpcodeSchema:
    opcode: str
    fields: list[str]
    inputs: dict[str, dict[str, Any]]


class SchemaRegistry:
    def __init__(self, schemas: dict[str, OpcodeSchema]):
        self.schemas = schemas

    def get(self, opcode: str) -> OpcodeSchema | None:
        return self.schemas.get(opcode)

    def verified_opcodes(self) -> list[str]:
        return sorted(self.schemas)

    def to_dict(self) -> dict[str, Any]:
        return {
            op: {
                "fields": list(schema.fields),
                "inputs": dict(schema.inputs),
            }
            for op, schema in sorted(self.schemas.items())
        }


def _read_project_from_llsp3(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path, 'r') as zf:
        scratch_bytes = zf.read('scratch.sb3')
    import io
    with zipfile.ZipFile(io.BytesIO(scratch_bytes), 'r') as zf:
        return json.loads(zf.read('project.json').decode('utf-8'))


def _menu_schema_for_ref(blocks: dict[str, dict[str, Any]], payload: list[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {'kind': payload[0]}
    if payload[0] == 1 and isinstance(payload[1], str) and payload[1] in blocks:
        menu = blocks[payload[1]]
        field_key = next(iter(menu.get('fields', {}).keys()), None)
        default_value = None
        if field_key:
            fv = menu['fields'][field_key]
            default_value = fv[0] if isinstance(fv, list) and fv else None
        out['menu'] = {
            'opcode': menu.get('opcode'),
            'field_key': field_key,
            'default_value': default_value,
        }
    elif payload[0] == 3 and len(payload) > 2:
        out['fallback'] = payload[2]
    return out


def learn_schema_from_project(project: dict[str, Any]) -> dict[str, OpcodeSchema]:
    schemas: dict[str, OpcodeSchema] = {}
    for target in project.get('targets', []):
        if target.get('isStage'):
            continue
        blocks = target.get('blocks', {})
        for bid, block in blocks.items():
            opcode = block.get('opcode')
            if not opcode:
                continue
            existing = schemas.get(opcode)
            if existing is None:
                existing = OpcodeSchema(opcode=opcode, fields=[], inputs={})
                schemas[opcode] = existing
            for fk in block.get('fields', {}).keys():
                if fk not in existing.fields:
                    existing.fields.append(fk)
            for ik, payload in block.get('inputs', {}).items():
                if ik not in existing.inputs and isinstance(payload, list):
                    existing.inputs[ik] = _menu_schema_for_ref(blocks, payload)
    return schemas


@lru_cache(maxsize=1)
def bundled_schema() -> SchemaRegistry:
    refs = []
    pkg = 'outputllsp3.resources'
    for name in ['block_reference.llsp3', 'full.llsp3', 'ok.llsp3']:
        try:
            with ir.as_file(ir.files(pkg).joinpath(name)) as p:
                refs.append(Path(p))
        except Exception:
            pass
    merged: dict[str, OpcodeSchema] = {}
    for ref in refs:
        proj = _read_project_from_llsp3(ref)
        learned = learn_schema_from_project(proj)
        for op, schema in learned.items():
            if op not in merged:
                merged[op] = schema
            else:
                cur = merged[op]
                for f in schema.fields:
                    if f not in cur.fields:
                        cur.fields.append(f)
                for ik, iv in schema.inputs.items():
                    cur.inputs.setdefault(ik, iv)
    return SchemaRegistry(merged)
