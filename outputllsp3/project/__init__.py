"""LLSP3 project coordinator.

``LLSP3Project`` is the central object of the package.  It composes four
focused managers and delegates all operations to them:

- :class:`~outputllsp3.project.blocks.BlockManager` – block creation, chains,
  operators, control flow, and hardware helpers.
- :class:`~outputllsp3.project.variables.VariableManager` – variables, lists,
  and namespace qualification.
- :class:`~outputllsp3.project.procedures.ProcedureManager` – custom
  procedures (define / call / attach body).
- :class:`~outputllsp3.project.serializer.ProjectSerializer` – template
  unpacking, asset-hash normalisation, validation, and ZIP I/O.

Typical usage::

    project = LLSP3Project('ok.llsp3', 'strings.json')
    api = API(project)
    api.flow.start(api.move.forward_cm(20))
    project.save('out.llsp3')

Public API
----------
``LLSP3Project``, ``BlockManager``, ``VariableManager``,
``ProcedureManager``, ``ProjectSerializer``
"""
from __future__ import annotations

import tempfile
import uuid
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

from ..catalog import BlockCatalog
from .blocks import BlockManager
from .variables import VariableManager
from .procedures import ProcedureManager
from .serializer import ProjectSerializer
from .layout import LayoutManager
from ..locale import t

logger = logging.getLogger(__name__)

__all__ = [
    "LLSP3Project",
    "BlockManager",
    "VariableManager",
    "ProcedureManager",
    "ProjectSerializer",
    "LayoutManager",
]


