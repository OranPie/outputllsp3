"""Low-level LLSP3 project builder and serialiser.

``LLSP3Project`` is the central object of the package.  It holds the in-memory
representation of a Scratch project (blocks, variables, lists, procedures,
assets) and provides the full block-creation API used by every transpiler.

Typical usage::

    project = LLSP3Project('ok.llsp3', 'strings.json')
    api = API(project)
    api.flow.start(api.move.forward_cm(20))
    project.save('out.llsp3')

Architecture
------------
- **Block creation** – ``add_block()`` generates a unique ID, registers the
  block in ``self.blocks``, and wires parent / next / input pointers.
- **Variables & lists** – ``add_variable()`` / ``add_list()`` declare sprite-level
  resources; ``variable()`` / ``list_item()`` generate reporter blocks.
- **Procedures** – ``define_procedure()`` / ``call_procedure()`` / ``arg()``
  manage custom Scratch procedures including default-value mutation fields.
- **Validation** – when ``set_strict_verified(True)`` all opcodes are checked
  against the bundled schema; additional structural checks run on ``save()``.
- **Serialisation** – ``save()`` rebuilds the llsp3 ZIP from the template,
  normalises asset hashes, injects generated ``project.json``, and writes to
  the target path.

Public API
----------
``LLSP3Project``, ``add_block``, ``add_variable``, ``add_list``,
``define_procedure``, ``call_procedure``, ``arg``, ``chain``,
``set_strict_verified``, ``save``, ``cleanup``
"""
from __future__ import annotations

import json
import shutil
import hashlib
import tempfile
import uuid
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

from .catalog import BlockCatalog


