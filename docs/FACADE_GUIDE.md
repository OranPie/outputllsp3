# Facade API Guide

This guide covers the high-level facades in `api.py` and `flow.py` — the
recommended way to build LLSP3 projects programmatically.

---

## Overview

The `API` class aggregates all sub-facades and is the main object passed to
`build(project, api, ns)` functions:

```python
from outputllsp3 import API, LLSP3Project

project = LLSP3Project('ok.llsp3', 'strings.json')
api = API(project)

api.flow.start(
    api.move.set_pair("AB"),
    api.robot.straight_cm(30, 420),
    api.robot.turn_deg(90, 260),
)

project.save('out.llsp3')
```

---

## Sub-facades

### `api.vars` — Variables

```python
api.vars.add('speed', 420)          # declare with initial value
api.vars.ensure('speed', 420)       # declare if not already declared
api.vars.get('speed')               # reporter block
api.vars.set('speed', 300)          # set-variable block
api.vars.change('speed', -50)       # change-variable block
```

Use `namespace='myns'` to scope variables:

```python
api.vars.add('x', 0, namespace='main')  # → "main__x"
```

Use `raw=True` to use the exact variable name without namespace prefix:

```python
api.vars.add('__flag', 0, raw=True)
```

---

### `api.lists` — Lists

```python
api.lists.add('items', [])             # declare
api.lists.append('items', 'hello')     # append block
api.lists.clear('items')               # clear block
api.lists.length('items')              # length reporter
api.lists.item('items', index)         # item reporter (1-based)
api.lists.contains('items', 'hello')   # contains reporter
api.lists.setitem('items', index, val) # replace block (1-based)
api.lists.delete('items', index)       # delete block (1-based)
api.lists.insert('items', index, val)  # insert block (1-based)
```

---

### `api.ops` — Operators

```python
api.ops.add(a, b)        # a + b
api.ops.sub(a, b)        # a - b
api.ops.mul(a, b)        # a * b
api.ops.div(a, b)        # a / b
api.ops.mod(a, b)        # a mod b
api.ops.abs(a)           # |a|
api.ops.round(a)         # round(a)
api.ops.pow(a, b)        # a ^ b

api.ops.eq(a, b)         # a = b   (boolean)
api.ops.lt(a, b)         # a < b   (boolean)
api.ops.gt(a, b)         # a > b   (boolean)
api.ops.and_(a, b)       # a AND b (boolean)
api.ops.or_(a, b)        # a OR b  (boolean)
api.ops.not_(a)          # NOT a   (boolean)

api.ops.join(a, b)       # string join
api.ops.length(s)        # string length
api.ops.contains(s, sub) # string contains
```

---

### `api.wait` — Wait blocks

```python
api.wait.seconds(2.5)    # wait 2.5 seconds
api.wait.ms(500)         # wait 500 milliseconds
```

---

### `api.move` — Drive-base movement

```python
api.move.set_pair("AB")           # set motor pair
api.move.dual_speed(left, right)  # set dual speed
api.move.stop()                   # stop drive
api.move.pair(pair_str)           # set motor pair block
```

---

### `api.robot` — High-level robot helpers (PID runtime)

```python
runtime = api.drivebase.install_pid_runtime(
    motor_pair='AB',
    wheel_diameter_mm=62.4,
    left_dir=1,
    right_dir=-1,
)

api.robot.straight_cm(30, 420)   # move 30 cm at speed 420
api.robot.straight_deg(360, 420) # move 360 motor-degrees at speed 420
api.robot.turn_deg(90, 260)      # turn 90° at speed 260
api.robot.pivot_left_deg(90, 220)
api.robot.pivot_right_deg(90, 220)
api.robot.stop()
```

---

### `api.flow` — Control flow

See [FlowBuilder](#flowbuilder) below.

---

### Short aliases

`API` exposes short aliases for interactive use:

| Alias | Full name |
|-------|-----------|
| `api.v` | `api.vars` |
| `api.o` | `api.ops` |
| `api.m` | `api.move` |
| `api.s` | `api.sensor` |
| `api.f` | `api.flow` |
| `api.db` | `api.drivebase` |
| `api.e` | `api.enums` |

---

## FlowBuilder

`api.flow` is a `FlowBuilder` instance.  All methods return block IDs.

### `start(*body)`

Attach a `whenProgramStarts` hat block:

```python
api.flow.start(
    api.robot.straight_cm(30, 420),
    api.wait.seconds(0.5),
)
```

### `procedure(name, args, *body, defaults=None)`

Define a custom procedure:

```python
api.flow.procedure(
    'move_square',
    ['side', 'speed'],
    *[api.robot.straight_cm(api.project.arg('side'), api.project.arg('speed'))],
    defaults=[20, 420],
)
```

### `call(name, *args)`

Emit a procedure call:

```python
api.flow.call('move_square', 30, 350)
```

### `if_(cond, *body)` / `if_else(cond, *then_, *else_)`

```python
api.flow.if_(api.ops.gt(speed, 300),
    api.robot.straight_cm(20, speed),
)
```

### `repeat(times, *body)`

```python
api.flow.repeat(4,
    api.robot.straight_cm(20, 420),
    api.robot.turn_deg(90, 260),
)
```

### `repeat_until(cond, *body)`

```python
api.flow.repeat_until(
    api.ops.gt(api.vars.get('count'), 10),
    api.vars.change('count', 1),
)
```

### `chain(parent, *body)`

Attach a sequence of blocks after a parent:

```python
start = api.flow.start()
api.flow.chain(start, api.robot.straight_cm(20, 420))
```

### `comment(text, …)`

Attach a floating comment to a block:

```python
api.flow.comment('This is a test', api.flow.start())
```

---

## Namespace Scoping

Use `api.namespace(prefix)` as a context manager to scope all variable
operations to a prefix:

```python
with api.namespace('mission1'):
    api.vars.add('dist', 30)    # declares "mission1__dist"
    api.vars.get('dist')         # reads  "mission1__dist"
```
