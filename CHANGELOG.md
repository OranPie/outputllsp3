# Changelog

All notable changes to `outputllsp3` are documented here.

---

## 0.32.0 — 2026-03-17

- Added default parameter value support for `@robot.proc` procedures in
  python-first mode and AST transpiler.
- Params with defaults (e.g. `def move(speed=420, dist=20):`) store their
  defaults in the Scratch `argumentdefaults` mutation field.
- Calls with fewer args than params have missing positional args filled from
  the proc's stored defaults at the call site.
- Keyword arguments at call sites (e.g. `move(dist=30)`) are now supported
  and matched to the declared parameter order.
- `project.py` `define_procedure()` accepts an optional `defaults` list;
  `call_procedure()` applies defaults for missing args.
- `flow.py` `procedure()` accepts an optional `defaults` keyword argument.
- Exporter (python-first style) reads `argumentdefaults` from proc mutations
  and emits `def proc(a, b=default):` in the decompiled output.

## 0.31.0 — 2026-03-17

- Added custom function return value support for `@robot.proc` procedures in
  python-first mode.
- Each proc that uses `return value` gets a unique `__retval_<proc>` variable
  (readable after the call) and a `__return_<proc>` flag that guards
  subsequent statements so they are skipped after return.
- Direct assignment from a proc call (`result = my_proc(args)`) is
  automatically lowered to call + retval read.
- Return inside a loop also sets the loop break flag so the loop exits
  immediately.
- Proc calls used inside expressions (not as a direct assignment RHS) fall
  back to reading the retval variable from the last call, with a compile note.
- Added the same return-value support to the AST transpiler (`ast_transpiler.py`).
- Exporter (python-first style) recognises the `__retval_*` / `__return_*`
  patterns and emits clean `return value` and `result = proc(args)` in the
  decompiled output.

## 0.29.0 — 2026-03-16

- Fixed `NameError` in pythonfirst `const_eval` when a `BoolOp` expression
  appeared at module level.
- Fixed parent-pointer validation error when using `not (x == y)` in
  python-first mode.
- Fixed `negate_condition` fallback in python-first mode to use
  `operator_not` instead of `eq(value, 0)`.
- Fixed ast_transpiler `negate_condition` Eq case and UnsupportedNode fallback.
- `parser.parse_llsp3` now accepts `.llsp` files; gives clearer error
  messages for missing archive members.
- Added `export_llsp3_to_python` to the public `__all__` export list.

## 0.28.0 — 2026-03-15

- Python-first export now emits valid Python placeholders instead of
  invalid comment-like expression stubs.
- Python-first export recognizes more drivebase and sensor patterns and
  lifts common procedure calls to `robot.*` helpers when possible.

## 0.26.0 — 2026-03-15

- `export-python` now supports `builder` style for a cleaner, more
  editable exact-reconstruction export.
- Exported builder files include summary and high-level hints while
  preserving exact-reconstruction semantics.

## 0.24.0 — 2026-03-15

- Python-first `range(start, stop, step)` now lowers through a
  range-to-while strategy for constant non-zero integer steps, supporting
  dynamic start/stop expressions.

## 0.23.0 — 2026-03-15

- Python-first adds `list.insert()` and `list.remove()` lowering.

## 0.21.0 — 2026-03-15

- Python-first adds `range(start, stop, step)` for constant integer steps
  and higher-level list helpers (`.contains` / `.get` / `.set`).

## 0.20.0 — 2026-03-15

- Python-first adds `while-else`, `in` / `not in` as expressions, and more
  stable while break/continue lowering.

## 0.19.0 — 2026-03-15

- Python-first adds `enumerate(list)`, while condition, and loop
  break/continue lowering.

## 0.14.0 — 2026-03-15

- Python-first AST adds `else`, while condition, list `setitem`, and list
  iteration.
- Added ergonomic API aliases and scoped namespace helper.
- Added `flow.chain` / `seq` / `comment` helpers.

## 0.12.0 — 2026-03-15

- Strict verified mode for non-fabricated block opcodes.
