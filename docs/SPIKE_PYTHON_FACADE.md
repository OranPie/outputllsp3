# SpikePython Facade Reference

`SpikePythonAPI` mirrors the official SPIKE Python library API so that
programs written for the SPIKE hub can be partially compiled to Scratch blocks
by `transpile_python_source`.

---

## Overview

```python
from outputllsp3 import SpikePythonAPI, LLSP3Project

project = LLSP3Project('ok.llsp3', 'strings.json')
api_spike = SpikePythonAPI(project)
```

Access sub-APIs via attributes:

```python
api_spike.hub          # hub-level helpers
api_spike.motor        # individual motor control
api_spike.motor_pair   # drive-base control
```

---

## `SpikePythonAPI.hub`

### `hub.light_matrix`

```python
hub.light_matrix.show_image(image)  # display a built-in image
hub.light_matrix.set_pixel(x, y, brightness)
hub.light_matrix.off()
```

### `hub.speaker`

```python
hub.speaker.beep(pitch, duration_ms)
hub.speaker.stop()
```

### `hub.motion_sensor`

```python
hub.motion_sensor.reset_yaw()       # reset yaw angle to 0
hub.motion_sensor.get_yaw_angle()   # read current yaw
```

---

## `SpikePythonAPI.motor`

```python
motor.run(port, speed)             # run motor at speed
motor.stop(port)                   # stop motor
motor.get_position(port)           # read absolute position
motor.get_speed(port)              # read current speed
motor.reset_relative_position(port, position)
motor.get_relative_position(port)
```

---

## `SpikePythonAPI.motor_pair`

```python
motor_pair.move(left_speed, right_speed)   # move both motors
motor_pair.stop()
```

---

## Supported Patterns in AST Transpiler

The AST transpiler understands these patterns from the official SPIKE Python API:

| Python call | Scratch output |
|------------|----------------|
| `runloop.sleep_ms(n)` | `wait n ms` |
| `motion_sensor.reset_yaw()` | `reset yaw` |
| `motor.reset_relative_position(port, 0)` | `set relative position` |
| `motor.relative_position(port)` | relative position reporter |
| `motion_sensor.tilt_angles()[0] / 10.0` | yaw angle reporter |

For patterns not yet in the mapping, the AST transpiler emits a
`wait 0 seconds` no-op with a compile note.

---

## Limitations

The SPIKE Python API is significantly richer than what the AST transpiler
currently models.  Only the subset documented here produces meaningful Scratch
blocks.  For full SPIKE Python program support, use the python-first mode
(`@robot.proc` / `@run.main`) which has higher-level abstractions.
