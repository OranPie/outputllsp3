# Examples

This directory contains example programs demonstrating different ways to use
`outputllsp3`.

---

## Running an Example

All examples compile to `.llsp3` files that can be uploaded to the LEGO
Education SPIKE app.

### Unified entry point (recommended)

```bash
# Auto-detects mode from file content:
outputllsp3 build examples/01_spike_builder_hello.py --out hello.llsp3

# Python-first files:
outputllsp3 build-python examples/12_python_first_sensors.py --out sensors.llsp3
```

### Build-script examples

```bash
outputllsp3 build examples/<file>.py --out <file>.llsp3
```

### Python-first examples

```bash
outputllsp3 build-python examples/python_first_robot.py --out robot.llsp3
outputllsp3 build-python examples/python_first_defaults.py --out defaults.llsp3
outputllsp3 build-python examples/python_first_return.py --out return.llsp3
```

---

## New Examples (interface expansion)

### `01_spike_builder_hello.py`

Minimal `SpikeBuilder` program — the new recommended entry point.

- `SpikeBuilder(project)` construction
- `b.setup(motor_pair=MotorPair.AB)` one-liner init
- `b.flow.start()`, `b.move`, `b.wait`, `b.sensor` sub-namespaces
- Typed `Port` and `MotorPair` enums

### `02_spike_builder_robot.py`

Full robot movement sequence using `SpikeBuilder`.

- `b.flow.proc()` to define reusable procedures
- `b.flow.call()` to invoke them
- `b.sensor.yaw()` expression as block input
- `b.ops.div()` for computed wait duration

### `03_spike_builder_sensors.py`

Sensor-reactive program: drive, stop on color/obstacle.

- `b.sensor.color_is()` with `Color` enum
- `b.sensor.distance_is()` with `Comparator` enum
- `b.flow.wait_until()`, `b.flow.if_else()`, `b.flow.forever()`
- `b.sensor.force_is_pressed()` as start trigger

### `04_spike_builder_display.py`

Light and sound show using all `LightImage` and `Color` enum values.

- Full `LightImage` enum slideshow
- `b.light.set_pixel()` for custom pixel art
- `b.light.set_center_button()` with `Color` enum
- `b.sound.beep_for()` fanfare sequence

### `05_flow_helpers.py`

New `FlowBuilder` helpers: `for_loop`, `while_loop`, `cond`.

- `api.flow.for_loop(var, start, end, *body)` — counted loop
- `api.flow.while_loop(condition, *body)` — repeat while true
- `api.flow.cond(condition, a, b)` — inline conditional expression

### `06_variables_and_lists.py`

Variables, lists, and the full operator set.

- `api.vars.add_many()`, `get()`, `set()`, `change()`
- `api.lists.add()`, `append()`, `clear()`, `get_item()`, `length()`
- `api.ops` arithmetic, string join, abs, round, random
- Building a formatted summary string from list data

### `07_transpile_unified.py`

Demonstrates the new `transpile()` unified entry point.

- `transpile(source, mode='auto', out=...)` replaces 6 separate functions
- `_detect_transpile_mode()` heuristic (directory/`@robot.proc`/`def build(`)
- Explicit mode override with `mode='build_script'`

### `08_auto_layout.py`

Auto-layout system — no more magic coordinate numbers.

- Multiple `api.flow.start()` calls without `x`/`y` — auto-stacked vertically
- Multiple `api.flow.procedure()` calls without `x`/`y` — auto-spread horizontally
- Explicit `x=999, y=888` override still works

### `09_namespaced_modules.py`

Multi-subsystem robot with namespace isolation.

- `api.namespace("drive")` and `api.namespace("arm")` context managers
- `api.vars.add_many()` for bulk constant declaration per subsystem
- Variables from different namespaces coexist without collision

### `10_new_enums.py`

Every new enum type used in context.

- `StopMode.BRAKE` / `COAST` / `HOLD` with `motor.set_stop_mode()`
- `Color.RED` / `GREEN` etc. with `sensor.color_is()` and `light.set_center_button()`
- `Comparator.LESS_THAN` with `sensor.distance_is()`
- `Axis.PITCH` / `ROLL` / `YAW` with `sensor.angle()`
- `LightImage` enum for strongly-typed image names

### `11_pid_robot.py`

Full PID-controlled competition robot using `api.drivebase`.

- `api.drivebase.install_pid_runtime(…)` installs ~6 procedures + ~20 variables
- `api.robot.straight_cm()`, `turn_deg()`, `pivot_left_deg()` high-level calls
- Wait-for-button-press start trigger

### `12_python_first_sensors.py`

Python-first style with sensors, lists, and multi-proc composition.

- `@robot.proc` with sensor readings
- `ls.list()` for data logging
- `robot.angle("yaw")` expression stubs
- `while` loop with counter inside a proc

### `13_competition_run.py`

Realistic competition-style program: three missions + return home.

- `SpikeBuilder` throughout for readable code
- Motor encoder–based `DriveDeg` procedure
- Shared `mission_ok` counter variable
- Auto-layout for all procedure definitions
- Button-press start, final score display

---

## Original Examples

### `hello_build.py`

The simplest possible build script (old API style).

### `strict_build.py`

Same as `hello_build.py` with strict-verified mode enabled.

### `python_first_robot.py`

Standard robot movement sequence — python-first style.

### `python_first_defaults.py`

Default parameter values and keyword arguments for `@robot.proc`.

### `python_first_return.py`

Return values from `@robot.proc` procedures.
