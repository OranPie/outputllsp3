# Changelog

All notable changes to `outputllsp3` are documented here.

---

## 0.36.0

### Human-readable export — all three styles

#### `python-first` exporter (`outputllsp3/exporter/python_first.py`)
- **Module docstring** at top of every export: filename, style, block/variable/list/procedure counts
- **Section headers** (`# ── Variables ───────`) separating variables, lists, procedures, entry points
- **Conditional `import math`** — added only when `operator_mathop` uses `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `ln`, `log`, `e^`, `floor`, or `ceiling`
- **Trig degree correction** — `sin(x)` emits `math.sin(math.radians(x))` because LEGO uses degrees
- **`abs` uses builtin** — no `import math` needed for `abs(x)`
- **Lists as `= []`** — list variables initialized as Python lists instead of `ls.list(name)`; `ls` import removed
- **Unknown opcodes** degrade gracefully: `pass  # TODO: 'opcode'` / `0  # TODO: 'opcode'`; diagnostic footer lists any unhandled opcodes
- **8 new opcode handlers**: `flippermoremotor_motorStartSpeed`, `motorTurnForSpeed`, `motorSetStopMethod`, `motorSetDegreeCounted`; `flippermoremove_startSteerAtSpeed`, `steerDistanceAtSpeed`; `flipperlight_lightDisplayText`, `centerButtonLight`; `control_for_each`

#### `builder` exporter (`outputllsp3/exporter/builder.py`)
- `_OPCODE_LABELS` dict with 60+ human-readable labels (covers all SPIKE block categories)
- Every `_set_block()` call now has an inline `# Human Label` comment
- Variable/list declarations annotated with `# name: <var_name>`
- Section headers grouping top-level blocks, procedures, and remaining blocks

#### `raw` exporter (`outputllsp3/exporter/raw.py`)
- Inline opcode comments on every block assignment line (reuses `_opcode_label` from builder)
- Variable/list declarations annotated with `# name: <var_name>`

#### Tests
- 25 new tests in `tests/test_export_readable.py` covering all improvements above
- Total test count: **293 passing**

---

## 0.33.0 — 2026-03-17

### Enhanced llsp3-to-Python export flow (`python-first` style)

**New expression mappings (`render_expr`)**

- Boolean operators: `operator_and`, `operator_or`, `operator_not` →
  `(a and b)`, `(a or b)`, `(not a)`
- Arithmetic: `operator_mod` → `(a % b)`, `operator_random` →
  `random.randint(from, to)`, `operator_round` → `round(x)`
- String operators: `operator_join` → `str(a) + str(b)`,
  `operator_length` → `len(s)`, `operator_letter_of` → `s[i-1]`,
  `operator_contains` → `(b in a)`
- `flipperoperator_isInBetween` → `(lo <= value <= hi)`
- `data_itemnumoflist` → `lst.index(item) + 1`
- Sensor reporters: `flippersensors_orientationAxis` → `robot.angle('yaw')`,
  `flippersensors_timer` → `run.timer()`,
  `flippersensors_loudness` → `run.loudness()`,
  `flippersensors_buttonIsPressed` → `robot.button(...) == ...`,
  `flippersensors_ismotion` → `robot.is_moving(...)`,
  `flippersensors_isTilted` → `robot.is_tilted(...)`,
  `flippersensors_distance` → `robot.distance(port.X, unit)`,
  `flippersensors_reflectivity` → `robot.reflected_light(port.X)`,
  `flippersensors_color` → `robot.color(port.X)`,
  `flippersensors_isColor` → `robot.is_color(port.X, color)`,
  `flippersensors_isDistance` → `robot.is_distance(...)`,
  `flippersensors_force` → `robot.force(port.X, unit)`
- Motor reporters: `flippermotor_speed` → `robot.motor_speed(port.X)`,
  `flippermotor_absolutePosition` → `robot.motor_position(port.X)`,
  `flippermoremotor_position` → `robot.motor_relative_position(port.X)`

**New statement mappings (`render_stmt`)**

- `control_forever` → `while True:` with full body rendering
- `control_stop` / `flippercontrol_stop` → `return` (or `return  # stop: all`)
- `control_wait_until` → polling `while not (cond): run.sleep(0.01)`
- Upgraded from `__stmt__(...)` placeholders to real calls:
  - `flippermove_setMovementPair` → `robot.use_pair(port.X, port.Y)`
  - `flippermoremove_startDualSpeed` → `robot.drive(left, right)`
  - `flippermoremove_startDualPower` → `robot.drive_power(left, right)`
  - `flippermoremotor_motorSetDegreeCounted` → `robot.set_motor_position(port.X, v)`
  - `flippersensors_resetYaw` → `robot.reset_yaw()`
  - `flippersensors_resetTimer` → `run.reset_timer()`
- Motor opcodes: `flippermotor_motorStartDirection` → `robot.run_motor(...)`,
  `flippermotor_motorStop` → `robot.stop_motor(port.X)`,
  `flippermotor_motorTurnForDirection` → `robot.run_motor_for(...)`,
  `flippermotor_motorGoDirectionToPosition` → `robot.motor_go_to_position(...)`,
  `flippermotor_motorSetSpeed` → `robot.set_motor_speed(port.X, speed)`
- Sound opcodes: `flippersound_beep` → `robot.beep(note)`,
  `flippersound_beepForTime` → `robot.beep_for(note, duration)`,
  `flippersound_stopSound` → `robot.stop_sound()`,
  `flippersound_playSound` → `robot.play_sound(sound)`,
  `flippersound_playSoundUntilDone` → `robot.play_sound_until_done(sound)`
- Display opcodes: `flipperdisplay_ledMatrix` → `robot.show_image(port.X, m)`,
  `flipperdisplay_ledMatrixFor` → `robot.show_image_for(...)`,
  `flipperdisplay_ledMatrixText` → `robot.show_text(port.X, text)`,
  `flipperdisplay_ledMatrixOff` → `robot.turn_off_pixels(port.X)`,
  `flipperdisplay_ledMatrixOn` → `robot.set_pixel(...)`,
  `flipperdisplay_ledMatrixBrightness` → `robot.set_pixel_brightness(...)`,
  `flipperdisplay_centerButtonLight` → `robot.set_center_light(color)`

**Structural improvements**

- Fixed broken duplicate `procedures_call` case in `render_stmt`.
- Multiple `whenProgramStarts` stacks now each become their own
  `@run.main`-decorated function (`main`, `main_1`, `main_2`, …) instead of
  being merged into a single body.
- `import random` is now included in the generated header so that
  `random.randint` expressions work without manual imports.

**`parser.LLSP3Document`**

- Added `lists` property (symmetric with `variables`).
- `summary()` now includes `list_count` and `list_names`.

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
