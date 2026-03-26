"""AST-based Python-first compiler.

``PythonFirstContext`` walks a Python AST and emits LLSP3 blocks via the
high-level ``API`` facades.  Helper dataclasses ``LoopContext`` and
``ReturnContext`` track control-flow state during compilation.
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..api import API
from ..project import LLSP3Project
from ..locale import t
from ..enums import (
    Axis, Color, Comparator, Direction, LightImage,
    MotorPair, Port, StopMode,
)

# Flat lookup: "ClassName.MEMBER" → the string value the compiler should emit.
# Covers all StrEnum members so enum attribute expressions const-eval cleanly.
_ENUM_ATTRS: dict[str, Any] = {}
_ENUM_ATTRS.update({f"Axis.{m.name}": m.value for m in Axis})
_ENUM_ATTRS.update({f"OrientationAxis.{m.name}": m.value for m in Axis})
_ENUM_ATTRS.update({f"Color.{m.name}": m.value for m in Color})
_ENUM_ATTRS.update({f"ColorValue.{m.name}": m.value for m in Color})
_ENUM_ATTRS.update({f"Comparator.{m.name}": m.value for m in Comparator})
_ENUM_ATTRS.update({f"Direction.{m.name}": m.value for m in Direction})
_ENUM_ATTRS.update({f"LightImage.{m.name}": m.value for m in LightImage})
_ENUM_ATTRS.update({f"MotorPair.{m.name}": m.value for m in MotorPair})
_ENUM_ATTRS.update({f"Port.{m.name}": m.value for m in Port})
_ENUM_ATTRS.update({f"StopMode.{m.name}": m.value for m in StopMode})

# stdlib result attribute lookup: "stdlib.<name>" → (group_to_install, stdlib_property_name)
# Both the canonical _result-suffixed names and shorthand aliases are included so
# users can write either `stdlib.clamp_result` or simply `stdlib.clamp` to read back
# the result variable after a call.
_STDLIB_RESULT_ATTRS: dict[str, tuple[str, str]] = {
    # math group
    "stdlib.clamp_result":    ("math", "clamp"),
    "stdlib.clamp":           ("math", "clamp"),
    "stdlib.map_result":      ("math", "map_result"),
    "stdlib.sign_result":     ("math", "sign"),
    "stdlib.sign":            ("math", "sign"),
    "stdlib.min_result":      ("math", "min_result"),
    "stdlib.max_result":      ("math", "max_result"),
    "stdlib.lerp_result":     ("math", "lerp"),
    "stdlib.lerp":            ("math", "lerp"),
    "stdlib.deadzone_result": ("math", "deadzone"),
    "stdlib.deadzone":        ("math", "deadzone"),
    "stdlib.smooth_result":   ("math", "smooth"),
    "stdlib.smooth":          ("math", "smooth"),
    # timing group
    "stdlib.wait_done":       ("timing", "wait_done"),
    # sensors group
    "stdlib.sensor_yaw":      ("sensors", "sensor_yaw"),
}

logger = logging.getLogger(__name__)


class UnsupportedNode(Exception):
    pass


class _ParamRef:
    def __init__(self, name: str):
        self.name = name


@dataclass
class LoopContext:
    kind: str
    fn_name: str
    break_var: str
    continue_var: str | None = None


@dataclass
class ReturnContext:
    """Tracks return-value machinery for a compiled procedure.

    Each ``@robot.proc`` that contains at least one ``return value`` statement
    gets a pair of raw (unnamespaced) Scratch variables:

    * ``flag_var``  – ``__return_<proc_name>``  – set to 1 when ``return`` is hit;
      guards all subsequent statements so they are skipped.
    * ``retval_var`` – ``__retval_<proc_name>`` – holds the returned value and
      can be read by the caller immediately after the procedure call.
    """
    fn_name: str
    flag_var: str
    retval_var: str


@dataclass
class PythonFirstContext:
    project: LLSP3Project
    source_path: Path

    def __post_init__(self):
        self.api = API(self.project)
        self.notes: list[str] = []
        self.const_env: dict[str, Any] = {}
        self.list_decls: dict[str, str] = {}
        self.proc_defs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        self.main_def: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        # Event-hat handlers collected from @run.when_* decorators.
        # Each entry: {'type': str, 'fn': FunctionDef, **kwargs}
        self._event_handlers: list[dict] = []
        # Functions decorated with @run.when_broadcast('msg') (kept for compat).
        self._broadcast_handlers: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
        # Pending monitor declarations collected from robot.show_monitor() calls.
        # Resolved after all compilation (when variables are fully declared).
        self._monitor_decls: list[dict] = []
        # Maps proc name → ReturnContext for procs that use ``return value``.
        self.proc_return_vars: dict[str, ReturnContext] = {}
        # Maps proc name → ordered list of param names.
        self.proc_params: dict[str, list[str]] = {}
        # Maps proc name → {param_name: default_value} for params that have defaults.
        self.proc_defaults: dict[str, dict[str, Any]] = {}
        self.runtime_config = {
            "motor_pair": "AB",
            "left_dir": 1,
            "right_dir": -1,
        }
        self.runtime_installed = False
        self._stdlib_groups_installed: set[str] = set()

    def note(self, msg: str, node: ast.AST | None = None) -> None:
        line = getattr(node, "lineno", "?") if node is not None else "?"
        self.notes.append(f"L{line}: {msg}")
        logger.debug(t("pf.note", msg=f"L{line}: {msg}"))

    # ---------- top-level analysis ----------

    @staticmethod
    def _fn_has_return_value(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Return True if *fn* contains at least one ``return <value>`` statement."""
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and node.value is not None:
                return True
        return False

    def _extract_fn_defaults(self, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
        """Return ``{param_name: const_value}`` for params that have default values.

        Defaults for all params are extracted from the AST.  Non-constant defaults
        (e.g. a function call) are const-evaluated; if evaluation fails the default
        is reported as a compile note and set to ``0`` so the build still succeeds.
        """
        args = fn.args.args
        defaults = fn.args.defaults  # last len(defaults) params
        n = len(args)
        m = len(defaults)
        result: dict[str, Any] = {}
        for i, default_node in enumerate(defaults):
            param_name = args[n - m + i].arg
            v = self.const_eval(default_node)
            if v is not None:
                result[param_name] = v
            else:
                self.note(
                    f'non-constant default for param {param_name!r} in {fn.name!r}; using 0',
                    default_node,
                )
                result[param_name] = 0
        return result

    def _fill_proc_args(self, proc_name: str, call: ast.Call, fn_name: str, params: set[str]) -> list[Any]:
        """Build the full ordered argument list for a call to *proc_name*.

        Handles three cases:
        * Positional args provided – used as-is.
        * Keyword args (``my_proc(speed=300)``) – matched to the declared parameter order.
        * Missing positional args – filled in from the proc's default values.

        If no parameter metadata is available (proc defined elsewhere / built-in) the
        raw positional arg list is returned unchanged.
        """
        param_list = self.proc_params.get(proc_name)
        if param_list is None:
            # No metadata: just compile the positional args
            return [self.compile_expr(a, fn_name, params) for a in call.args]

        defaults_map = self.proc_defaults.get(proc_name, {})
        filled: dict[int, Any] = {}

        # Positional args
        for i, arg in enumerate(call.args):
            filled[i] = self.compile_expr(arg, fn_name, params)

        # Keyword args – match by parameter name
        for kw in call.keywords:
            if kw.arg in param_list:
                idx = param_list.index(kw.arg)
                filled[idx] = self.compile_expr(kw.value, fn_name, params)
            elif kw.arg:
                self.note(f'unknown keyword arg {kw.arg!r} in call to {proc_name!r}; skipped', call)

        # Build the ordered result, filling defaults for any missing positions
        result: list[Any] = []
        for i, p in enumerate(param_list):
            if i in filled:
                result.append(filled[i])
            elif p in defaults_map:
                result.append(defaults_map[p])
            else:
                self.note(
                    f'missing required arg {p!r} in call to {proc_name!r} (no default); using 0', call
                )
                result.append(0)
        return result

    def analyze(self, tree: ast.Module) -> None:
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                tname = node.targets[0].id
                if self._is_ls_list_call(node.value):
                    lname = self._extract_list_name(node.value, tname)
                    self.list_decls[tname] = lname
                    continue
                value = self.const_eval(node.value)
                if value is not None:
                    self.const_env[tname] = value
                    continue
            # Collect robot.show_monitor() calls at module level for deferred registration.
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                fname = self.attr_name(node.value.func)
                if fname == 'robot.show_monitor' and node.value.args:
                    vname = self.const_eval(node.value.args[0])
                    if isinstance(vname, str):
                        kw = {kw.arg: self.const_eval(kw.value) for kw in node.value.keywords}
                        self._monitor_decls.append({
                            'name': vname,
                            'visible': kw.get('visible', True),
                            'slider_min': kw.get('slider_min', None),
                            'slider_max': kw.get('slider_max', None),
                            'discrete': kw.get('discrete', True),
                        })
                        continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                deco_names = [self.attr_name(d) for d in node.decorator_list]
                if "run.main" in deco_names:
                    self.main_def = node
                if "robot.proc" in deco_names:
                    self.proc_defs.append(node)
                # @run.when_*(...) — collect as event-hat handlers
                for deco in node.decorator_list:
                    deco_fn = self.attr_name(deco.func) if isinstance(deco, ast.Call) else self.attr_name(deco)
                    if not deco_fn.startswith('run.when_'):
                        continue
                    kind = deco_fn[len('run.when_'):]  # e.g. 'broadcast', 'condition', 'button'
                    args_ev = [self.const_eval(a) for a in (deco.args if isinstance(deco, ast.Call) else [])]
                    kw_ev = {kw.arg: self.const_eval(kw.value) for kw in (deco.keywords if isinstance(deco, ast.Call) else [])}
                    entry = {'type': kind, 'fn': node, 'args': args_ev, 'kw': kw_ev}
                    self._event_handlers.append(entry)
                    # Back-compat: keep _broadcast_handlers for 'broadcast' kind
                    if kind == 'broadcast' and args_ev and isinstance(args_ev[0], str):
                        self._broadcast_handlers.append((args_ev[0], node))

    def declare_resources(self):
        for pyname, lname in self.list_decls.items():
            self.api.lists.add(lname, [])
        # Create explicit variables only when a top-level constant is referenced later via vars lookup.
        # In python-first mode, constants are typically inlined.

    # ---------- compile ----------

    def transpile(self, tree: ast.Module):
        logger.debug(t("pf.parse", path=self.source_path, count=len(tree.body)))
        self.analyze(tree)
        self.declare_resources()

        # procedures first
        idx = 0
        for fn in self.proc_defs:
            params = [a.arg for a in fn.args.args]
            logger.debug(t("pf.proc", name=fn.name, arg_count=len(params)))
            # Collect default values for each parameter.
            defaults_map = self._extract_fn_defaults(fn)
            defaults_list = [defaults_map.get(p, "") for p in params]
            self.proc_params[fn.name] = params
            if defaults_map:
                self.proc_defaults[fn.name] = defaults_map
            return_ctx: ReturnContext | None = None
            init_blocks: list[str] = []
            if self._fn_has_return_value(fn):
                flag_var = f"__return_{fn.name}"
                retval_var = f"__retval_{fn.name}"
                self.api.vars.ensure(flag_var, 0, raw=True)
                self.api.vars.ensure(retval_var, 0, raw=True)
                return_ctx = ReturnContext(fn_name=fn.name, flag_var=flag_var, retval_var=retval_var)
                self.proc_return_vars[fn.name] = return_ctx
                # Reset flag at the start of each call so it doesn't carry over.
                init_blocks = [self.api.vars.set(flag_var, 0, raw=True)]
            body = self.compile_body(fn.body, fn_name=fn.name, params=set(params), return_ctx=return_ctx)
            self.api.flow.procedure(fn.name, params, *init_blocks, *body, defaults=defaults_list, x=700, y=160 + idx * 230)
            idx += 1

        if self.main_def is None:
            raise RuntimeError("No @run.main function found")

        logger.debug(t("pf.main", name=self.main_def.name))
        main_body = self.compile_body(self.main_def.body, fn_name=self.main_def.name, params=set())
        start = self.api.flow.start(x=-220, y=90)
        self.api.flow.chain(start, *main_body)
        if self.notes:
            self.project.add_comment(start, "python-first notes:\n" + "\n".join(self.notes[:12]), x=20, y=20, width=420, height=180)

        # Compile all @run.when_*(...) handlers as event-hat stacks.
        for i, ev in enumerate(self._event_handlers):
            kind = ev['type']
            fn = ev['fn']
            args = ev['args']
            kw = ev['kw']
            body = self.compile_body(fn.body, fn_name=fn.name, params=set())
            ev_kwargs: dict = dict(kw)
            try:
                if kind == 'broadcast':
                    msg = args[0] if args else kw.get('message', 'message1')
                    self.api.flow.when('broadcast', *body, message=msg)
                elif kind == 'condition':
                    # lambda: expr — we can't evaluate a lambda at compile time;
                    # compile the lambda body as a boolean expression block.
                    lambda_fn = fn  # will be handled via note
                    self.note(f"@run.when_condition: condition compiled as whenCondition block (lambda not supported at compile time)", fn)
                    # Best-effort: emit a whenCondition with no condition (always-fire)
                    self.api.flow.when('condition', *body, condition=None)
                elif kind == 'button':
                    button = args[0] if len(args) > 0 else kw.get('button', 'left')
                    action = args[1] if len(args) > 1 else kw.get('action', kw.get('event', 'pressed'))
                    self.api.flow.when('button', *body, button=button, action=action)
                elif kind == 'gesture':
                    gesture = args[0] if args else kw.get('gesture', 'tapped')
                    self.api.flow.when('gesture', *body, gesture=gesture)
                elif kind == 'orientation':
                    value = args[0] if args else kw.get('value', 'front')
                    self.api.flow.when('orientation', *body, value=value)
                elif kind == 'tilted':
                    direction = args[0] if args else kw.get('direction', 'any')
                    self.api.flow.when('tilted', *body, direction=direction)
                elif kind == 'timer':
                    threshold = args[0] if args else kw.get('threshold', 5.0)
                    self.api.flow.when('timer', *body, threshold=threshold)
                elif kind == 'color':
                    port = args[0] if len(args) > 0 else kw.get('port', 'A')
                    color = args[1] if len(args) > 1 else kw.get('color', 'any')
                    self.api.flow.when('color', *body, port=port, color=color)
                elif kind in ('pressed', 'force'):
                    port = args[0] if len(args) > 0 else kw.get('port', 'A')
                    option = args[1] if len(args) > 1 else kw.get('option', 'pressed')
                    self.api.flow.when('force', *body, port=port, option=option)
                elif kind in ('near_or_far', 'near', 'far'):
                    port = args[0] if len(args) > 0 else kw.get('port', 'A')
                    option = args[1] if len(args) > 1 else kw.get('option', 'near')
                    self.api.flow.when('near', *body, port=port)
                elif kind == 'distance':
                    port = args[0] if len(args) > 0 else kw.get('port', 'A')
                    comp = args[1] if len(args) > 1 else kw.get('comparator', 'less_than')
                    value = args[2] if len(args) > 2 else kw.get('value', 10)
                    self.api.flow.when('distance', *body, port=port, comparator=comp, value=value)
                elif kind in ('distance_closer_than',):
                    value = args[0] if args else kw.get('value', 10)
                    self.api.flow.when('near', *body, port='A')
                elif kind == 'louder_than':
                    # No direct SPIKE equivalent; emit a note and skip
                    self.note(f"@run.when_louder_than: not supported in SPIKE LLSP3 — skipped", fn)
                else:
                    self.note(f"@run.when_{kind}: unrecognised event type — skipped", fn)
            except Exception as exc:
                self.note(f"@run.when_{kind}: compile error ({exc}) — skipped", fn)

        # Apply deferred monitor declarations: now that all variables have been
        # declared (by data_setvariableto blocks), resolve them by name.
        for decl in self._monitor_decls:
            try:
                self.api.vars.show_monitor(
                    decl['name'],
                    visible=decl.get('visible', True),
                    slider_min=decl.get('slider_min'),
                    slider_max=decl.get('slider_max'),
                    discrete=decl.get('discrete', True),
                )
            except KeyError:
                pass  # variable never used in code — skip

    # ---------- constants ----------

    def const_eval(self, expr: ast.expr):
        if isinstance(expr, ast.Constant):
            return expr.value
        if isinstance(expr, ast.Name):
            return self.const_env.get(expr.id)
        if isinstance(expr, ast.Attribute):
            name = self.attr_name(expr)
            ports = {
                "port.A": "A", "port.B": "B", "port.C": "C", "port.D": "D", "port.E": "E", "port.F": "F",
            }
            if name in ports:
                return ports[name]
            if name in _ENUM_ATTRS:
                return _ENUM_ATTRS[name]
            return self.const_env.get(name)
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
            v = self.const_eval(expr.operand)
            return -v if isinstance(v, (int, float)) else None
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
            v = self.const_eval(expr.operand)
            return not v if v is not None else None
        if isinstance(expr, ast.BoolOp):
            # Evaluate constant-only BoolOp (e.g. ``True and False``) without
            # generating any blocks.  If any operand is non-constant, bail out.
            vals = [self.const_eval(v) for v in expr.values]
            if any(v is None for v in vals):
                return None
            if isinstance(expr.op, ast.And):
                result: Any = True
                for v in vals:
                    result = result and v
                return result
            if isinstance(expr.op, ast.Or):
                result = False
                for v in vals:
                    result = result or v
                return result
            return None
        if isinstance(expr, ast.BinOp):
            a = self.const_eval(expr.left)
            b = self.const_eval(expr.right)
            if a is None or b is None:
                return None
            if isinstance(expr.op, ast.Add): return a + b
            if isinstance(expr.op, ast.Sub): return a - b
            if isinstance(expr.op, ast.Mult): return a * b
            if isinstance(expr.op, ast.Div): return a / b
        return None

    # ---------- expressions ----------

    def _truthy(self, value: Any) -> str:
        if isinstance(value, str) and value in self.project.blocks and self.project.is_boolean_opcode(self.project.blocks[value].get("opcode")):
            return value
        if isinstance(value, bool):
            return self.api.ops.eq(1, 1 if value else 0)
        if isinstance(value, (int, float)):
            return self.api.ops.eq(1, 1 if value else 0)
        return self.api.ops.or_(self.api.ops.lt(value, 0), self.api.ops.gt(value, 0))

    def compile_expr(self, expr: ast.expr, fn_name: str, params: set[str]) -> Any:
        if isinstance(expr, ast.Constant):
            return expr.value
        if isinstance(expr, ast.Name):
            if expr.id in params:
                return self.project.arg(expr.id)
            if expr.id in self.list_decls:
                return self.api.lists.length(self.list_decls[expr.id])
            if expr.id in self.const_env:
                return self.const_env[expr.id]
            try:
                return self.api.vars.get(expr.id, namespace=fn_name)
            except Exception:
                try:
                    return self.api.vars.get(expr.id)
                except Exception:
                    return expr.id
        if isinstance(expr, ast.Attribute):
            name = self.attr_name(expr)
            ports = {
                "port.A": "A", "port.B": "B", "port.C": "C", "port.D": "D", "port.E": "E", "port.F": "F",
            }
            if name in ports:
                return ports[name]
            if name in _ENUM_ATTRS:
                return _ENUM_ATTRS[name]
            if name in self.const_env:
                return self.const_env[name]
            # stdlib result variable reporters (install group on first access)
            if name in _STDLIB_RESULT_ATTRS:
                group, prop = _STDLIB_RESULT_ATTRS[name]
                self.ensure_stdlib_group(group)
                return getattr(self.api.stdlib, prop)
            return name
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
            return self.api.ops.sub(0, self.compile_expr(expr.operand, fn_name, params))
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
            return self.api.ops.not_(self.compile_condition(expr.operand, fn_name, params))
        if isinstance(expr, ast.Call):
            fname = self.attr_name(expr.func)
            if fname == 'len' and expr.args and isinstance(expr.args[0], ast.Name) and expr.args[0].id in self.list_decls:
                return self.api.lists.length(self.list_decls[expr.args[0].id])
            if fname == 'abs' and expr.args:
                return self.api.ops.abs(self.compile_expr(expr.args[0], fn_name, params))
            if fname in {'int', 'float'} and expr.args:
                return self.compile_expr(expr.args[0], fn_name, params)
            # robot.* expression helpers
            if fname == 'robot.angle':
                axis = 'yaw'
                if expr.args:
                    a = self.const_eval(expr.args[0])
                    if isinstance(a, str):
                        axis = a
                return self.api.sensor.angle(axis)
            if fname == 'robot.motor_relative_position' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.motor.relative_position(port)
            if fname == 'robot.motor_speed' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.motor.speed(port)
            if fname == 'robot.color' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.sensor.color(port)
            if fname == 'robot.distance' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.sensor.distance(port)
            if fname == 'robot.force' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.sensor.force(port)
            if fname == 'robot.reflectivity' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.sensor.reflectivity(port)
            # sensor reporters without port
            if fname == 'robot.timer':
                return self.api.sensor.timer()
            if fname == 'robot.loudness':
                return self.api.sensor.loudness()
            if fname == 'robot.button_pressed':
                button = self.compile_expr(expr.args[0], fn_name, params) if expr.args else 'center'
                return self.api.sensor.button_pressed(button)
            if fname == 'robot.button_released':
                button = self.compile_expr(expr.args[0], fn_name, params) if expr.args else 'center'
                return self.api.sensor.button_released(button)
            # motor reporters
            if fname == 'robot.motor_absolute_position' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.motor.absolute_position(port)
            # boolean sensor checks
            if fname == 'robot.is_color' and len(expr.args) >= 2:
                port = self.compile_expr(expr.args[0], fn_name, params)
                color = self.compile_expr(expr.args[1], fn_name, params)
                return self.api.sensor.is_color(port, color)
            if fname == 'robot.is_distance' and len(expr.args) >= 3:
                port = self.compile_expr(expr.args[0], fn_name, params)
                comp = self.compile_expr(expr.args[1], fn_name, params)
                val = self.compile_expr(expr.args[2], fn_name, params)
                return self.api.sensor.is_distance(port, comp, val)
            if fname == 'robot.is_pressed' and expr.args:
                port = self.compile_expr(expr.args[0], fn_name, params)
                return self.api.sensor.is_pressed(port)
            if fname.endswith('.contains') and isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name):
                base = expr.func.value.id
                if base in self.list_decls and expr.args:
                    return self.api.lists.contains(self.list_decls[base], self.compile_expr(expr.args[0], fn_name, params))
            if fname.endswith('.get') and isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name):
                base = expr.func.value.id
                if base in self.list_decls and expr.args:
                    index_expr = self.compile_expr(expr.args[0], fn_name, params)
                    one_based = self.api.ops.add(index_expr, 1)
                    return self.api.lists.item(self.list_decls[base], one_based)
            if fname.endswith('.pop') and isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name):
                base = expr.func.value.id
                if base in self.list_decls:
                    if expr.args:
                        index_expr = self.compile_expr(expr.args[0], fn_name, params)
                    else:
                        index_expr = self.api.ops.sub(self.api.lists.length(self.list_decls[base]), 1)
                    one_based = self.api.ops.add(index_expr, 1)
                    return self.api.lists.item(self.list_decls[base], one_based)
            if isinstance(expr.func, ast.Name):
                # Proc call used as an expression value: return the unique return variable.
                # The call must have been executed (as a statement) before this expression
                # is evaluated for the retval to be current.
                proc_name = expr.func.id
                if proc_name in self.proc_return_vars:
                    self.note(
                        f'proc call {proc_name}() used inside an expression; '
                        f'reads __retval_{proc_name} which was set by the last call',
                        expr,
                    )
                    return self.api.vars.get(self.proc_return_vars[proc_name].retval_var, raw=True)
                full_args = self._fill_proc_args(proc_name, expr, fn_name, params)
                return self.api.flow.call(proc_name, *full_args)
        if isinstance(expr, ast.BoolOp) and expr.values:
            compiled = [self.compile_condition(v, fn_name, params) for v in expr.values]
            acc = compiled[0]
            for other in compiled[1:]:
                if isinstance(expr.op, ast.And):
                    acc = self.api.ops.and_(acc, other)
                elif isinstance(expr.op, ast.Or):
                    acc = self.api.ops.or_(acc, other)
            return acc
        if isinstance(expr, ast.BinOp):
            a = self.compile_expr(expr.left, fn_name, params)
            b = self.compile_expr(expr.right, fn_name, params)
            if isinstance(expr.op, ast.Add): return self.api.ops.add(a, b)
            if isinstance(expr.op, ast.Sub): return self.api.ops.sub(a, b)
            if isinstance(expr.op, ast.Mult): return self.api.ops.mul(a, b)
            if isinstance(expr.op, ast.Div): return self.api.ops.div(a, b)
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and len(expr.comparators) == 1:
            left = self.compile_expr(expr.left, fn_name, params)
            right_node = expr.comparators[0]
            right = self.compile_expr(right_node, fn_name, params)
            op = expr.ops[0]
            if isinstance(op, ast.Lt): return self.api.ops.lt(left, right)
            if isinstance(op, ast.Gt): return self.api.ops.gt(left, right)
            if isinstance(op, ast.Eq): return self.api.ops.eq(left, right)
            if isinstance(op, ast.LtE): return self.api.ops.lt(left, self.api.ops.add(right, 0.0001))
            if isinstance(op, ast.GtE): return self.api.ops.gt(left, self.api.ops.sub(right, 0.0001))
            if isinstance(op, ast.In) and isinstance(right_node, ast.Name) and right_node.id in self.list_decls:
                return self.api.lists.contains(self.list_decls[right_node.id], left)
            if isinstance(op, ast.NotIn) and isinstance(right_node, ast.Name) and right_node.id in self.list_decls:
                contains = self.api.lists.contains(self.list_decls[right_node.id], left)
                return self.api.ops.not_(contains)
        if isinstance(expr, ast.Subscript):
            # Python-first list indexing: 0-based -> Scratch list item is 1-based
            if isinstance(expr.value, ast.Name) and expr.value.id in self.list_decls:
                index_expr = self._compile_subscript_index(expr.slice, fn_name, params)
                one_based = self.api.ops.add(index_expr, 1)
                return self.api.lists.item(self.list_decls[expr.value.id], one_based)
        return 0

    def _compile_subscript_index(self, slice_node: ast.AST, fn_name: str, params: set[str]) -> Any:
        if isinstance(slice_node, ast.Constant):
            return slice_node.value
        return self.compile_expr(slice_node, fn_name, params)

    def compile_condition(self, expr: ast.expr, fn_name: str, params: set[str]) -> str:
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
            return self.negate_condition(expr.operand, fn_name, params)
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and len(expr.comparators) == 1:
            left = self.compile_expr(expr.left, fn_name, params)
            right_node = expr.comparators[0]
            right = self.compile_expr(right_node, fn_name, params)
            op = expr.ops[0]
            if isinstance(op, ast.Lt): return self.api.ops.lt(left, right)
            if isinstance(op, ast.Gt): return self.api.ops.gt(left, right)
            if isinstance(op, ast.Eq): return self.api.ops.eq(left, right)
            if isinstance(op, ast.LtE): return self.api.ops.lt(left, self.api.ops.add(right, 0.0001))
            if isinstance(op, ast.GtE): return self.api.ops.gt(left, self.api.ops.sub(right, 0.0001))
            if isinstance(op, ast.In) and isinstance(right_node, ast.Name) and right_node.id in self.list_decls:
                return self.api.lists.contains(self.list_decls[right_node.id], left)
            if isinstance(op, ast.NotIn) and isinstance(right_node, ast.Name) and right_node.id in self.list_decls:
                contains = self.api.lists.contains(self.list_decls[right_node.id], left)
                return self.api.ops.not_(contains)
        value = self.compile_expr(expr, fn_name, params)
        return self.api.ops.gt(value, 0)

    def negate_condition(self, expr: ast.expr, fn_name: str, params: set[str]) -> str:
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and len(expr.comparators) == 1:
            left = self.compile_expr(expr.left, fn_name, params)
            right_node = expr.comparators[0]
            right = self.compile_expr(right_node, fn_name, params)
            op = expr.ops[0]
            if isinstance(op, ast.Lt): return self.api.ops.not_(self.api.ops.lt(left, right))
            if isinstance(op, ast.Gt): return self.api.ops.not_(self.api.ops.gt(left, right))
            if isinstance(op, ast.Eq): return self.api.ops.not_(self.api.ops.eq(left, right))
            if isinstance(op, ast.LtE): return self.api.ops.gt(left, right)
            if isinstance(op, ast.GtE): return self.api.ops.lt(left, right)
            if isinstance(op, ast.In) and isinstance(right_node, ast.Name) and right_node.id in self.list_decls:
                contains = self.api.lists.contains(self.list_decls[right_node.id], left)
                return self.api.ops.not_(contains)
            if isinstance(op, ast.NotIn) and isinstance(right_node, ast.Name) and right_node.id in self.list_decls:
                return self.api.lists.contains(self.list_decls[right_node.id], left)
        inner = self.compile_condition(expr, fn_name, params)
        return self.api.ops.not_(inner)

    # ---------- statements ----------

    def compile_body(self, body: list[ast.stmt], fn_name: str, params: set[str],
                     loop_ctx: LoopContext | None = None,
                     return_ctx: ReturnContext | None = None) -> list[str]:
        out: list[str] = []
        for stmt in body:
            compiled = self.compile_stmt(stmt, fn_name, params, loop_ctx=loop_ctx, return_ctx=return_ctx)
            if loop_ctx is None and return_ctx is None:
                out.extend(compiled)
            else:
                for blk in compiled:
                    # Create a fresh guard for each block – Scratch blocks can only have one parent.
                    guard = self._execution_guard(loop_ctx, return_ctx)
                    out.append(self.api.flow.if_(guard, blk))
        return out

    def _execution_guard(self, loop_ctx: LoopContext | None, return_ctx: ReturnContext | None) -> str:
        """Build a boolean condition that is True only when execution should proceed.

        Combines the loop break/continue guard with the function return guard so
        that a single ``control_if`` wraps each statement.
        """
        guards: list[str] = []
        if loop_ctx is not None:
            guards.append(self.loop_guard(loop_ctx))
        if return_ctx is not None:
            r = self.api.vars.get(return_ctx.flag_var, raw=True)
            guards.append(self.api.ops.eq(r, 0))
        if not guards:
            raise RuntimeError("_execution_guard called with no context")
        result = guards[0]
        for g in guards[1:]:
            result = self.api.ops.and_(result, g)
        return result

    def loop_guard(self, loop_ctx: LoopContext) -> str:
        b = self.api.vars.get(loop_ctx.break_var, namespace=loop_ctx.fn_name)
        if loop_ctx.continue_var:
            c = self.api.vars.get(loop_ctx.continue_var, namespace=loop_ctx.fn_name)
            return self.api.ops.and_(self.api.ops.eq(b, 0), self.api.ops.eq(c, 0))
        return self.api.ops.eq(b, 0)

    def _compile_list_side_effect(self, call: ast.Call, fn_name: str, params: set[str]) -> list[str] | None:
        if not isinstance(call.func, ast.Attribute) or not isinstance(call.func.value, ast.Name):
            return None
        base = call.func.value.id
        if base not in self.list_decls:
            return None
        m = call.func.attr
        lname = self.list_decls[base]
        if m == 'append' and call.args:
            return [self.api.lists.append(lname, self.compile_expr(call.args[0], fn_name, params))]
        if m == 'clear':
            return [self.api.lists.clear(lname)]
        if m == 'insert' and len(call.args) >= 2:
            idx = self.compile_expr(call.args[0], fn_name, params)
            item = self.compile_expr(call.args[1], fn_name, params)
            return [self.api.lists.insert(lname, self.api.ops.add(idx, 1), item)]
        if m == 'set' and len(call.args) >= 2:
            idx = self.compile_expr(call.args[0], fn_name, params)
            item = self.compile_expr(call.args[1], fn_name, params)
            return [self.api.lists.setitem(lname, self.api.ops.add(idx, 1), item)]
        if m == 'remove' and call.args:
            target = self.compile_expr(call.args[0], fn_name, params)
            idx_var = f"__rm_idx_{getattr(call,'lineno','rm')}"
            done_var = f"__rm_done_{getattr(call,'lineno','rm')}"
            self.api.vars.ensure(idx_var, 0, namespace=fn_name)
            self.api.vars.ensure(done_var, 0, namespace=fn_name)
            idx_ref = self.api.vars.get(idx_var, namespace=fn_name)
            done_ref = self.api.vars.get(done_var, namespace=fn_name)
            one_based = self.api.ops.add(idx_ref, 1)
            current = self.api.lists.item(lname, one_based)
            body = [
                self.api.flow.if_(self.api.ops.eq(current, target),
                    self.api.lists.delete(lname, one_based),
                    self.api.vars.set(done_var, 1, namespace=fn_name),
                ),
                self.api.flow.if_(self.api.ops.eq(done_ref, 0),
                    self.api.vars.set(idx_var, self.api.ops.add(idx_ref, 1), namespace=fn_name)
                )
            ]
            cond = self.api.ops.or_(self._truthy(done_ref), self.api.ops.gt(idx_ref, self.api.ops.sub(self.api.lists.length(lname), 1)))
            return [
                self.api.vars.set(idx_var, 0, namespace=fn_name),
                self.api.vars.set(done_var, 0, namespace=fn_name),
                self.api.flow.repeat_until(cond, *body),
            ]
        return None

    def compile_stmt(self, stmt: ast.stmt, fn_name: str, params: set[str],
                     loop_ctx: LoopContext | None = None,
                     return_ctx: ReturnContext | None = None) -> list[str]:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            special = self._compile_list_side_effect(stmt.value, fn_name, params)
            if special is not None:
                return special
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target_node = stmt.targets[0]
            if isinstance(target_node, ast.Name):
                target = target_node.id
                # Direct assignment from a proc call with return value: result = my_proc(args)
                if (isinstance(stmt.value, ast.Call) and
                        isinstance(stmt.value.func, ast.Name) and
                        stmt.value.func.id in self.proc_return_vars):
                    proc_name = stmt.value.func.id
                    rctx = self.proc_return_vars[proc_name]
                    full_args = self._fill_proc_args(proc_name, stmt.value, fn_name, params)
                    call_blk = self.api.flow.call(proc_name, *full_args)
                    self.api.vars.ensure(target, 0, namespace=fn_name)
                    assign_blk = self.api.vars.set(
                        target,
                        self.api.vars.get(rctx.retval_var, raw=True),
                        namespace=fn_name,
                    )
                    return [call_blk, assign_blk]
                # top-level list declaration inside function is not supported, but keep note
                if self._is_ls_list_call(stmt.value):
                    lname = self._extract_list_name(stmt.value, target)
                    self.list_decls[target] = lname
                    self.api.lists.add(lname, [])
                    return []
                self.api.vars.ensure(target, 0, namespace=fn_name)
                return [self.api.vars.set(target, self.compile_expr(stmt.value, fn_name, params), namespace=fn_name)]
            if isinstance(target_node, ast.Subscript) and isinstance(target_node.value, ast.Name) and target_node.value.id in self.list_decls:
                index_expr = self._compile_subscript_index(target_node.slice, fn_name, params)
                one_based = self.api.ops.add(index_expr, 1)
                return [self.api.lists.setitem(self.list_decls[target_node.value.id], one_based, self.compile_expr(stmt.value, fn_name, params))]

        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            name = stmt.target.id
            self.api.vars.ensure(name, 0, namespace=fn_name)
            rhs = self.compile_expr(stmt.value, fn_name, params)
            cur = self.api.vars.get(name, namespace=fn_name)
            if isinstance(stmt.op, ast.Add):
                return [self.api.vars.set(name, self.api.ops.add(cur, rhs), namespace=fn_name)]
            if isinstance(stmt.op, ast.Sub):
                return [self.api.vars.set(name, self.api.ops.sub(cur, rhs), namespace=fn_name)]
            if isinstance(stmt.op, ast.Mult):
                return [self.api.vars.set(name, self.api.ops.mul(cur, rhs), namespace=fn_name)]
            if isinstance(stmt.op, ast.Div):
                return [self.api.vars.set(name, self.api.ops.div(cur, rhs), namespace=fn_name)]

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return [self.compile_call(stmt.value, fn_name, params)]

        if isinstance(stmt, ast.If):
            cond = self.compile_condition(stmt.test, fn_name, params)
            body = self.compile_body(stmt.body, fn_name, params, loop_ctx=loop_ctx, return_ctx=return_ctx)
            out = [self.api.flow.if_(cond, *body)] if body else []
            if stmt.orelse:
                else_cond = self.negate_condition(stmt.test, fn_name, params)
                else_body = self.compile_body(stmt.orelse, fn_name, params, loop_ctx=loop_ctx, return_ctx=return_ctx)
                if else_body:
                    out.append(self.api.flow.if_(else_cond, *else_body))
            return out

        if isinstance(stmt, ast.While):
            break_var = f"__break_{getattr(stmt,'lineno','while')}"
            cont_var = f"__continue_{getattr(stmt,'lineno','while')}"
            self.api.vars.ensure(break_var, 0, namespace=fn_name)
            self.api.vars.ensure(cont_var, 0, namespace=fn_name)
            wctx = LoopContext('while', fn_name, break_var, cont_var)
            init_blocks = [
                self.api.vars.set(break_var, 0, namespace=fn_name),
                self.api.vars.set(cont_var, 0, namespace=fn_name),
            ]
            body_blocks = [self.api.vars.set(cont_var, 0, namespace=fn_name)]
            body_blocks.extend(self.compile_body(stmt.body, fn_name, params, loop_ctx=wctx, return_ctx=return_ctx))
            if isinstance(stmt.test, ast.Constant) and stmt.test.value is True:
                end_cond = self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 1)
            else:
                end_cond = self.api.ops.or_(
                    self.negate_condition(stmt.test, fn_name, params),
                    self.api.vars.get(break_var, namespace=fn_name)
                )
            out = [*init_blocks, self.api.flow.repeat_until(end_cond, *body_blocks)]
            if stmt.orelse:
                else_body = self.compile_body(stmt.orelse, fn_name, params, return_ctx=return_ctx)
                if else_body:
                    out.append(self.api.flow.if_(self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 0), *else_body))
            return out

        if isinstance(stmt, ast.For):
            break_var = f"__break_{getattr(stmt,'lineno','for')}"
            cont_var = f"__continue_{getattr(stmt,'lineno','for')}"
            self.api.vars.ensure(break_var, 0, namespace=fn_name)
            self.api.vars.ensure(cont_var, 0, namespace=fn_name)
            lctx = LoopContext('for', fn_name, break_var, cont_var)
            init_blocks = [self.api.vars.set(break_var, 0, namespace=fn_name)]
            # support for range(...), for item in list, and enumerate(list)
            if isinstance(stmt.iter, ast.Name) and stmt.iter.id in self.list_decls:
                loop_var = stmt.target.id if isinstance(stmt.target, ast.Name) else None
                index_name = f"__idx_{loop_var or 'item'}_{getattr(stmt,'lineno','for')}"
                self.api.vars.ensure(index_name, 0, namespace=fn_name)
                init_blocks.append(self.api.vars.set(index_name, 0, namespace=fn_name))
                body_params = params | ({loop_var} if loop_var else set())
                body_blocks = [self.api.vars.set(cont_var, 0, namespace=fn_name)]
                if loop_var:
                    self.api.vars.ensure(loop_var, 0, namespace=fn_name)
                    one_based = self.api.ops.add(self.api.vars.get(index_name, namespace=fn_name), 1)
                    body_blocks.append(self.api.vars.set(loop_var, self.api.lists.item(self.list_decls[stmt.iter.id], one_based), namespace=fn_name))
                body_blocks.extend(self.compile_body(stmt.body, fn_name, body_params, loop_ctx=lctx, return_ctx=return_ctx))
                inc_guard = self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 0)
                body_blocks.append(self.api.flow.if_(inc_guard, self.api.vars.set(index_name, self.api.ops.add(self.api.vars.get(index_name, namespace=fn_name), 1), namespace=fn_name)))
                cond = self.api.ops.or_(self.api.ops.gt(self.api.vars.get(index_name, namespace=fn_name), self.api.ops.sub(self.api.lists.length(self.list_decls[stmt.iter.id]), 1)), self.api.vars.get(break_var, namespace=fn_name))
                return [*init_blocks, self.api.flow.repeat_until(cond, *body_blocks)]
            if isinstance(stmt.iter, ast.Call) and self.attr_name(stmt.iter.func) == 'enumerate' and stmt.iter.args and isinstance(stmt.iter.args[0], ast.Name) and stmt.iter.args[0].id in self.list_decls and isinstance(stmt.target, ast.Tuple) and len(stmt.target.elts)==2:
                idx_target = stmt.target.elts[0].id if isinstance(stmt.target.elts[0], ast.Name) else None
                item_target = stmt.target.elts[1].id if isinstance(stmt.target.elts[1], ast.Name) else None
                index_name = f"__idx_{(item_target or 'item')}_{getattr(stmt,'lineno','for')}"
                self.api.vars.ensure(index_name, 0, namespace=fn_name)
                init_blocks.append(self.api.vars.set(index_name, 0, namespace=fn_name))
                body_params = params | ({idx_target} if idx_target else set()) | ({item_target} if item_target else set())
                body_blocks = [self.api.vars.set(cont_var, 0, namespace=fn_name)]
                if idx_target and idx_target != '_':
                    self.api.vars.ensure(idx_target, 0, namespace=fn_name)
                    body_blocks.append(self.api.vars.set(idx_target, self.api.vars.get(index_name, namespace=fn_name), namespace=fn_name))
                if item_target and item_target != '_':
                    self.api.vars.ensure(item_target, 0, namespace=fn_name)
                    one_based = self.api.ops.add(self.api.vars.get(index_name, namespace=fn_name), 1)
                    body_blocks.append(self.api.vars.set(item_target, self.api.lists.item(self.list_decls[stmt.iter.args[0].id], one_based), namespace=fn_name))
                body_blocks.extend(self.compile_body(stmt.body, fn_name, body_params, loop_ctx=lctx, return_ctx=return_ctx))
                inc_guard = self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 0)
                body_blocks.append(self.api.flow.if_(inc_guard, self.api.vars.set(index_name, self.api.ops.add(self.api.vars.get(index_name, namespace=fn_name), 1), namespace=fn_name)))
                cond = self.api.ops.or_(self.api.ops.gt(self.api.vars.get(index_name, namespace=fn_name), self.api.ops.sub(self.api.lists.length(self.list_decls[stmt.iter.args[0].id]), 1)), self.api.vars.get(break_var, namespace=fn_name))
                return [*init_blocks, self.api.flow.repeat_until(cond, *body_blocks)]
            range_lowered = self._compile_for_range_loop(stmt, fn_name, params, lctx, break_var, cont_var, init_blocks, return_ctx=return_ctx)
            if range_lowered is not None:
                return range_lowered
            self.note('only for range(...) is supported in python-first mode', stmt)
            return init_blocks

        if isinstance(stmt, ast.Break):
            if loop_ctx is None:
                self.note('break outside loop skipped', stmt)
                return []
            return [self.api.vars.set(loop_ctx.break_var, 1, namespace=loop_ctx.fn_name)]

        if isinstance(stmt, ast.Continue):
            if loop_ctx is None or not loop_ctx.continue_var:
                self.note('continue outside loop skipped', stmt)
                return []
            return [self.api.vars.set(loop_ctx.continue_var, 1, namespace=loop_ctx.fn_name)]

        if isinstance(stmt, ast.Delete):
            out = []
            for target in stmt.targets:
                if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id in self.list_decls:
                    index_expr = self._compile_subscript_index(target.slice, fn_name, params)
                    one_based = self.api.ops.add(index_expr, 1)
                    out.append(self.api.lists.delete(self.list_decls[target.value.id], one_based))
                else:
                    self.note('unsupported delete target skipped', stmt)
            return out

        if isinstance(stmt, ast.Return):
            if return_ctx is None:
                # return outside a proc with return value: no-op
                return []
            blocks: list[str] = []
            if stmt.value is not None:
                blocks.append(self.api.vars.set(return_ctx.retval_var,
                                                self.compile_expr(stmt.value, fn_name, params),
                                                raw=True))
            blocks.append(self.api.vars.set(return_ctx.flag_var, 1, raw=True))
            # When inside a loop, also set the loop break flag to exit the loop early.
            if loop_ctx is not None:
                blocks.append(self.api.vars.set(loop_ctx.break_var, 1, namespace=loop_ctx.fn_name))
            return blocks

        self.note(f'unsupported stmt skipped: {type(stmt).__name__}', stmt)
        return []

    def _compile_for_range(self, stmt: ast.For, fn_name: str, params: set[str]):
        loop_var = stmt.target.id if isinstance(stmt.target, ast.Name) else None
        init_blocks: list[str] = []
        times: Any = 0
        step_value: Any = 1
        if isinstance(stmt.iter, ast.Call) and self.attr_name(stmt.iter.func) == 'range':
            args = stmt.iter.args
            if len(args) == 1:
                times = self.compile_expr(args[0], fn_name, params)
                if loop_var and loop_var != '_':
                    self.api.vars.ensure(loop_var, 0, namespace=fn_name)
                    init_blocks.append(self.api.vars.set(loop_var, 0, namespace=fn_name))
            elif len(args) == 2:
                start = self.compile_expr(args[0], fn_name, params)
                stop = self.compile_expr(args[1], fn_name, params)
                times = self.api.ops.sub(stop, start)
                if loop_var and loop_var != '_':
                    self.api.vars.ensure(loop_var, 0, namespace=fn_name)
                    init_blocks.append(self.api.vars.set(loop_var, start, namespace=fn_name))
            elif len(args) == 3:
                c0 = self.const_eval(args[0])
                c1 = self.const_eval(args[1])
                c2 = self.const_eval(args[2])
                if all(isinstance(v, int) for v in [c0, c1, c2]) and c2 != 0:
                    times = len(range(c0, c1, c2))
                    step_value = c2
                    if loop_var and loop_var != '_':
                        self.api.vars.ensure(loop_var, 0, namespace=fn_name)
                        init_blocks.append(self.api.vars.set(loop_var, c0, namespace=fn_name))
                else:
                    self.note('range(start, stop, step) currently supports constant integer step/limits only', stmt)
                    times = 0
            else:
                self.note('range with more than 3 args is unsupported', stmt)
                times = 0
        else:
            self.note('only for range(...) is supported in python-first mode', stmt)
        if loop_var == '_':
            loop_var = None
        return times, init_blocks, loop_var, step_value

    def _compile_for_range_loop(self, stmt: ast.For, fn_name: str, params: set[str], lctx: LoopContext,
                                break_var: str, cont_var: str, init_blocks: list[str],
                                return_ctx: ReturnContext | None = None) -> list[str] | None:
        if not (isinstance(stmt.iter, ast.Call) and self.attr_name(stmt.iter.func) == 'range'):
            return None
        args = stmt.iter.args
        loop_var = stmt.target.id if isinstance(stmt.target, ast.Name) else None
        if loop_var == '_':
            loop_var = None
        if len(args) == 1:
            start = 0
            stop = self.compile_expr(args[0], fn_name, params)
            step_const = 1
        elif len(args) == 2:
            start = self.compile_expr(args[0], fn_name, params)
            stop = self.compile_expr(args[1], fn_name, params)
            step_const = 1
        elif len(args) == 3:
            start = self.compile_expr(args[0], fn_name, params)
            stop = self.compile_expr(args[1], fn_name, params)
            c2 = self.const_eval(args[2])
            if not isinstance(c2, int) or c2 == 0:
                self.note('range(start, stop, step) currently supports constant non-zero integer step only', stmt)
                return None
            step_const = c2
        else:
            self.note('range with more than 3 args is unsupported', stmt)
            return None

        if loop_var:
            self.api.vars.ensure(loop_var, 0, namespace=fn_name)
            init_blocks.append(self.api.vars.set(loop_var, start, namespace=fn_name))
        else:
            loop_var = f"__range_value_{getattr(stmt,'lineno','for')}"
            self.api.vars.ensure(loop_var, 0, namespace=fn_name)
            init_blocks.append(self.api.vars.set(loop_var, start, namespace=fn_name))

        body_params = params | {loop_var}
        body_blocks = [self.api.vars.set(cont_var, 0, namespace=fn_name)]
        body_blocks.extend(self.compile_body(stmt.body, fn_name, body_params, loop_ctx=lctx, return_ctx=return_ctx))
        inc_guard = self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 0)
        body_blocks.append(self.api.flow.if_(inc_guard, self.api.vars.set(loop_var, self.api.ops.add(self.api.vars.get(loop_var, namespace=fn_name), step_const), namespace=fn_name)))

        if step_const > 0:
            keep_going = self.api.ops.lt(self.api.vars.get(loop_var, namespace=fn_name), stop)
        else:
            keep_going = self.api.ops.gt(self.api.vars.get(loop_var, namespace=fn_name), stop)
        cond = self.api.ops.or_(self.api.ops.not_(keep_going), self.api.vars.get(break_var, namespace=fn_name))
        return [*init_blocks, self.api.flow.repeat_until(cond, *body_blocks)]

    # ---------- calls ----------

    def ensure_runtime(self):
        if not self.runtime_installed:
            self.api.robot.install_pid(motor_pair=self.runtime_config['motor_pair'], left_dir=self.runtime_config['left_dir'], right_dir=self.runtime_config['right_dir'])
            self.runtime_installed = True

    def ensure_stdlib_group(self, group: str) -> None:
        """Install a stdlib group on first use (idempotent)."""
        if group not in self._stdlib_groups_installed:
            getattr(self.api.stdlib, group)()
            self._stdlib_groups_installed.add(group)

    def compile_call(self, call: ast.Call, fn_name: str, params: set[str]) -> str:
        name = self.attr_name(call.func)
        args = [self.compile_expr(a, fn_name, params) for a in call.args]

        if name == 'run.sleep_ms':
            ms = self.compile_expr(call.args[0], fn_name, params) if call.args else 0
            return self.api.wait.ms(ms if isinstance(ms, int) else 0)
        if name == 'run.sleep':
            secs = self.compile_expr(call.args[0], fn_name, params) if call.args else 0
            return self.api.wait.seconds(float(secs) if isinstance(secs, (int, float)) else 0)
        if name == 'run.broadcast':
            msg = self.const_eval(call.args[0]) if call.args else ''
            if isinstance(msg, str) and msg:
                return self.api.flow.broadcast(msg)
            self.note(f"run.broadcast: non-constant message — skipped", call)
            return None
        if name == 'run.broadcast_and_wait':
            msg = self.const_eval(call.args[0]) if call.args else ''
            if isinstance(msg, str) and msg:
                return self.api.flow.broadcast_and_wait(msg)
            self.note(f"run.broadcast_and_wait: non-constant message — skipped", call)
            return None

        if name == 'robot.use_pair' and len(args) >= 2:
            pair = f"{args[0]}{args[1]}"
            self.runtime_config['motor_pair'] = str(pair)
            return self.api.move.pair(str(pair))
        if name == 'robot.set_direction':
            # handle keywords for compile-time config only
            left = 1
            right = -1
            for kw in call.keywords:
                if kw.arg == 'left':
                    v = self.const_eval(kw.value)
                    if isinstance(v, (int, float)):
                        left = 1 if v >= 0 else -1
                if kw.arg == 'right':
                    v = self.const_eval(kw.value)
                    if isinstance(v, (int, float)):
                        right = 1 if v >= 0 else -1
            self.runtime_config['left_dir'] = left
            self.runtime_config['right_dir'] = right
            return self.api.wait.seconds(0)
        if name == 'robot.forward_cm':
            self.ensure_runtime()
            return self.api.robot.straight_cm(args[0], args[1] if len(args) > 1 else None)
        if name == 'robot.forward_deg':
            self.ensure_runtime()
            return self.api.robot.straight_deg(args[0], args[1] if len(args) > 1 else None)
        if name == 'robot.backward_cm':
            self.ensure_runtime()
            return self.api.robot.straight_cm(self.api.ops.sub(0, args[0]), args[1] if len(args) > 1 else None)
        if name == 'robot.turn_deg':
            self.ensure_runtime()
            return self.api.robot.turn_deg(args[0], args[1] if len(args) > 1 else None)
        if name == 'robot.pivot_left':
            self.ensure_runtime()
            return self.api.robot.pivot_left_deg(args[0], args[1] if len(args) > 1 else None)
        if name == 'robot.pivot_right':
            self.ensure_runtime()
            return self.api.robot.pivot_right_deg(args[0], args[1] if len(args) > 1 else None)
        if name == 'robot.stop':
            return self.api.move.stop()
        if name == 'robot.pause_ms':
            return self.api.wait.ms(args[0] if args else 0)
        if name == 'robot.show_text':
            return self.api.light.show_text(args[0] if args else '')
        if name == 'robot.show_image':
            return self.api.light.show_image(args[0] if args else 'HEART')
        if name == 'robot.clear_display':
            return self.api.light.clear()
        if name == 'robot.beep':
            if len(args) >= 2:
                return self.api.sound.beep_for(args[0], args[1])
            return self.api.sound.beep(args[0] if args else 60)
        if name == 'robot.stop_sound':
            return self.api.sound.stop()
        if name == 'robot.reset_yaw':
            return self.api.sensor.reset_yaw()
        if name == 'robot.show_monitor':
            # Metadata-only: marks a variable as visible in the SPIKE monitor panel.
            # Resolves keyword args from the AST call if present.
            if not args:
                return None  # no var name given — silently skip
            var_name_val = self.const_eval(call.args[0]) if call.args else None
            if not isinstance(var_name_val, str):
                return None
            kw = {kw.arg: self.const_eval(kw.value) for kw in call.keywords}
            visible = kw.get('visible', True)
            slider_min = kw.get('slider_min', None)
            slider_max = kw.get('slider_max', None)
            discrete = kw.get('discrete', True)
            try:
                self.api.vars.show_monitor(var_name_val, visible=visible,
                                           slider_min=slider_min, slider_max=slider_max,
                                           discrete=discrete)
            except KeyError:
                pass  # variable not yet declared — silently skip
            return None  # no block generated
        if name == 'robot.run_motor':
            return self.api.motor.run(args[0] if args else 'A', args[1] if len(args) > 1 else 500)
        if name == 'robot.run_motor_power':
            return self.api.motor.run_power(args[0] if args else 'A', args[1] if len(args) > 1 else 100)
        if name == 'robot.stop_motor':
            return self.api.motor.stop(args[0] if args else 'A')
        if name == 'robot.motor_run_for_degrees':
            return self.api.motor.run_for_degrees(args[0] if args else 'A', args[1] if len(args) > 1 else 360, args[2] if len(args) > 2 else 500)
        if name == 'robot.run_motor_for_seconds':
            return self.api.motor.run_for_seconds(args[0] if args else 'A', args[1] if len(args) > 1 else 1, args[2] if len(args) > 2 else 500)
        if name == 'robot.run_motor_for':
            # robot.run_motor_for(port, direction, value, unit)
            port = args[0] if args else 'A'
            direction = args[1] if len(args) > 1 else 'clockwise'
            value = args[2] if len(args) > 2 else 360
            unit = args[3] if len(args) > 3 else 'degrees'
            return self.api.motor.run_for_direction(port, direction, value, unit)
        if name == 'robot.motor_go_to_position':
            # robot.motor_go_to_position(port, direction, position)
            port = args[0] if args else 'A'
            direction = args[1] if len(args) > 1 else 'shortest'
            position = args[2] if len(args) > 2 else 0
            return self.api.motor.go_to_position(port, direction, position)
        if name == 'robot.set_motor_stop_mode':
            return self.api.motor.set_stop_mode(args[0] if args else 'A', args[1] if len(args) > 1 else 'brake')
        if name == 'robot.motor_reset_position':
            port = args[0] if args else 'A'
            value = args[1] if len(args) > 1 else 0
            return self.api.motor.reset_relative_position(port, value)
        if name == 'robot.reset_timer':
            return self.api.sensor.reset_timer()
        if name == 'robot.show_image_for':
            image = args[0] if args else 'HEART'
            seconds = args[1] if len(args) > 1 else 1
            return self.api.light.show_image_for(image, seconds)
        if name == 'robot.set_pixel':
            x = args[0] if args else 0
            y = args[1] if len(args) > 1 else 0
            brightness = args[2] if len(args) > 2 else 100
            return self.api.light.set_pixel(x, y, brightness)
        if name == 'robot.set_display_brightness':
            return self.api.light.set_brightness(args[0] if args else 100)
        if name == 'robot.set_center_light':
            return self.api.light.set_center_button(args[0] if args else 'white')
        if name == 'robot.play_sound':
            return self.api.sound.play(args[0] if args else 1)
        if name == 'robot.play_sound_until_done':
            return self.api.sound.play_until_done(args[0] if args else 1)
        if name == 'robot.drive':
            left = args[0] if args else 0
            right = args[1] if len(args) > 1 else 0
            return self.api.move.start_dual_speed(left, right)
        if name == 'robot.steer':
            steering = args[0] if args else 0
            speed = args[1] if len(args) > 1 else 50
            return self.api.move.steer(steering, speed)

        # list operations
        if name.endswith('.append') and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            base = call.func.value.id
            if base in self.list_decls:
                return self.api.lists.append(self.list_decls[base], args[0] if args else '')
        if name.endswith('.clear') and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            base = call.func.value.id
            if base in self.list_decls:
                return self.api.lists.clear(self.list_decls[base])
        if name.endswith('.pop') and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            base = call.func.value.id
            if base in self.list_decls:
                if args:
                    one_based = self.api.ops.add(args[0], 1)
                else:
                    one_based = self.api.lists.length(self.list_decls[base])
                return self.api.lists.delete(self.list_decls[base], one_based)
        if name.endswith('.set') and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            base = call.func.value.id
            if base in self.list_decls and len(args) >= 2:
                one_based = self.api.ops.add(args[0], 1)
                return self.api.lists.setitem(self.list_decls[base], one_based, args[1])

        # stdlib calls (install group lazily on first use)
        # Math group: Clamp, MapRange, Sign, MinVal, MaxVal, Lerp, Deadzone, Smooth
        if name == 'stdlib.clamp':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("Clamp", *args[:3])
        if name == 'stdlib.map_range':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("MapRange", *args[:5])
        if name == 'stdlib.sign':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("Sign", *args[:1])
        if name == 'stdlib.min_val':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("MinVal", *args[:2])
        if name == 'stdlib.max_val':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("MaxVal", *args[:2])
        if name == 'stdlib.lerp':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("Lerp", *args[:3])
        if name == 'stdlib.deadzone':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("Deadzone", *args[:2])
        if name == 'stdlib.smooth':
            self.ensure_stdlib_group('math')
            return self.api.flow.call("Smooth", *args[:3])
        # Timing group: WaitOrTimeout, set_wait_done, reset_wait
        if name == 'stdlib.wait_or_timeout':
            self.ensure_stdlib_group('timing')
            return self.api.flow.call("WaitOrTimeout", *args[:1])
        if name == 'stdlib.set_wait_done':
            self.ensure_stdlib_group('timing')
            val = args[0] if args else 1
            return self.api.stdlib.set_wait_done(val)
        if name == 'stdlib.reset_wait':
            self.ensure_stdlib_group('timing')
            return self.api.stdlib.reset_wait()
        # Display group: Countdown, FlashText
        if name == 'stdlib.countdown':
            self.ensure_stdlib_group('display')
            return self.api.flow.call("Countdown", *args[:1])
        if name == 'stdlib.flash_text':
            self.ensure_stdlib_group('display')
            return self.api.flow.call("FlashText", *args[:2])
        # Sensors group: SmoothYaw
        if name == 'stdlib.smooth_yaw':
            self.ensure_stdlib_group('sensors')
            return self.api.flow.call("SmoothYaw", *args[:1])

        # procedure call
        if isinstance(call.func, ast.Name):
            proc_name = call.func.id
            full_args = self._fill_proc_args(proc_name, call, fn_name, params)
            return self.api.flow.call(proc_name, *full_args)

        self.note(f'unsupported call lowered to no-op: {name}', call)
        return self.api.wait.seconds(0)

    # ---------- utils ----------

    def _is_ls_list_call(self, expr: ast.expr) -> bool:
        return isinstance(expr, ast.Call) and self.attr_name(expr.func) == 'ls.list'

    def _extract_list_name(self, expr: ast.Call, fallback: str) -> str:
        if expr.args and isinstance(expr.args[0], ast.Constant) and isinstance(expr.args[0].value, str):
            return expr.args[0].value
        return fallback

    def attr_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return self.attr_name(node.value) + '.' + node.attr
        if isinstance(node, ast.Call):
            return self.attr_name(node.func)
        return ''


def _load_source(path: str | Path) -> ast.Module:
    path = Path(path)
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