class LLSP3Project:
    """Thin coordinator that owns the project state and delegates to managers."""

    def __init__(
        self,
        template_llsp3: str | Path,
        strings_json: str | Path,
        *,
        sprite_name: str = "OutputLLSP3 Generated",
    ) -> None:
        self.catalog = BlockCatalog(strings_json)
        self.template_llsp3 = Path(template_llsp3)
        self.tmpdir = Path(tempfile.mkdtemp(prefix="outputllsp3_"))
        self.outer_dir = self.tmpdir / "outer"
        self.inner_dir = self.tmpdir / "inner"
        self.outer_dir.mkdir(parents=True, exist_ok=True)
        self.inner_dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self._proc_meta: dict[str, dict[str, Any]] = {}
        self._monitors: dict[str, dict[str, Any]] = {}  # var_id → monitor config
        self.default_namespace: str = ""
        self.function_namespace_mode: bool = False
        self.strict_verified: bool = False

        self._blocks = BlockManager(self)
        self._vars = VariableManager(self)
        self._procs = ProcedureManager(self)
        self._serializer = ProjectSerializer(self)

        self._serializer.unpack(self.template_llsp3)
        self.project_json["targets"][self.sprite_index]["name"] = sprite_name
        logger.debug(t("project.init", template=str(template_llsp3)))
        self.clear_code()

    # -- ID generation ----------------------------------------------------

    def _id(self, prefix: str = "b") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}_{uuid.uuid4().hex[:6]}"

    # -- data properties --------------------------------------------------

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

    # -- state management -------------------------------------------------

    def clear_code(self) -> None:
        logger.debug(t("project.clear"))
        self.sprite["blocks"] = OrderedDict()
        self.sprite["variables"] = OrderedDict()
        self.sprite["lists"] = OrderedDict()
        self.sprite["broadcasts"] = OrderedDict()
        self.sprite["comments"] = OrderedDict()
        self.project_json["monitors"] = []
        self._monitors.clear()
        self._proc_meta.clear()

    def set_strict_verified(self, enabled: bool = True) -> None:
        self.strict_verified = enabled

    # -- class-level constants (backward compat) --------------------------

    BOOLEAN_OPCODES = BlockManager.BOOLEAN_OPCODES
    BUILTIN_EXTENSION_PREFIXES = BlockManager.BUILTIN_EXTENSION_PREFIXES

    # == BlockManager delegation ==========================================

    def add_block(
        self, opcode: str, *, inputs: dict[str, Any] | None = None,
        fields: dict[str, Any] | None = None, parent: str | None = None,
        next: str | None = None, shadow: bool = False, top_level: bool = False,
        x: int = 0, y: int = 0, mutation: dict[str, Any] | None = None,
    ) -> str:
        return self._blocks.add_block(
            opcode, inputs=inputs, fields=fields, parent=parent, next=next,
            shadow=shadow, top_level=top_level, x=x, y=y, mutation=mutation,
        )

    def add_comment(
        self, block_id: str, text: str, *, x: int | None = None, y: int | None = None,
        width: int = 260, height: int = 120, minimized: bool = False,
    ) -> str:
        return self._blocks.add_comment(
            block_id, text, x=x, y=y, width=width, height=height, minimized=minimized,
        )

    def chain(self, container: str, block_ids: Iterable[str]) -> str | None:
        return self._blocks.chain(container, block_ids)

    def chain_inline(self, *block_ids: str) -> str | None:
        return self._blocks.chain_inline(*block_ids)

    # literal helpers
    def lit_number(self, value: int | float | str): return self._blocks.lit_number(value)
    def lit_decimal(self, value: int | float | str): return self._blocks.lit_decimal(value)
    def lit_text(self, value: Any): return self._blocks.lit_text(value)

    # reference helpers
    def ref_number(self, block_id: str, fallback: int | float | str = 0): return self._blocks.ref_number(block_id, fallback)
    def ref_text(self, block_id: str, fallback: Any = 0): return self._blocks.ref_text(block_id, fallback)
    def ref_bool(self, block_id: str): return self._blocks.ref_bool(block_id)
    def ref_stmt(self, block_id: str): return self._blocks.ref_stmt(block_id)
    def ref_menu(self, block_id: str): return self._blocks.ref_menu(block_id)

    # input coercion (used internally by other modules)
    def _num_input(self, value: Any): return self._blocks._num_input(value)
    def _text_input(self, value: Any): return self._blocks._text_input(value)
    def _bool_input(self, value: Any): return self._blocks._bool_input(value)

    # opcode helpers
    def _block_opcode(self, block_id: Any) -> str | None: return self._blocks._block_opcode(block_id)
    def is_boolean_opcode(self, opcode: str | None) -> bool: return self._blocks.is_boolean_opcode(opcode)

    # arithmetic / logical blocks
    def add(self, a: Any, b: Any) -> str: return self._blocks.add(a, b)
    def sub(self, a: Any, b: Any) -> str: return self._blocks.sub(a, b)
    def mul(self, a: Any, b: Any) -> str: return self._blocks.mul(a, b)
    def div(self, a: Any, b: Any) -> str: return self._blocks.div(a, b)
    def lt(self, a: Any, b: Any) -> str: return self._blocks.lt(a, b)
    def gt(self, a: Any, b: Any) -> str: return self._blocks.gt(a, b)
    def eq(self, a: Any, b: Any) -> str: return self._blocks.eq(a, b)
    def or_(self, a: Any, b: Any) -> str: return self._blocks.or_(a, b)
    def and_(self, a: Any, b: Any) -> str: return self._blocks.and_(a, b)
    def not_(self, value: Any) -> str: return self._blocks.not_(value)
    def mod(self, a: Any, b: Any) -> str: return self._blocks.mod(a, b)
    def round_(self, value: Any) -> str: return self._blocks.round_(value)
    def join(self, a: Any, b: Any) -> str: return self._blocks.join(a, b)
    def length_of(self, value: Any) -> str: return self._blocks.length_of(value)
    def letter_of(self, index: Any, value: Any) -> str: return self._blocks.letter_of(index, value)
    def str_contains(self, string: Any, substring: Any) -> str: return self._blocks.str_contains(string, substring)
    def random(self, from_: Any, to: Any) -> str: return self._blocks.random(from_, to)
    def mathop(self, op: str, value: Any) -> str: return self._blocks.mathop(op, value)

    # timing / stop blocks
    def wait(self, seconds: float) -> str: return self._blocks.wait(seconds)
    def wait_until(self, condition: Any) -> str: return self._blocks.wait_until(condition)
    def stop_all(self) -> str: return self._blocks.stop_all()
    def stop_other_stacks(self) -> str: return self._blocks.stop_other_stacks()
    def broadcast(self, message: str) -> str: return self._blocks.broadcast(message)
    def broadcast_and_wait(self, message: str) -> str: return self._blocks.broadcast_and_wait(message)

    # control flow blocks
    def if_block(self, condition: str, *substack: str) -> str: return self._blocks.if_block(condition, *substack)
    def repeat_until(self, condition: str, *substack: str) -> str: return self._blocks.repeat_until(condition, *substack)
    def if_else_block(self, condition: str, substack: tuple, substack2: tuple) -> str: return self._blocks.if_else_block(condition, substack, substack2)
    def forever(self, *substack: str) -> str: return self._blocks.forever(*substack)
    def repeat(self, times: Any, *substack: str) -> str: return self._blocks.repeat(times, *substack)

    # argument / hardware helpers
    def arg(self, name: str) -> str: return self._blocks.arg(name)
    def movement_pair_menu(self, pair: str = "AB") -> str: return self._blocks.movement_pair_menu(pair)
    def single_motor_menu(self, port: str = "A") -> str: return self._blocks.single_motor_menu(port)
    def multiple_motor_menu(self, port: str = "A") -> str: return self._blocks.multiple_motor_menu(port)
    def set_movement_pair(self, pair: str = "AB") -> str: return self._blocks.set_movement_pair(pair)
    def reset_yaw(self) -> str: return self._blocks.reset_yaw()
    def yaw(self) -> str: return self._blocks.yaw()
    def motor_relative_position(self, port: str) -> str: return self._blocks.motor_relative_position(port)
    def motor_set_relative_position(self, port: str, value: int | float) -> str: return self._blocks.motor_set_relative_position(port, value)
    def start_dual_speed(self, left: Any, right: Any) -> str: return self._blocks.start_dual_speed(left, right)
    def start_dual_power(self, left: Any, right: Any) -> str: return self._blocks.start_dual_power(left, right)
    def stop_moving(self) -> str: return self._blocks.stop_moving()
    def motor_set_stop_method(self, port: str, mode: str = "brake") -> str: return self._blocks.motor_set_stop_method(port, mode)
    def motor_set_acceleration(self, port: str, accel: Any) -> str: return self._blocks.motor_set_acceleration(port, accel)
    def motor_set_speed(self, port: str, speed: Any) -> str: return self._blocks.motor_set_speed(port, speed)

    # == VariableManager delegation =======================================

    def sanitize_namespace(self, value: str) -> str: return self._vars.sanitize_namespace(value)
    def set_default_namespace(self, namespace: str | None, *, function_namespace: bool = False) -> None: return self._vars.set_default_namespace(namespace, function_namespace=function_namespace)
    def qualify_var_name(self, name: str, namespace: str | None = None, raw: bool = False) -> str: return self._vars.qualify_var_name(name, namespace=namespace, raw=raw)
    def add_variable(self, name: str, value: Any = 0, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.add_variable(name, value, namespace=namespace, raw=raw)
    def variable_id(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.variable_id(name, namespace=namespace, raw=raw)
    def variable(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.variable(name, namespace=namespace, raw=raw)
    def set_variable(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.set_variable(name, value, namespace=namespace, raw=raw)
    def change_variable(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.change_variable(name, value, namespace=namespace, raw=raw)
    def show_monitor(self, name: str, *, visible: bool = True, slider_min: Any = None, slider_max: Any = None, discrete: bool = True, namespace: str | None = None, raw: bool = False) -> None: return self._vars.show_monitor(name, visible=visible, slider_min=slider_min, slider_max=slider_max, discrete=discrete, namespace=namespace, raw=raw)
    def add_list(self, name: str, value: list[Any] | None = None, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.add_list(name, value, namespace=namespace, raw=raw)
    def list_id(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_id(name, namespace=namespace, raw=raw)
    def list_name(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_name(name, namespace=namespace, raw=raw)
    def list_contents(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_contents(name, namespace=namespace, raw=raw)
    def list_length(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_length(name, namespace=namespace, raw=raw)
    def list_item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_item(name, index, namespace=namespace, raw=raw)
    def list_contains(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_contains(name, item, namespace=namespace, raw=raw)
    def list_replace(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_replace(name, index, item, namespace=namespace, raw=raw)
    def list_delete(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_delete(name, index, namespace=namespace, raw=raw)
    def list_insert(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_insert(name, index, item, namespace=namespace, raw=raw)
    def list_append(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_append(name, item, namespace=namespace, raw=raw)
    def list_clear(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self._vars.list_clear(name, namespace=namespace, raw=raw)

    # == ProcedureManager delegation ======================================

    def define_procedure(self, name: str, args: list[str], *, x: int, y: int, defaults: list[Any] | None = None) -> str:
        return self._procs.define_procedure(name, args, x=x, y=y, defaults=defaults)

    def call_procedure(self, name: str, args: list[Any] | tuple[Any, ...] = ()) -> str:
        return self._procs.call_procedure(name, args)

    def attach_procedure_body(self, name: str, *block_ids: str) -> str | None:
        return self._procs.attach_procedure_body(name, *block_ids)

    # == ProjectSerializer delegation =====================================

    def validate(self) -> list[str]:
        return self._serializer.validate()

    def save(self, out_path: str | Path) -> Path:
        logger.debug(t("project.save", out=str(out_path)))
        return self._serializer.save(out_path)

    def cleanup(self) -> None:
        self._serializer.cleanup()
