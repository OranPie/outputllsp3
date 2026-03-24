"""Custom procedure (custom block) management.

``ProcedureManager`` handles ``define_procedure``, ``call_procedure``, and
``attach_procedure_body``.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import LLSP3Project


class ProcedureManager:
    def __init__(self, project: "LLSP3Project") -> None:
        self._p = project

    def define_procedure(
        self, name: str, args: list[str], *, x: int, y: int,
        defaults: list[Any] | None = None,
    ) -> str:
        defid = self._p._id("def")
        argids = [self._p._id("arg") for _ in args]
        protoid = self._p._id("proto")
        proto_inputs = OrderedDict()
        for aid, aname in zip(argids, args):
            rep = self._p.add_block(
                "argument_reporter_string_number",
                parent=protoid,
                fields={"VALUE": [aname, None]},
                shadow=True,
            )
            proto_inputs[aid] = self._p._blocks.ref_menu(rep)

        actual_defaults: list[Any] = list(defaults) if defaults is not None else []
        actual_defaults = (actual_defaults + [""] * len(args))[:len(args)]

        def _default_str(d: Any) -> str:
            return "" if d is None or d == "" else str(d)

        mut = {
            "tagName": "mutation",
            "children": [],
            "proccode": name + ("" if not args else " " + " ".join(["%s"] * len(args))),
            "argumentids": json.dumps(argids),
            "argumentnames": json.dumps(args),
            "argumentdefaults": json.dumps([_default_str(d) for d in actual_defaults]),
            "warp": "false",
        }
        self._p.blocks[protoid] = OrderedDict([
            ("opcode", "procedures_prototype"),
            ("next", None),
            ("parent", defid),
            ("inputs", proto_inputs),
            ("fields", OrderedDict()),
            ("shadow", True),
            ("topLevel", False),
            ("mutation", mut),
        ])
        self._p.blocks[defid] = OrderedDict([
            ("opcode", "procedures_definition"),
            ("next", None),
            ("parent", None),
            ("inputs", OrderedDict({"custom_block": self._p._blocks.ref_menu(protoid)})),
            ("fields", OrderedDict()),
            ("shadow", False),
            ("topLevel", True),
            ("x", x),
            ("y", y),
        ])
        self._p._proc_meta[name] = {
            "proccode": mut["proccode"],
            "argids": argids,
            "defaults": actual_defaults,
        }
        return defid

    def call_procedure(self, name: str, args: list[Any] | tuple[Any, ...] = ()) -> str:
        meta = self._p._proc_meta[name]
        argids = meta["argids"]
        stored_defaults = meta.get("defaults", [""] * len(argids))
        ins = OrderedDict()
        expected = len(argids)
        actual = len(args)
        if actual != expected:
            import warnings
            warnings.warn(
                f"Procedure '{name}' expects {expected} argument(s), got {actual}.",
                stacklevel=2,
            )
        for i, aid in enumerate(argids):
            if i < len(args):
                ins[aid] = self._p._blocks._text_input(args[i])
            elif i < len(stored_defaults) and stored_defaults[i] not in ("", None):
                ins[aid] = self._p._blocks._text_input(stored_defaults[i])
        return self._p.add_block(
            "procedures_call",
            inputs=ins,
            mutation={
                "tagName": "mutation",
                "children": [],
                "proccode": meta["proccode"],
                "argumentids": json.dumps(meta["argids"]),
                "warp": "false",
            },
        )

    def attach_procedure_body(self, name: str, *block_ids: str) -> str | None:
        target_code = self._p._proc_meta[name]["proccode"]
        defid = None
        for bid, block in self._p.blocks.items():
            if block.get("opcode") == "procedures_definition":
                protoid = block["inputs"]["custom_block"][1]
                if self._p.blocks[protoid].get("mutation", {}).get("proccode") == target_code:
                    defid = bid
                    break
        if defid is None:
            raise KeyError(name)
        first = self._p._blocks.chain(defid, block_ids)
        self._p.blocks[defid]["next"] = first
        return first