class LLSP3Project:
    def __init__(self, template_llsp3: str | Path, strings_json: str | Path, *, sprite_name: str = "OutputLLSP3 Generated"):
        self.catalog = BlockCatalog(strings_json)
        self.template_llsp3 = Path(template_llsp3)
        self.tmpdir = Path(tempfile.mkdtemp(prefix="outputllsp3_"))
        self.outer_dir = self.tmpdir / "outer"
        self.inner_dir = self.tmpdir / "inner"
        self.outer_dir.mkdir(parents=True, exist_ok=True)
        self.inner_dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self._proc_meta: dict[str, dict[str, Any]] = {}
        self.default_namespace: str = ""
        self.function_namespace_mode: bool = False
        self.strict_verified: bool = False
        self._unpack()
        self.project_json["targets"][self.sprite_index]["name"] = sprite_name
        self.clear_code()

    def _unpack(self) -> None:
        with zipfile.ZipFile(self.template_llsp3, "r") as zf:
            zf.extractall(self.outer_dir)
        with zipfile.ZipFile(self.outer_dir / "scratch.sb3", "r") as zf:
            zf.extractall(self.inner_dir)
        self.manifest = json.loads((self.outer_dir / "manifest.json").read_text(encoding="utf-8"))
        self.project_json = json.loads((self.inner_dir / "project.json").read_text(encoding="utf-8"))
        self.sprite_index = next(i for i, t in enumerate(self.project_json["targets"]) if not t.get("isStage"))

    @property
    def sprite(self) -> dict[str, Any]:
        return self.project_json["targets"][self.sprite_index]

    @property
    def blocks(self) -> OrderedDict[str, dict[str, Any]]:
        return self.sprite["blocks"]

    @property
    def variables(self) -> OrderedDict[str, list[Any]]:
        return self.sprite["variables"]

    @property
    def comments(self) -> OrderedDict[str, dict[str, Any]]:
        return self.sprite["comments"]

    @property
    def lists(self) -> OrderedDict[str, list[Any]]:
        return self.sprite["lists"]

    def clear_code(self) -> None:
        self.sprite["blocks"] = OrderedDict()
        self.sprite["variables"] = OrderedDict()
        self.sprite["lists"] = OrderedDict()
        self.sprite["broadcasts"] = OrderedDict()
        self.sprite["comments"] = OrderedDict()
        self.project_json["monitors"] = []
        self._proc_meta.clear()

    def sanitize_namespace(self, value: str) -> str:
        import re
        value = re.sub(r"[^A-Za-z0-9_]+", "__", str(value)).strip("_")
        return value

    def set_default_namespace(self, namespace: str | None, *, function_namespace: bool = False) -> None:
        self.default_namespace = self.sanitize_namespace(namespace or "")
        self.function_namespace_mode = function_namespace

    def set_strict_verified(self, enabled: bool = True) -> None:
        self.strict_verified = enabled

    def qualify_var_name(self, name: str, namespace: str | None = None, raw: bool = False) -> str:
        if raw:
            return name
        ns = self.sanitize_namespace(namespace if namespace is not None else self.default_namespace)
        if not ns:
            return name
        if name.startswith(ns + "__"):
            return name
        return f"{ns}__{name}"

    def add_comment(self, block_id: str, text: str, *, x: int | None = None, y: int | None = None, width: int = 260, height: int = 120, minimized: bool = False) -> str:
        cid = self._id("c")
        self.comments[cid] = OrderedDict([
            ("blockId", block_id),
            ("x", 0 if x is None else x),
            ("y", 0 if y is None else y),
            ("width", width),
            ("height", height),
            ("minimized", minimized),
            ("text", text),
        ])
        return cid

    def cleanup(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _id(self, prefix: str = "b") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}_{uuid.uuid4().hex[:6]}"

    def lit_number(self, value: int | float | str):
        return [1, [4, str(value)]]

    def lit_decimal(self, value: int | float | str):
        return [1, [5, str(value)]]

    def lit_text(self, value: Any):
        return [1, [10, str(value)]]

    def ref_number(self, block_id: str, fallback: int | float | str = 0):
        return [3, block_id, [4, str(fallback)]]

    def ref_text(self, block_id: str, fallback: Any = 0):
        return [3, block_id, [10, str(fallback)]]

    def ref_bool(self, block_id: str):
        return [2, block_id]

    def ref_stmt(self, block_id: str):
        return [2, block_id]

    def ref_menu(self, block_id: str):
        return [1, block_id]

    BOOLEAN_OPCODES = {
        "operator_lt", "operator_gt", "operator_equals", "operator_or", "operator_and", "operator_not",
        "data_listcontainsitem",
    }
    BUILTIN_EXTENSION_PREFIXES = {"argument", "control", "data", "operator", "procedures"}

    def _block_opcode(self, block_id: Any) -> str | None:
        if isinstance(block_id, str) and block_id in self.blocks:
            return self.blocks[block_id].get("opcode")
        return None

    def is_boolean_opcode(self, opcode: str | None) -> bool:
        return opcode in self.BOOLEAN_OPCODES if opcode else False

    def _normalize_asset_hashes(self) -> None:
        asset_fields = ("costumes", "sounds")
        rename_map: dict[str, tuple[str, str]] = {}
        for target in self.project_json.get("targets", []):
            for field in asset_fields:
                for asset in target.get(field, []):
                    md5ext = asset.get("md5ext")
                    if not md5ext:
                        continue
                    if md5ext in rename_map:
                        digest, normalized_name = rename_map[md5ext]
                        asset["assetId"] = digest
                        asset["md5ext"] = normalized_name
                        continue
                    asset_path = self.inner_dir / md5ext
                    if not asset_path.exists():
                        continue
                    data = asset_path.read_bytes()
                    digest = hashlib.md5(data).hexdigest()
                    ext = asset_path.suffix or (("." + asset.get("dataFormat", "")) if asset.get("dataFormat") else "")
                    correct_name = f"{digest}{ext}"
                    if asset_path.name != correct_name:
                        correct_path = self.inner_dir / correct_name
                        if not correct_path.exists():
                            asset_path.rename(correct_path)
                        else:
                            asset_path.unlink()
                        asset_path = correct_path
                    rename_map[md5ext] = (digest, asset_path.name)
                    asset["assetId"] = digest
                    asset["md5ext"] = asset_path.name

    def _child_block_ids(self, inputs: dict[str, Any] | None) -> list[str]:
        out = []
        for spec in (inputs or {}).values():
            if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], str) and spec[1] in self.blocks:
                out.append(spec[1])
        return out

    def add_block(self, opcode: str, *, inputs: dict[str, Any] | None = None, fields: dict[str, Any] | None = None,
                  parent: str | None = None, next: str | None = None, shadow: bool = False,
                  top_level: bool = False, x: int = 0, y: int = 0, mutation: dict[str, Any] | None = None) -> str:
        if opcode not in self.catalog:
            raise KeyError(f"Unknown opcode: {opcode}")
        bid = self._id()
        block = OrderedDict()
        block["opcode"] = opcode
        block["next"] = next
        block["parent"] = parent
        block["inputs"] = OrderedDict(inputs or {})
        block["fields"] = OrderedDict(fields or {})
        block["shadow"] = shadow
        block["topLevel"] = top_level
        if top_level:
            block["x"] = x
            block["y"] = y
        if mutation is not None:
            block["mutation"] = mutation
        self.blocks[bid] = block
        for child in self._child_block_ids(block["inputs"]):
            if self.blocks[child].get("parent") in (None, "INLINE", "TEMP"):
                self.blocks[child]["parent"] = bid
        return bid

    def chain(self, container: str, block_ids: Iterable[str]) -> str | None:
        ids = [bid for bid in block_ids if bid]
        for i, bid in enumerate(ids):
            self.blocks[bid]["parent"] = container if i == 0 else ids[i - 1]
            self.blocks[bid]["next"] = ids[i + 1] if i + 1 < len(ids) else None
        return ids[0] if ids else None

    def chain_inline(self, *block_ids: str) -> str | None:
        return self.chain("INLINE", block_ids)

    def add_variable(self, name: str, value: Any = 0, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        vid = self._id("var")
        self.variables[vid] = [qname, value]
        return vid

    def variable_id(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        for vid, (n, _) in self.variables.items():
            if n == qname:
                return vid
        raise KeyError(qname)

    def variable(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_variable", fields={"VARIABLE": [qname, self.variable_id(name, namespace=namespace, raw=raw)]})

    def set_variable(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_setvariableto", inputs={"VALUE": self._text_input(value)}, fields={"VARIABLE": [qname, self.variable_id(name, namespace=namespace, raw=raw)]})

    def change_variable(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_changevariableby", inputs={"VALUE": self._text_input(value)}, fields={"VARIABLE": [qname, self.variable_id(name, namespace=namespace, raw=raw)]})

    def add_list(self, name: str, value: list[Any] | None = None, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        lid = self._id("list")
        self.lists[lid] = [qname, list(value or [])]
        return lid

    def list_id(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.qualify_var_name(name, namespace=namespace, raw=raw)
        for lid, (n, _) in self.lists.items():
            if n == qname:
                return lid
        raise KeyError(qname)

    def list_name(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.qualify_var_name(name, namespace=namespace, raw=raw)

    def list_contents(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_listcontents", fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_length(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_lengthoflist", fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_itemoflist", inputs={"INDEX": self._num_input(index)}, fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_contains(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_listcontainsitem", inputs={"ITEM": self._text_input(item)}, fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_replace(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_replaceitemoflist", inputs={"INDEX": self._num_input(index), "ITEM": self._text_input(item)}, fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_delete(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_deleteoflist", inputs={"INDEX": self._num_input(index)}, fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_insert(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_insertatlist", inputs={"INDEX": self._num_input(index), "ITEM": self._text_input(item)}, fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_append(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_addtolist", inputs={"ITEM": self._text_input(item)}, fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def list_clear(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        qname = self.list_name(name, namespace=namespace, raw=raw)
        return self.add_block("data_deletealloflist", fields={"LIST": [qname, self.list_id(name, namespace=namespace, raw=raw)]})

    def _num_input(self, value: Any):
        if isinstance(value, str) and value in self.blocks:
            return self.ref_number(value)
        if isinstance(value, (int, float)):
            return self.lit_number(value)
        if isinstance(value, list):
            return value
        return self.lit_text(value)

    def _text_input(self, value: Any):
        if isinstance(value, str) and value in self.blocks:
            return self.ref_text(value)
        if isinstance(value, list):
            return value
        return self.lit_text(value)

    def _bool_input(self, value: Any):
        if isinstance(value, str) and value in self.blocks:
            if self.is_boolean_opcode(self._block_opcode(value)):
                return self.ref_bool(value)
            return self.ref_bool(self.gt(value, 0))
        if isinstance(value, bool):
            return self.ref_bool(self.eq(1, 1 if value else 0))
        if isinstance(value, (int, float)):
            return self.ref_bool(self.eq(1, 1 if value else 0))
        if isinstance(value, list):
            return value
        return self.ref_bool(self.eq(1, 1 if value else 0))

    def add(self, a: Any, b: Any) -> str: return self.add_block("operator_add", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})
    def sub(self, a: Any, b: Any) -> str: return self.add_block("operator_subtract", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})
    def mul(self, a: Any, b: Any) -> str: return self.add_block("operator_multiply", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})
    def div(self, a: Any, b: Any) -> str: return self.add_block("operator_divide", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})
    def lt(self, a: Any, b: Any) -> str: return self.add_block("operator_lt", inputs={"OPERAND1": self._num_input(a), "OPERAND2": self._num_input(b)})
    def gt(self, a: Any, b: Any) -> str: return self.add_block("operator_gt", inputs={"OPERAND1": self._num_input(a), "OPERAND2": self._num_input(b)})
    def eq(self, a: Any, b: Any) -> str: return self.add_block("operator_equals", inputs={"OPERAND1": self._num_input(a), "OPERAND2": self._num_input(b)})
    def or_(self, a: Any, b: Any) -> str: return self.add_block("operator_or", inputs={"OPERAND1": self._bool_input(a), "OPERAND2": self._bool_input(b)})
    def and_(self, a: Any, b: Any) -> str: return self.add_block("operator_and", inputs={"OPERAND1": self._bool_input(a), "OPERAND2": self._bool_input(b)})
    def not_(self, value: Any) -> str: return self.add_block("operator_not", inputs={"OPERAND": self._bool_input(value)})
    def mathop(self, op: str, value: Any) -> str: return self.add_block("operator_mathop", inputs={"NUM": self._num_input(value)}, fields={"OPERATOR": [op, None]})
    def wait(self, seconds: float) -> str: return self.add_block("control_wait", inputs={"DURATION": self.lit_decimal(seconds)})

    def if_block(self, condition: str, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block("control_if", inputs={"CONDITION": self.ref_bool(condition), **({"SUBSTACK": self.ref_stmt(first)} if first else {})})
        self._fix_substack_parents(blk, first)
        return blk

    def repeat_until(self, condition: str, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block("control_repeat_until", inputs={"CONDITION": self.ref_bool(condition), **({"SUBSTACK": self.ref_stmt(first)} if first else {})})
        self._fix_substack_parents(blk, first)
        return blk

    def if_else_block(self, condition: str, substack: tuple[str, ...], substack2: tuple[str, ...]) -> str:
        first_then = self.chain("TEMP", substack)
        first_else = self.chain("TEMP", substack2)
        inputs: dict = {"CONDITION": self.ref_bool(condition)}
        if first_then:
            inputs["SUBSTACK"] = self.ref_stmt(first_then)
        if first_else:
            inputs["SUBSTACK2"] = self.ref_stmt(first_else)
        blk = self.add_block("control_if_else", inputs=inputs)
        self._fix_substack_parents(blk, first_then)
        self._fix_substack_parents(blk, first_else)
        return blk

    def forever(self, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block("control_forever", inputs={**({"SUBSTACK": self.ref_stmt(first)} if first else {})})
        self._fix_substack_parents(blk, first)
        return blk

    def repeat(self, times: Any, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block("control_repeat", inputs={"TIMES": self._num_input(times), **({"SUBSTACK": self.ref_stmt(first)} if first else {})})
        self._fix_substack_parents(blk, first)
        return blk

    def _fix_substack_parents(self, owner: str, first: str | None) -> None:
        cur, prev = first, None
        while cur:
            self.blocks[cur]["parent"] = owner if prev is None else prev
            prev, cur = cur, self.blocks[cur]["next"]


    def arg(self, name: str) -> str:
        return self.add_block("argument_reporter_string_number", fields={"VALUE": [name, None]})
    def movement_pair_menu(self, pair: str = "AB") -> str:
        return self.add_block("flippermove_movement-port-selector", shadow=True, fields={"field_flippermove_movement-port-selector": [pair, None]})
    def single_motor_menu(self, port: str = "A") -> str:
        return self.add_block("flippermoremotor_single-motor-selector", shadow=True, fields={"field_flippermoremotor_single-motor-selector": [port, None]})
    def multiple_motor_menu(self, port: str = "A") -> str:
        return self.add_block("flippermoremotor_multiple-port-selector", shadow=True, fields={"field_flippermoremotor_multiple-port-selector": [port, None]})
    def set_movement_pair(self, pair: str = "AB") -> str:
        m = self.movement_pair_menu(pair)
        return self.add_block("flippermove_setMovementPair", inputs={"PAIR": self.ref_menu(m)})
    def reset_yaw(self) -> str: return self.add_block("flippersensors_resetYaw")
    def yaw(self) -> str: return self.add_block("flippersensors_orientationAxis", fields={"AXIS": ["yaw", None]})
    def motor_relative_position(self, port: str) -> str:
        m = self.single_motor_menu(port)
        return self.add_block("flippermoremotor_position", inputs={"PORT": self.ref_menu(m)})
    def motor_set_relative_position(self, port: str, value: int | float) -> str:
        m = self.multiple_motor_menu(port)
        return self.add_block("flippermoremotor_motorSetDegreeCounted", inputs={"PORT": self.ref_menu(m), "VALUE": self.lit_number(value)})
    def start_dual_speed(self, left: Any, right: Any) -> str: return self.add_block("flippermoremove_startDualSpeed", inputs={"LEFT": self._num_input(left), "RIGHT": self._num_input(right)})
    def start_dual_power(self, left: Any, right: Any) -> str: return self.add_block("flippermoremove_startDualPower", inputs={"LEFT": self._num_input(left), "RIGHT": self._num_input(right)})
    def stop_moving(self) -> str: return self.add_block("flippermove_stopMove")

    def define_procedure(self, name: str, args: list[str], *, x: int, y: int, defaults: list[Any] | None = None) -> str:
        defid = self._id("def")
        argids = [self._id("arg") for _ in args]
        protoid = self._id("proto")
        proto_inputs = OrderedDict()
        for aid, aname in zip(argids, args):
            rep = self.add_block("argument_reporter_string_number", parent=protoid, fields={"VALUE": [aname, None]}, shadow=True)
            proto_inputs[aid] = self.ref_menu(rep)
        # Build the argumentdefaults list: one string entry per param.
        # Entries for params without a default are empty strings (Scratch convention).
        actual_defaults: list[Any] = list(defaults) if defaults is not None else []
        # Pad / trim to match the number of args.
        actual_defaults = (actual_defaults + [""] * len(args))[:len(args)]
        def _default_str(d: Any) -> str:
            if d is None or d == "":
                return ""
            return str(d)
        mut = {
            "tagName": "mutation",
            "children": [],
            "proccode": name + ("" if not args else " " + " ".join(["%s"] * len(args))),
            "argumentids": json.dumps(argids),
            "argumentnames": json.dumps(args),
            "argumentdefaults": json.dumps([_default_str(d) for d in actual_defaults]),
            "warp": "false",
        }
        self.blocks[protoid] = OrderedDict([
            ("opcode", "procedures_prototype"), ("next", None), ("parent", defid), ("inputs", proto_inputs), ("fields", OrderedDict()), ("shadow", True), ("topLevel", False), ("mutation", mut),
        ])
        self.blocks[defid] = OrderedDict([
            ("opcode", "procedures_definition"), ("next", None), ("parent", None), ("inputs", OrderedDict({"custom_block": self.ref_menu(protoid)})), ("fields", OrderedDict()), ("shadow", False), ("topLevel", True), ("x", x), ("y", y),
        ])
        self._proc_meta[name] = {"proccode": mut["proccode"], "argids": argids, "defaults": actual_defaults}
        return defid

    def call_procedure(self, name: str, args: list[Any] | tuple[Any, ...] = ()) -> str:
        meta = self._proc_meta[name]
        argids = meta["argids"]
        stored_defaults = meta.get("defaults", [""] * len(argids))
        ins = OrderedDict()
        for i, aid in enumerate(argids):
            if i < len(args):
                ins[aid] = self._text_input(args[i])
            elif i < len(stored_defaults) and stored_defaults[i] not in ("", None):
                # Fill missing positional arg with its stored default value.
                ins[aid] = self._text_input(stored_defaults[i])
            # else: no input (Scratch uses the mutation's argumentdefaults entry at runtime)
        return self.add_block("procedures_call", inputs=ins, mutation={"tagName": "mutation", "children": [], "proccode": meta["proccode"], "argumentids": json.dumps(meta["argids"]), "warp": "false"})

    def attach_procedure_body(self, name: str, *block_ids: str) -> str | None:
        target_code = self._proc_meta[name]["proccode"]
        defid = None
        for bid, block in self.blocks.items():
            if block.get("opcode") == "procedures_definition":
                protoid = block["inputs"]["custom_block"][1]
                if self.blocks[protoid].get("mutation", {}).get("proccode") == target_code:
                    defid = bid
                    break
        if defid is None:
            raise KeyError(name)
        first = self.chain(defid, block_ids)
        self.blocks[defid]["next"] = first
        return first

    def validate(self) -> list[str]:
        errs = []
        for bid, block in self.blocks.items():
            if block.get("next") is not None and block["next"] not in self.blocks:
                errs.append(f"{bid}: missing next {block['next']}")
            if block.get("parent") is not None and block["parent"] not in self.blocks:
                errs.append(f"{bid}: missing parent {block['parent']}")
            for name, spec in block.get("inputs", {}).items():
                if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], str) and spec[1] in self.blocks:
                    child = self.blocks[spec[1]]
                    if child.get("parent") != bid:
                        errs.append(f"{bid}.{name}: child {spec[1]} has parent {child.get('parent')} instead of {bid}")
            opcode = block.get("opcode")
            if opcode in {"operator_or", "operator_and"}:
                for key in ("OPERAND1", "OPERAND2"):
                    spec = block.get("inputs", {}).get(key)
                    if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], str) and spec[1] in self.blocks:
                        child_opcode = self.blocks[spec[1]].get("opcode")
                        if not self.is_boolean_opcode(child_opcode):
                            errs.append(f"{bid}.{key}: boolean slot connected to non-boolean opcode {child_opcode}")
            if opcode == "operator_equals":
                for key in ("OPERAND1", "OPERAND2"):
                    spec = block.get("inputs", {}).get(key)
                    if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], str) and spec[1] in self.blocks:
                        child_opcode = self.blocks[spec[1]].get("opcode")
                        if self.is_boolean_opcode(child_opcode):
                            errs.append(f"{bid}.{key}: equals connected to boolean opcode {child_opcode}")
            if opcode in {"control_if", "control_repeat_until"}:
                spec = block.get("inputs", {}).get("CONDITION")
                if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], str) and spec[1] in self.blocks:
                    child_opcode = self.blocks[spec[1]].get("opcode")
                    if not self.is_boolean_opcode(child_opcode):
                        errs.append(f"{bid}.CONDITION: control condition connected to non-boolean opcode {child_opcode}")
        return errs

    def save(self, out_path: str | Path) -> Path:
        errs = self.validate()
        if errs:
            raise ValueError("Validation failed:\n" + "\n".join(errs[:50]))
        self._normalize_asset_hashes()
        self.project_json["extensions"] = sorted({
            b["opcode"].split("_", 1)[0]
            for b in self.blocks.values()
            if "_" in b["opcode"] and b["opcode"].split("_", 1)[0] not in self.BUILTIN_EXTENSION_PREFIXES
        })
        (self.inner_dir / "project.json").write_text(json.dumps(self.project_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        scratch_sb3 = self.outer_dir / "scratch.sb3"
        with zipfile.ZipFile(scratch_sb3, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(self.inner_dir.iterdir(), key=lambda p: p.name):
                zf.write(item, arcname=item.name)
        out_path = Path(out_path)
        self.manifest["name"] = out_path.stem
        self.manifest["size"] = scratch_sb3.stat().st_size
        (self.outer_dir / "manifest.json").write_text(json.dumps(self.manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in ["manifest.json", "icon.svg", "scratch.sb3"]:
                zf.write(self.outer_dir / name, arcname=name)
        return out_path
