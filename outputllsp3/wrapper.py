"""Module-discovery facade that maps LLSP3Project opcodes to callable helpers.

``ScratchWrapper`` wraps an ``LLSP3Project`` and uses schema introspection to
expose Scratch modules as first-class Python objects.  Callers can enumerate
available modules, look up individual blocks, and invoke them to generate block
IDs without knowing raw opcode strings.

Public API
----------
- ``ScratchWrapper(project)``  – wrap an ``LLSP3Project``
- ``available_modules(verified_only)`` – list module names derived from opcodes
- ``describe(module, name)``           – return block metadata for one opcode
- ``invoke(opcode, **kwargs)``         – generate a block by opcode string
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .schema import bundled_schema

CORE_SAFE_PREFIXES = {"data", "control", "operator", "procedures", "argument", "event", "sound"}


def _norm(value: str) -> str:
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', value)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    s = s.replace('-', '_')
    s = re.sub(r'[^A-Za-z0-9_]+', '_', s)
    return s.lower().strip('_')


def _guess_numeric(name: str) -> bool:
    name = name.upper()
    return any(k in name for k in ['NUM', 'ANGLE', 'POWER', 'SPEED', 'VALUE', 'DURATION', 'TIME', 'POSITION', 'ROTATION', 'DISTANCE', 'DEG', 'CM', 'MM', 'PERCENT', 'BRIGHTNESS', 'X', 'Y', 'PIXEL'])


@dataclass
class OpcodeFunction:
    project: Any
    opcode: str

    def __call__(self, /, **kwargs: Any) -> str:
        if '_inputs' in kwargs or '_fields' in kwargs:
            return self.project.add_block(self.opcode, inputs=kwargs.get('_inputs'), fields=kwargs.get('_fields'))
        schema = bundled_schema().get(self.opcode)
        if getattr(self.project, "strict_verified", False):
            prefix = self.opcode.split('_', 1)[0]
            if schema is None and prefix not in CORE_SAFE_PREFIXES:
                raise ValueError(f"Opcode not verified from reference llsp3 files: {self.opcode}")
        tmpl = self.project.catalog[self.opcode]
        inputs = {}
        fields = {}
        for ph in tmpl.placeholders:
            keys = [ph, ph.lower(), _norm(ph)]
            value = None
            hit = None
            for k in keys:
                if k in kwargs:
                    hit = k
                    value = kwargs[k]
                    break
            if hit is None:
                continue
            if schema and ph in schema.fields:
                fields[ph] = [str(value), None]
                continue
            if schema and ph in schema.inputs:
                meta = schema.inputs[ph]
                if 'menu' in meta:
                    menu = meta['menu']
                    is_dynamic = isinstance(value, str) and value in self.project.blocks
                    shadow_field_val = meta['menu'].get('default_value', 'A') if is_dynamic else str(value)
                    menu_block = self.project.add_block(
                        menu['opcode'],
                        shadow=True,
                        fields={menu['field_key']: [shadow_field_val, None]},
                    )
                    if is_dynamic:
                        # Reporter covering shadow menu: [3, reporter_id, shadow_id]
                        inputs[ph] = [3, value, menu_block]
                    else:
                        inputs[ph] = self.project.ref_menu(menu_block)
                    continue
                if meta.get('kind') == 2:
                    inputs[ph] = self.project.ref_bool(value)
                    continue
                if meta.get('kind') == 3:
                    if isinstance(value, str) and value in self.project.blocks:
                        fallback = 0
                        if 'fallback' in meta and isinstance(meta['fallback'], list) and len(meta['fallback']) > 1:
                            fallback = meta['fallback'][1]
                        inputs[ph] = self.project.ref_number(value, fallback)
                    elif _guess_numeric(ph):
                        inputs[ph] = self.project.lit_number(value)
                    else:
                        inputs[ph] = self.project.lit_text(value)
                    continue
            if isinstance(value, str) and value in self.project.blocks:
                inputs[ph] = self.project.ref_number(value) if _guess_numeric(ph) else self.project.ref_text(value)
            else:
                inputs[ph] = self.project.lit_number(value) if _guess_numeric(ph) else self.project.lit_text(value)
        return self.project.add_block(self.opcode, inputs=inputs, fields=fields)


@dataclass
class ModuleFacade:
    project: Any
    prefixes: list[str]

    def _all_matches(self) -> list[str]:
        out = []
        for opcode in self.project.catalog.registry:
            if any(opcode.startswith(prefix + '_') for prefix in self.prefixes):
                out.append(opcode)
        return sorted(out)

    def _resolve(self, name: str) -> str:
        wanted = _norm(name)
        matches = []
        verified = set(bundled_schema().verified_opcodes())
        for opcode in self._all_matches():
            if getattr(self.project, "strict_verified", False):
                prefix = opcode.split('_', 1)[0]
                if opcode not in verified and prefix not in CORE_SAFE_PREFIXES:
                    continue
            suffix = opcode.split('_', 1)[1]
            if _norm(suffix) == wanted:
                matches.append(opcode)
        if not matches:
            raise AttributeError(name)
        matches.sort(key=lambda op: (self.prefixes.index(op.split('_',1)[0]) if op.split('_',1)[0] in self.prefixes else 999, len(op)))
        return matches[0]

    def __getattr__(self, name: str) -> OpcodeFunction:
        return OpcodeFunction(self.project, self._resolve(name))

    def opcode(self, opcode: str, /, **kwargs: Any) -> str:
        if opcode not in self.project.catalog:
            raise KeyError(opcode)
        return OpcodeFunction(self.project, opcode)(**kwargs)

    def available(self, *, normalized: bool = True, verified_only: bool = False) -> list[str]:
        ops = self._all_matches()
        if verified_only:
            verified = set(bundled_schema().verified_opcodes())
            ops = [op for op in ops if op in verified or op.split("_",1)[0] in CORE_SAFE_PREFIXES]
        if not normalized:
            return ops
        return sorted({_norm(op.split('_', 1)[1]) for op in ops})

    def signatures(self, *, verified_only: bool = False) -> dict[str, str]:
        out = {}
        ops = self._all_matches()
        if verified_only:
            verified = set(bundled_schema().verified_opcodes())
            ops = [op for op in ops if op in verified or op.split("_",1)[0] in CORE_SAFE_PREFIXES]
        for opcode in ops:
            tmpl = self.project.catalog[opcode]
            name = _norm(opcode.split('_', 1)[1])
            params = [f"{_norm(p)}" for p in tmpl.placeholders]
            out[name] = f"{name}({', '.join(params)})"
        return dict(sorted(out.items()))

    def describe(self, name: str | None = None) -> dict[str, Any]:
        if name is None:
            return {
                'prefixes': list(self.prefixes),
                'functions': self.signatures(verified_only=getattr(self.project, 'strict_verified', False)),
            }
        opcode = name if name in self.project.catalog else self._resolve(name)
        tmpl = self.project.catalog[opcode]
        schema = bundled_schema().get(opcode)
        return {
            'opcode': opcode,
            'name': _norm(opcode.split('_', 1)[1]),
            'template': tmpl.text,
            'placeholders': list(tmpl.placeholders),
            'fields': list(schema.fields) if schema else [],
            'inputs': dict(schema.inputs) if schema else {},
            'signature': f"{_norm(opcode.split('_', 1)[1])}({', '.join(_norm(p) for p in tmpl.placeholders)})",
        }


@dataclass
class ScratchWrapper:
    project: Any

    def __post_init__(self):
        prefixes = sorted({t.prefix for t in self.project.catalog.registry.values()})
        self._modules = {}
        for prefix in prefixes:
            facade = ModuleFacade(self.project, [prefix])
            setattr(self, prefix, facade)
            self._modules[prefix] = facade
        aliases = {
            'events': ['flipperevents', 'event', 'ev3events', 'horizontalevents'],
            'move': ['flippermove', 'flippermoremove'],
            'motor': ['flippermotor', 'flippermoremotor', 'ev3motor', 'horizontalmotor'],
            'sensor': ['flippersensors', 'ev3sensors'],
            'light': ['flipperlight', 'flipperdisplay'],
            'sound': ['flippersound', 'sound'],
            'control': ['control', 'flippercontrol'],
            'vars': ['data'],
            'ops': ['operator'],
            'procedures': ['procedures'],
        }
        for alias, prefixes in aliases.items():
            facade = ModuleFacade(self.project, prefixes)
            setattr(self, alias, facade)
            self._modules[alias] = facade

    def available_modules(self, *, verified_only: bool = False) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "prefixes": list(facade.prefixes),
                "functions": facade.available(verified_only=verified_only),
            }
            for name, facade in sorted(self._modules.items())
        }

    def available(self, module: str | None = None, *, verified_only: bool = False) -> Any:
        if module is None:
            return self.available_modules(verified_only=verified_only)
        return self._modules[module].available(verified_only=verified_only)

    def describe(self, module: str, name: str | None = None) -> dict[str, Any]:
        return self._modules[module].describe(name)
