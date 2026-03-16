from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .api import API
from .project import LLSP3Project
from .workflow import discover_defaults
from .enums import Port as _PortEnum


# ----------------------------
# Public Python-first syntax helpers
# ----------------------------

class _RuntimeListProxy:
    def __init__(self, name: str):
        self.name = name
    def append(self, item: Any):
        return None
    def clear(self):
        return None
    def insert(self, index: int, item: Any):
        return None
    def remove(self, item: Any):
        return None
    def pop(self, index: int = -1):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")
    def contains(self, item: Any):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")
    def get(self, index: int):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")
    def set(self, index: int, value: Any):
        return None
    def __len__(self):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")
    def __contains__(self, item: Any):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")
    def __getitem__(self, index: int):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")
    def __setitem__(self, index: int, value: Any):
        return None


class _ListModule:
    def list(self, name: str) -> _RuntimeListProxy:
        return _RuntimeListProxy(name)


class _RunModule:
    def main(self, fn):
        fn.__outputllsp3_main__ = True
        return fn
    def sleep_ms(self, ms: int):
        return None
    def sleep(self, seconds: float):
        return None


class _RobotModule:
    def proc(self, fn):
        fn.__outputllsp3_proc__ = True
        return fn
    def use_pair(self, right: Any, left: Any):
        return None
    def set_direction(self, *, left: int = 1, right: int = -1):
        return None
    def forward_cm(self, distance_cm: Any, speed: Any | None = None):
        return None
    def forward_deg(self, target_deg: Any, speed: Any | None = None):
        return None
    def backward_cm(self, distance_cm: Any, speed: Any | None = None):
        return None
    def turn_deg(self, angle_deg: Any, speed: Any | None = None):
        return None
    def pivot_left(self, angle_deg: Any, speed: Any | None = None):
        return None
    def pivot_right(self, angle_deg: Any, speed: Any | None = None):
        return None
    def stop(self):
        return None
    def pause_ms(self, ms: int):
        return None


class _PortModule:
    A = _PortEnum.A.value
    B = _PortEnum.B.value
    C = _PortEnum.C.value
    D = _PortEnum.D.value
    E = _PortEnum.E.value
    F = _PortEnum.F.value


robot = _RobotModule()
run = _RunModule()
port = _PortModule()
ls = _ListModule()


def reset_pythonfirst_registry():
    # compatibility no-op; old tracing mode removed in favor of AST compilation
    return None


