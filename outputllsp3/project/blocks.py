"""Block creation and manipulation.

``BlockManager`` handles all block-building operations:
literal/reference helpers, input coercion, ``add_block``, chain helpers,
control-flow blocks, arithmetic/logical operators, and hardware helpers.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from . import LLSP3Project


class BlockManager:
    BOOLEAN_OPCODES = {
        # Core Scratch operators
        "operator_lt", "operator_gt", "operator_equals",
        "operator_or", "operator_and", "operator_not",
        "data_listcontainsitem",
        # SPIKE Prime / LLSP3 sensor boolean reporters
        "flippersensors_isColor",
        "flippersensors_isDistance",
        "flippersensors_isPressed",
        "flippersensors_isReflectivity",
        "flippersensors_buttonIsPressed",
        "flippersensors_isTilted",
        "flippersensors_ismotion",
        "flippersensors_isorientation",
        "flipperoperator_isInBetween",
        # EV3 sensor booleans
        "ev3sensors_isEV3TouchSensorPressed",
        "ev3sensors_isEV3BrickButtonPressed",
        "ev3sensors_isEV3InfraredBeaconActive",
        "ev3sensors_isEV3InfraredBeaconButtonPressed",
    }
    BUILTIN_EXTENSION_PREFIXES = {"argument", "control", "data", "operator", "procedures"}

    def __init__(self, project: "LLSP3Project") -> None:
        self._p = project

    # -- literal helpers --------------------------------------------------

    def lit_number(self, value: int | float | str):
        return [1, [4, str(value)]]

    def lit_decimal(self, value: int | float | str):
        return [1, [5, str(value)]]

    def lit_text(self, value: Any):
        return [1, [10, str(value)]]

    # -- reference helpers ------------------------------------------------

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

    # -- input coercion ---------------------------------------------------

    def _num_input(self, value: Any):
        if isinstance(value, str) and value in self._p.blocks:
            return self.ref_number(value)
        if isinstance(value, (int, float)):
            return self.lit_number(value)
        if isinstance(value, list):
            return value
        return self.lit_text(value)

    def _text_input(self, value: Any):
        if isinstance(value, str) and value in self._p.blocks:
            return self.ref_text(value)
        if isinstance(value, list):
            return value
        return self.lit_text(value)

    def _bool_input(self, value: Any):
        if isinstance(value, str) and value in self._p.blocks:
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

    # -- opcode inspection ------------------------------------------------

    def _block_opcode(self, block_id: Any) -> str | None:
        if isinstance(block_id, str) and block_id in self._p.blocks:
            return self._p.blocks[block_id].get("opcode")
        return None

    def is_boolean_opcode(self, opcode: str | None) -> bool:
        return opcode in self.BOOLEAN_OPCODES if opcode else False

    def _child_block_ids(self, inputs: dict[str, Any] | None) -> list[str]:
        out = []
        for spec in (inputs or {}).values():
            if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], str) and spec[1] in self._p.blocks:
                out.append(spec[1])
        return out

    # -- core block creation ----------------------------------------------

    def add_block(
        self, opcode: str, *, inputs: dict[str, Any] | None = None,
        fields: dict[str, Any] | None = None, parent: str | None = None,
        next: str | None = None, shadow: bool = False, top_level: bool = False,
        x: int = 0, y: int = 0, mutation: dict[str, Any] | None = None,
    ) -> str:
        if opcode not in self._p.catalog:
            raise KeyError(f"Unknown opcode: {opcode}")
        bid = self._p._id()
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
        self._p.blocks[bid] = block
        for child in self._child_block_ids(block["inputs"]):
            if self._p.blocks[child].get("parent") in (None, "INLINE", "TEMP"):
                self._p.blocks[child]["parent"] = bid
        return bid

    def add_comment(
        self, block_id: str, text: str, *, x: int | None = None, y: int | None = None,
        width: int = 260, height: int = 120, minimized: bool = False,
    ) -> str:
        cid = self._p._id("c")
        self._p.comments[cid] = OrderedDict([
            ("blockId", block_id),
            ("x", 0 if x is None else x),
            ("y", 0 if y is None else y),
            ("width", width),
            ("height", height),
            ("minimized", minimized),
            ("text", text),
        ])
        return cid

    def chain(self, container: str, block_ids: Iterable[str]) -> str | None:
        ids = [bid for bid in block_ids if bid]
        for i, bid in enumerate(ids):
            if not isinstance(bid, str):
                raise TypeError(
                    f"chain(): expected a block-ID string at position {i}, "
                    f"got {type(bid).__name__} {bid!r}. "
                    f"Call a block-building method (e.g. v.set(), move.stop()) "
                    f"to produce a block ID instead of passing a raw literal."
                )
            if bid not in self._p.blocks:
                if len(bid) == 1:
                    raise KeyError(
                        f"chain(): single-character key {bid!r} suggests a string was "
                        f"star-unpacked (e.g. `*method()` where method() returns one string). "
                        f"Remove the `*` and pass the block ID directly."
                    )
                raise KeyError(
                    f"chain(): block ID {bid!r} not found in project blocks. "
                    f"Ensure the block was created before being added to a sequence."
                )
            self._p.blocks[bid]["parent"] = container if i == 0 else ids[i - 1]
            self._p.blocks[bid]["next"] = ids[i + 1] if i + 1 < len(ids) else None
        return ids[0] if ids else None

    def chain_inline(self, *block_ids: str) -> str | None:
        return self.chain("INLINE", block_ids)

    # -- control flow blocks ----------------------------------------------

    def if_block(self, condition: str, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block(
            "control_if",
            inputs={"CONDITION": self.ref_bool(condition),
                    **({"SUBSTACK": self.ref_stmt(first)} if first else {})},
        )
        self._fix_substack_parents(blk, first)
        return blk

    def repeat_until(self, condition: str, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block(
            "control_repeat_until",
            inputs={"CONDITION": self.ref_bool(condition),
                    **({"SUBSTACK": self.ref_stmt(first)} if first else {})},
        )
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
        blk = self.add_block(
            "control_forever",
            inputs={**({"SUBSTACK": self.ref_stmt(first)} if first else {})},
        )
        self._fix_substack_parents(blk, first)
        return blk

    def repeat(self, times: Any, *substack: str) -> str:
        first = self.chain("TEMP", substack)
        blk = self.add_block(
            "control_repeat",
            inputs={"TIMES": self._num_input(times),
                    **({"SUBSTACK": self.ref_stmt(first)} if first else {})},
        )
        self._fix_substack_parents(blk, first)
        return blk

    def _fix_substack_parents(self, owner: str, first: str | None) -> None:
        cur, prev = first, None
        while cur:
            self._p.blocks[cur]["parent"] = owner if prev is None else prev
            prev, cur = cur, self._p.blocks[cur]["next"]

    # -- arithmetic / logical blocks --------------------------------------

    def add(self, a: Any, b: Any) -> str:
        return self.add_block("operator_add", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})

    def sub(self, a: Any, b: Any) -> str:
        return self.add_block("operator_subtract", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})

    def mul(self, a: Any, b: Any) -> str:
        return self.add_block("operator_multiply", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})

    def div(self, a: Any, b: Any) -> str:
        return self.add_block("operator_divide", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})

    def lt(self, a: Any, b: Any) -> str:
        return self.add_block("operator_lt", inputs={"OPERAND1": self._num_input(a), "OPERAND2": self._num_input(b)})

    def gt(self, a: Any, b: Any) -> str:
        return self.add_block("operator_gt", inputs={"OPERAND1": self._num_input(a), "OPERAND2": self._num_input(b)})

    def eq(self, a: Any, b: Any) -> str:
        return self.add_block("operator_equals", inputs={"OPERAND1": self._num_input(a), "OPERAND2": self._num_input(b)})

    def or_(self, a: Any, b: Any) -> str:
        return self.add_block("operator_or", inputs={"OPERAND1": self._bool_input(a), "OPERAND2": self._bool_input(b)})

    def and_(self, a: Any, b: Any) -> str:
        return self.add_block("operator_and", inputs={"OPERAND1": self._bool_input(a), "OPERAND2": self._bool_input(b)})

    def not_(self, value: Any) -> str:
        return self.add_block("operator_not", inputs={"OPERAND": self._bool_input(value)})

    def mod(self, a: Any, b: Any) -> str:
        return self.add_block("operator_mod", inputs={"NUM1": self._num_input(a), "NUM2": self._num_input(b)})

    def round_(self, value: Any) -> str:
        return self.add_block("operator_round", inputs={"NUM": self._num_input(value)})

    def join(self, a: Any, b: Any) -> str:
        return self.add_block("operator_join", inputs={"STRING1": self._text_input(a), "STRING2": self._text_input(b)})

    def length_of(self, value: Any) -> str:
        return self.add_block("operator_length", inputs={"STRING": self._text_input(value)})

    def letter_of(self, index: Any, value: Any) -> str:
        return self.add_block("operator_letter_of", inputs={"LETTER": self._num_input(index), "STRING": self._text_input(value)})

    def str_contains(self, string: Any, substring: Any) -> str:
        return self.add_block("operator_contains", inputs={"STRING1": self._text_input(string), "STRING2": self._text_input(substring)})

    def random(self, from_: Any, to: Any) -> str:
        return self.add_block("operator_random", inputs={"FROM": self._num_input(from_), "TO": self._num_input(to)})

    def mathop(self, op: str, value: Any) -> str:
        return self.add_block("operator_mathop", inputs={"NUM": self._num_input(value)}, fields={"OPERATOR": [op, None]})

    # -- timing / stop blocks ---------------------------------------------

    def wait(self, seconds: Any) -> str:
        return self.add_block("control_wait", inputs={"DURATION": self._num_input(seconds)})

    def wait_until(self, condition: Any) -> str:
        return self.add_block("control_wait_until", inputs={"CONDITION": self.ref_bool(condition)})

    def stop_all(self) -> str:
        return self.add_block(
            "flippercontrol_stop",
            fields={"STOP_OPTION": ["all", None]},
            mutation={"tagName": "mutation", "children": [], "hasnext": "false"},
        )

    # -- argument / hardware helpers --------------------------------------

    def arg(self, name: str) -> str:
        return self.add_block("argument_reporter_string_number", fields={"VALUE": [name, None]})

    def movement_pair_menu(self, pair: str = "AB") -> str:
        return self.add_block(
            "flippermove_movement-port-selector", shadow=True,
            fields={"field_flippermove_movement-port-selector": [pair, None]},
        )

    def single_motor_menu(self, port: str = "A") -> str:
        return self.add_block(
            "flippermoremotor_single-motor-selector", shadow=True,
            fields={"field_flippermoremotor_single-motor-selector": [port, None]},
        )

    def multiple_motor_menu(self, port: str = "A") -> str:
        return self.add_block(
            "flippermoremotor_multiple-port-selector", shadow=True,
            fields={"field_flippermoremotor_multiple-port-selector": [port, None]},
        )

    def set_movement_pair(self, pair: str = "AB") -> str:
        m = self.movement_pair_menu(pair)
        return self.add_block("flippermove_setMovementPair", inputs={"PAIR": self.ref_menu(m)})

    def reset_yaw(self) -> str:
        return self.add_block("flippersensors_resetYaw")

    def yaw(self) -> str:
        return self.add_block("flippersensors_orientationAxis", fields={"AXIS": ["yaw", None]})

    def motor_relative_position(self, port: str) -> str:
        m = self.single_motor_menu(port)
        return self.add_block("flippermoremotor_position", inputs={"PORT": self.ref_menu(m)})

    def motor_set_relative_position(self, port: str, value: int | float) -> str:
        m = self.multiple_motor_menu(port)
        return self.add_block(
            "flippermoremotor_motorSetDegreeCounted",
            inputs={"PORT": self.ref_menu(m), "VALUE": self.lit_number(value)},
        )

    def start_dual_speed(self, left: Any, right: Any) -> str:
        return self.add_block(
            "flippermoremove_startDualSpeed",
            inputs={"LEFT": self._num_input(left), "RIGHT": self._num_input(right)},
        )

    def start_dual_power(self, left: Any, right: Any) -> str:
        return self.add_block(
            "flippermoremove_startDualPower",
            inputs={"LEFT": self._num_input(left), "RIGHT": self._num_input(right)},
        )

    def stop_moving(self) -> str:
        return self.add_block("flippermove_stopMove")
