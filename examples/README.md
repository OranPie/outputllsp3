# Examples

This directory contains example programs demonstrating different ways to use
`outputllsp3`.

---

## Running an Example

All examples compile to `.llsp3` files that can be uploaded to the LEGO
Education SPIKE app.

### Python-first examples (recommended)

```bash
outputllsp3 build-python examples/python_first_robot.py --out robot.llsp3
outputllsp3 build-python examples/python_first_defaults.py --out defaults.llsp3
outputllsp3 build-python examples/python_first_return.py --out return.llsp3
```

### Build-script examples

```bash
outputllsp3 build examples/hello_build.py --out hello.llsp3
outputllsp3 build examples/strict_build.py --out strict.llsp3
```

---

## Example Files

### `hello_build.py`

The simplest possible build script.  Demonstrates:

- `build(project, api, ns)` entry point
- `api.flow.start(…)` to attach a program-start hat
- `api.robot` helpers for straight and turn movement

### `strict_build.py`

Same as `hello_build.py` but compiled with strict-verified mode enabled.
Demonstrates:

- `project.set_strict_verified(True)` to enable opcode validation

### `python_first_robot.py`

A standard robot movement sequence using the python-first style.  Demonstrates:

- `@run.main` decorator
- `robot.use_pair(port.B, port.A)` to configure the drive-base
- `robot.forward_cm`, `robot.turn_deg`, `robot.stop`

### `python_first_defaults.py`

Demonstrates default parameter values and keyword arguments for `@robot.proc`
procedures.  Demonstrates:

- `@robot.proc` with default values: `def move_square(side=20, speed=420):`
- Calling with all defaults: `move_square()`
- Overriding positional args: `move_square(30)`
- Keyword arguments: `move_square(speed=350)`
- Mixed keyword and positional: `clamp(200, hi=80)`

### `python_first_return.py`

Demonstrates return values from `@robot.proc` procedures.  Demonstrates:

- `@robot.proc` with `return value`
- Assigning the result: `result = my_proc(args)`
- Using return inside a loop (exits the loop immediately)