# ----------------------------
# AST-based Python-first transpiler
# ----------------------------

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
        self.runtime_config = {
            "motor_pair": "AB",
            "left_dir": 1,
            "right_dir": -1,
        }
        self.runtime_installed = False

    def note(self, msg: str, node: ast.AST | None = None) -> None:
        line = getattr(node, "lineno", "?") if node is not None else "?"
        self.notes.append(f"L{line}: {msg}")

    # ---------- top-level analysis ----------

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
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                deco_names = [self.attr_name(d) for d in node.decorator_list]
                if "run.main" in deco_names:
                    self.main_def = node
                if "robot.proc" in deco_names:
                    self.proc_defs.append(node)

    def declare_resources(self):
        for pyname, lname in self.list_decls.items():
            self.api.lists.add(lname, [])
        # Create explicit variables only when a top-level constant is referenced later via vars lookup.
        # In python-first mode, constants are typically inlined.

    # ---------- compile ----------

    def transpile(self, tree: ast.Module):
        self.analyze(tree)
        self.declare_resources()

        # procedures first
        idx = 0
        for fn in self.proc_defs:
            params = [a.arg for a in fn.args.args]
            body = self.compile_body(fn.body, fn_name=fn.name, params=set(params))
            self.api.flow.procedure(fn.name, params, *body, x=700, y=160 + idx * 230)
            idx += 1

        if self.main_def is None:
            raise RuntimeError("No @run.main function found")

        main_body = self.compile_body(self.main_def.body, fn_name=self.main_def.name, params=set())
        start = self.api.flow.start(x=-220, y=90)
        self.api.flow.chain(start, *main_body)
        if self.notes:
            self.project.add_comment(start, "python-first notes:\n" + "\n".join(self.notes[:12]), x=20, y=20, width=420, height=180)

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
            return self.const_env.get(name)
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
            v = self.const_eval(expr.operand)
            return -v if isinstance(v, (int, float)) else None
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
            if name in self.const_env:
                return self.const_env[name]
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
                return self.api.flow.call(expr.func.id, *[self.compile_expr(a, fn_name, params) for a in expr.args])
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

    def compile_body(self, body: list[ast.stmt], fn_name: str, params: set[str], loop_ctx: LoopContext | None = None) -> list[str]:
        out: list[str] = []
        for stmt in body:
            compiled = self.compile_stmt(stmt, fn_name, params, loop_ctx=loop_ctx)
            if loop_ctx is None:
                out.extend(compiled)
            else:
                # Continue/break semantics: after either flag is set, skip the rest of the user body.
                for blk in compiled:
                    out.append(self.api.flow.if_(self.loop_guard(loop_ctx), blk))
        return out

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

    def compile_stmt(self, stmt: ast.stmt, fn_name: str, params: set[str], loop_ctx: LoopContext | None = None) -> list[str]:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            special = self._compile_list_side_effect(stmt.value, fn_name, params)
            if special is not None:
                return special
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target_node = stmt.targets[0]
            if isinstance(target_node, ast.Name):
                target = target_node.id
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
            if isinstance(stmt.op, ast.Add):
                return [self.api.vars.set(name, self.api.ops.add(self.api.vars.get(name, namespace=fn_name), rhs), namespace=fn_name)]
            if isinstance(stmt.op, ast.Sub):
                return [self.api.vars.set(name, self.api.ops.sub(self.api.vars.get(name, namespace=fn_name), rhs), namespace=fn_name)]

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return [self.compile_call(stmt.value, fn_name, params)]

        if isinstance(stmt, ast.If):
            cond = self.compile_condition(stmt.test, fn_name, params)
            body = self.compile_body(stmt.body, fn_name, params, loop_ctx=loop_ctx)
            out = [self.api.flow.if_(cond, *body)] if body else []
            if stmt.orelse:
                else_cond = self.negate_condition(stmt.test, fn_name, params)
                else_body = self.compile_body(stmt.orelse, fn_name, params, loop_ctx=loop_ctx)
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
            body_blocks.extend(self.compile_body(stmt.body, fn_name, params, loop_ctx=wctx))
            if isinstance(stmt.test, ast.Constant) and stmt.test.value is True:
                end_cond = self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 1)
            else:
                end_cond = self.api.ops.or_(
                    self.negate_condition(stmt.test, fn_name, params),
                    self.api.vars.get(break_var, namespace=fn_name)
                )
            out = [*init_blocks, self.api.flow.repeat_until(end_cond, *body_blocks)]
            if stmt.orelse:
                else_body = self.compile_body(stmt.orelse, fn_name, params)
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
                body_blocks.extend(self.compile_body(stmt.body, fn_name, body_params, loop_ctx=lctx))
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
                body_blocks.extend(self.compile_body(stmt.body, fn_name, body_params, loop_ctx=lctx))
                inc_guard = self.api.ops.eq(self.api.vars.get(break_var, namespace=fn_name), 0)
                body_blocks.append(self.api.flow.if_(inc_guard, self.api.vars.set(index_name, self.api.ops.add(self.api.vars.get(index_name, namespace=fn_name), 1), namespace=fn_name)))
                cond = self.api.ops.or_(self.api.ops.gt(self.api.vars.get(index_name, namespace=fn_name), self.api.ops.sub(self.api.lists.length(self.list_decls[stmt.iter.args[0].id]), 1)), self.api.vars.get(break_var, namespace=fn_name))
                return [*init_blocks, self.api.flow.repeat_until(cond, *body_blocks)]
            range_lowered = self._compile_for_range_loop(stmt, fn_name, params, lctx, break_var, cont_var, init_blocks)
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
            return []

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
                                break_var: str, cont_var: str, init_blocks: list[str]) -> list[str] | None:
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
        body_blocks.extend(self.compile_body(stmt.body, fn_name, body_params, loop_ctx=lctx))
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

    def compile_call(self, call: ast.Call, fn_name: str, params: set[str]) -> str:
        name = self.attr_name(call.func)
        args = [self.compile_expr(a, fn_name, params) for a in call.args]

        if name == 'run.sleep_ms':
            ms = self.compile_expr(call.args[0], fn_name, params) if call.args else 0
            return self.api.wait.ms(ms if isinstance(ms, int) else 0)
        if name == 'run.sleep':
            secs = self.compile_expr(call.args[0], fn_name, params) if call.args else 0
            return self.api.wait.seconds(float(secs) if isinstance(secs, (int, float)) else 0)

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

        # procedure call
        if isinstance(call.func, ast.Name):
            return self.api.flow.call(call.func.id, *args)

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


def transpile_pythonfirst_file(path: str | Path, *, template: str | Path | None = None, strings: str | Path | None = None, out: str | Path = None, sprite_name: str | None = None, strict_verified: bool = False):
    path = Path(path)
    defaults = discover_defaults(path.parent)
    template = Path(template) if template else defaults['template']
    strings = Path(strings) if strings else defaults['strings']
    out = Path(out)
    project = LLSP3Project(template, strings, sprite_name=sprite_name or out.stem)
    project.set_default_namespace(path.stem)
    project.set_strict_verified(strict_verified)
    ctx = PythonFirstContext(project, path)
    try:
        ctx.transpile(_load_source(path))
        return project.save(out)
    finally:
        project.cleanup()
