from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .api import API
from .project import LLSP3Project
from .transpiler import autodiscover


class UnsupportedNode(Exception):
    pass


class ASTBuilder:
    def __init__(self, project: LLSP3Project, source_path: str | Path):
        self.project = project
        self.api = API(project)
        self.source_path = Path(source_path)
        self.mod_name = self.source_path.stem
        self.const_env: dict[str, Any] = {"math.pi": 3.141592653589793}
        self.notes: list[str] = []

    def note(self, msg: str, node: ast.AST | None = None) -> None:
        line = getattr(node, 'lineno', '?') if node is not None else '?'
        self.notes.append(f"L{line}: {msg}")

    def transpile(self, tree: ast.Module) -> None:
        # top-level constants
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                value = self.const_eval(node.value)
                if value is not None:
                    self.const_env[node.targets[0].id] = value
                    self.api.vars.add(node.targets[0].id, value)

        funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn in funcs:
            if fn.name.startswith('_'):
                continue
            self.compile_function(fn)

        # detect runloop.run(main()) or main() at module end
        start_body = []
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                c = node.value
                if self.attr_name(c.func) == 'runloop.run' and c.args:
                    target = c.args[0]
                    if isinstance(target, ast.Call) and isinstance(target.func, ast.Name):
                        start_body.append(self.api.flow.call(target.func.id))
                    elif isinstance(target, ast.Name):
                        start_body.append(self.api.flow.call(target.id))
                elif isinstance(c.func, ast.Name) and c.func.id == 'main':
                    start_body.append(self.api.flow.call('main'))
        if not start_body and any(f.name == 'main' for f in funcs):
            start_body.append(self.api.flow.call('main'))
        if start_body:
            self.api.flow.start(*start_body)
            if self.notes:
                self.project.add_comment(start_body[0], "ast transpile notes:\n" + "\n".join(self.notes[:12]), x=120, y=20, width=420, height=180)

    def compile_function(self, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = [a.arg for a in fn.args.args]
        body_blocks = self.compile_body(fn.body, fn_name=fn.name)
        self.api.flow.procedure(fn.name, args, *body_blocks, x=720, y=120 + len(self.project.blocks) * 4)

    def compile_body(self, body: list[ast.stmt], fn_name: str) -> list[str]:
        out: list[str] = []
        i = 0
        while i < len(body):
            # pattern: motor.run(A, x); motor.run(B, y)  => dual_speed(x, y)
            if i + 1 < len(body) and self._is_call_stmt(body[i], 'motor.run') and self._is_call_stmt(body[i + 1], 'motor.run'):
                c1 = self._stmt_call(body[i]); c2 = self._stmt_call(body[i + 1])
                p1 = self._port_name_from_expr(c1.args[0]) if len(c1.args) >= 1 else None
                p2 = self._port_name_from_expr(c2.args[0]) if len(c2.args) >= 1 else None
                if p1 in {'A', 'B'} and p2 in {'A', 'B'} and p1 != p2 and len(c1.args) >= 2 and len(c2.args) >= 2:
                    left_expr = self.compile_expr(c1.args[1], fn_name) if p1 == 'A' else self.compile_expr(c2.args[1], fn_name)
                    right_expr = self.compile_expr(c2.args[1], fn_name) if p2 == 'B' else self.compile_expr(c1.args[1], fn_name)
                    out.append(self.api.move.dual_speed(left_expr, right_expr))
                    i += 2
                    continue
            # pattern: motor.stop(A); motor.stop(B) => stop
            if i + 1 < len(body) and self._is_call_stmt(body[i], 'motor.stop') and self._is_call_stmt(body[i + 1], 'motor.stop'):
                out.append(self.api.move.stop())
                i += 2
                continue
            out.extend(self.compile_stmt(body[i], fn_name=fn_name))
            i += 1
        return out

    def _stmt_call(self, stmt: ast.stmt) -> ast.Call:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return stmt.value
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await) and isinstance(stmt.value.value, ast.Call):
            return stmt.value.value
        raise UnsupportedNode('not a call stmt')

    def _is_call_stmt(self, stmt: ast.stmt, name: str) -> bool:
        try:
            return self.attr_name(self._stmt_call(stmt).func) == name
        except Exception:
            return False

    def compile_stmt(self, stmt: ast.stmt, fn_name: str) -> list[str]:
        api = self.api
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            name = stmt.targets[0].id
            api.vars.add(name, 0, namespace=fn_name)
            return [api.vars.set(name, self.compile_expr(stmt.value, fn_name), namespace=fn_name)]
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            name = stmt.target.id
            api.vars.add(name, 0, namespace=fn_name)
            rhs = self.compile_expr(stmt.value, fn_name)
            if isinstance(stmt.op, ast.Add):
                return [api.vars.set(name, api.ops.add(api.vars.get(name, namespace=fn_name), rhs), namespace=fn_name)]
            if isinstance(stmt.op, ast.Sub):
                return [api.vars.set(name, api.ops.sub(api.vars.get(name, namespace=fn_name), rhs), namespace=fn_name)]
        if isinstance(stmt, ast.Expr):
            if isinstance(stmt.value, ast.Call):
                return [self.compile_call(stmt.value, fn_name)]
            if isinstance(stmt.value, ast.Await) and isinstance(stmt.value.value, ast.Call):
                return [self.compile_call(stmt.value.value, fn_name)]
        if isinstance(stmt, ast.If):
            cond = self.compile_condition(stmt.test, fn_name)
            body = self.compile_body(stmt.body, fn_name)
            out = [api.flow.if_(cond, *body)] if body else []
            if stmt.orelse:
                self.note('else branch skipped (not yet lowered)', stmt)
            return out
        if isinstance(stmt, ast.While) and isinstance(stmt.test, ast.Constant) and stmt.test.value is True:
            cond = None
            rest = stmt.body
            if rest and isinstance(rest[0], ast.If) and len(rest[0].body) == 1 and isinstance(rest[0].body[0], ast.Break):
                cond = self.negate_condition(rest[0].test, fn_name)
                rest = rest[1:]
            else:
                # fallback: loop until impossible false, preserve body structure
                cond = self.api.ops.eq(1, 0)
                self.note('while True without top break guard lowered as repeat-until(false)', stmt)
            return [api.flow.repeat_until(cond, *self.compile_body(rest, fn_name))]
        if isinstance(stmt, ast.Return):
            return []
        self.note(f'unsupported stmt skipped: {type(stmt).__name__}', stmt)
        return []

    def compile_condition(self, expr: ast.expr, fn_name: str) -> str:
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
            return self.negate_condition(expr.operand, fn_name)
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and len(expr.comparators) == 1:
            left = self.compile_expr(expr.left, fn_name)
            right = self.compile_expr(expr.comparators[0], fn_name)
            op = expr.ops[0]
            if isinstance(op, ast.Lt): return self.api.ops.lt(left, right)
            if isinstance(op, ast.Gt): return self.api.ops.gt(left, right)
            if isinstance(op, ast.Eq): return self.api.ops.eq(left, right)
            if isinstance(op, ast.LtE): return self.api.ops.lt(left, self.api.ops.add(right, 0.0001))
            if isinstance(op, ast.GtE): return self.api.ops.gt(left, self.api.ops.sub(right, 0.0001))
        raise UnsupportedNode(ast.dump(expr))

    def negate_condition(self, expr: ast.expr, fn_name: str) -> str:
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and len(expr.comparators) == 1:
            left = self.compile_expr(expr.left, fn_name)
            right = self.compile_expr(expr.comparators[0], fn_name)
            op = expr.ops[0]
            if isinstance(op, ast.Lt): return self.api.ops.not_(self.api.ops.lt(left, right))
            if isinstance(op, ast.Gt): return self.api.ops.not_(self.api.ops.gt(left, right))
            if isinstance(op, ast.Eq): return self.api.ops.not_(self.api.ops.eq(left, right))
            if isinstance(op, ast.LtE): return self.api.ops.gt(left, right)
            if isinstance(op, ast.GtE): return self.api.ops.lt(left, right)
        inner = self.compile_condition(expr, fn_name)
        return self.api.ops.not_(inner)

    def compile_expr(self, expr: ast.expr, fn_name: str) -> Any:
        # direct special-case for motion_sensor.tilt_angles()[0] / 10.0 pattern
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
            if self._is_tilt_angles_index_zero(expr.left) and isinstance(expr.right, ast.Constant) and float(expr.right.value) == 10.0:
                return self.api.sensor.angle()
        if isinstance(expr, ast.Constant):
            return expr.value
        if isinstance(expr, ast.Name):
            if expr.id in {'True', 'False'}:
                return int(expr.id == 'True')
            try:
                return self.project.arg(expr.id)
            except Exception:
                pass
            try:
                return self.api.vars.get(expr.id, namespace=fn_name)
            except Exception:
                try:
                    return self.api.vars.get(expr.id)
                except Exception:
                    return self.const_env.get(expr.id, expr.id)
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
            return self.api.ops.sub(0, self.compile_expr(expr.operand, fn_name))
        if isinstance(expr, ast.BinOp):
            a = self.compile_expr(expr.left, fn_name)
            b = self.compile_expr(expr.right, fn_name)
            if isinstance(expr.op, ast.Add): return self.api.ops.add(a, b)
            if isinstance(expr.op, ast.Sub): return self.api.ops.sub(a, b)
            if isinstance(expr.op, ast.Mult): return self.api.ops.mul(a, b)
            if isinstance(expr.op, ast.Div): return self.api.ops.div(a, b)
        if isinstance(expr, ast.Call):
            name = self.attr_name(expr.func)
            if name == 'abs':
                return self.api.ops.abs(self.compile_expr(expr.args[0], fn_name))
            if name in {'int', 'float'} and expr.args:
                return self.compile_expr(expr.args[0], fn_name)
            if name == 'yaw_deg':
                return self.api.sensor.angle()
            if name == 'avg_motor_deg':
                return self.api.ops.div(self.api.ops.add(self.api.motor.relative_position('A'), self.api.motor.relative_position('B')), 2)
            if name == 'abs_avg_motor_deg':
                return self.api.ops.div(self.api.ops.add(self.api.ops.abs(self.api.motor.relative_position('A')), self.api.ops.abs(self.api.motor.relative_position('B'))), 2)
            if isinstance(expr.func, ast.Name):
                return self.api.flow.call(expr.func.id, *[self.compile_expr(a, fn_name) for a in expr.args])
        if self._is_tilt_angles_index_zero(expr):
            return self.api.sensor.angle()
        if isinstance(expr, ast.Attribute):
            name = self.attr_name(expr)
            if name in {'port.A', 'hub.port.A'}: return 'A'
            if name in {'port.B', 'hub.port.B'}: return 'B'
            if name in {'port.C', 'hub.port.C'}: return 'C'
            if name in {'port.D', 'hub.port.D'}: return 'D'
            if name == 'math.pi': return 3.141592653589793
        return 0

    def compile_call(self, call: ast.Call, fn_name: str) -> str:
        name = self.attr_name(call.func)
        args = [self.compile_expr(a, fn_name) for a in call.args]
        if name == 'runloop.sleep_ms':
            ms = call.args[0].value if call.args and isinstance(call.args[0], ast.Constant) else 20
            return self.api.wait.ms(int(ms))
        if name == 'motion_sensor.reset_yaw':
            return self.api.sensor.reset_yaw()
        if name == 'motor.reset_relative_position':
            return self.api.motor.set_relative_position(args[0], args[1] if len(args) > 1 else 0)
        if name == 'motor.relative_position':
            return self.api.motor.relative_position(args[0])
        if name == 'motor.run':
            port = self._port_name_from_expr(call.args[0]) if call.args else None
            speed = args[1] if len(args) > 1 else 0
            if port == 'A':
                return self.api.move.dual_speed(speed, 0)
            if port == 'B':
                return self.api.move.dual_speed(0, speed)
            self.note('motor.run mapped only for A/B pair; skipped', call)
            return self.api.wait.seconds(0.0)
        if name == 'motor.stop':
            port = self._port_name_from_expr(call.args[0]) if call.args else None
            if port in {'A', 'B'}:
                return self.api.move.stop()
            return self.api.wait.seconds(0.0)
        if isinstance(call.func, ast.Name):
            return self.api.flow.call(call.func.id, *args)
        self.note(f'unsupported call lowered to no-op: {name}', call)
        return self.api.wait.seconds(0.0)

    def const_eval(self, expr: ast.expr):
        try:
            return ast.literal_eval(expr)
        except Exception:
            pass
        if isinstance(expr, ast.Name):
            return self.const_env.get(expr.id)
        if isinstance(expr, ast.Attribute):
            return self.const_env.get(self.attr_name(expr))
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

    def _is_tilt_angles_index_zero(self, expr: ast.expr) -> bool:
        if isinstance(expr, ast.Subscript):
            if self.attr_name(expr.value) == 'motion_sensor.tilt_angles':
                sl = expr.slice
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    return True
        return False

    def _port_name_from_expr(self, expr: ast.expr) -> str | None:
        v = self.compile_expr(expr, fn_name='')
        if isinstance(v, str) and v in {'A', 'B', 'C', 'D'}:
            return v
        return None

    def attr_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return self.attr_name(node.value) + '.' + node.attr
        if isinstance(node, ast.Call):
            return self.attr_name(node.func)
        return ''


def transpile_python_source(path: str | Path, *, template: str | Path | None = None, strings: str | Path | None = None,
                            out: str | Path, sprite_name: str | None = None, function_namespace: bool = False) -> Path:
    path = Path(path)
    auto = autodiscover(path.parent)
    template = Path(template) if template else auto['template']
    strings = Path(strings) if strings else auto['strings']
    if template is None or strings is None:
        raise FileNotFoundError('Could not auto-discover template or strings.json')
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(path))
    project = LLSP3Project(template, strings, sprite_name=sprite_name or path.stem)
    project.set_default_namespace(path.stem, function_namespace=function_namespace)
    builder = ASTBuilder(project, path)
    try:
        builder.transpile(tree)
        return project.save(out)
    finally:
        project.cleanup()
