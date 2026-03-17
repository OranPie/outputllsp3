# SPIKE Python ↔ ScratchWrapper Mapping

This table maps official SPIKE Python API calls to the corresponding
`ScratchWrapper` opcode invocations and `API` facade calls.

---

## Motor Control

| SPIKE Python | Opcode | API Facade |
|---|---|---|
| `motor.run(port, speed)` | `flippermotor_motorRun` | `api.motor.run(port, speed)` |
| `motor.stop(port)` | `flippermotor_motorStop` | `api.motor.stop(port)` |
| `motor.reset_relative_position(port, pos)` | `flippermoremotor_motorSetDegreeCounted` | `api.motor.set_relative_position(port, pos)` |
| `motor.get_relative_position(port)` | `flippermoremotor_motorGetDegreeCounted` | `api.motor.relative_position(port)` |

---

## Drive-Base (Motor Pair)

| SPIKE Python | Opcode | API Facade |
|---|---|---|
| `motor_pair.move(lspeed, rspeed)` | `flippermoremove_startDualSpeed` | `api.move.dual_speed(left, right)` |
| `motor_pair.stop()` | `flippermove_stopMove` | `api.move.stop()` |
| `motor_pair.set_pair(left, right)` | `flippermove_setMovementPair` | `api.move.pair(pair)` |

---

## Timing

| SPIKE Python | Opcode | API Facade |
|---|---|---|
| `runloop.sleep_ms(n)` | `flippercontrol_waitForMS` | `api.wait.ms(n)` |
| (seconds) | `control_wait` | `api.wait.seconds(n)` |

---

## Sensors

| SPIKE Python | Opcode | API Facade |
|---|---|---|
| `motion_sensor.reset_yaw()` | `flipperorientation_resetOrientation` | `api.sensor.reset_yaw()` |
| `motion_sensor.tilt_angles()[0] / 10.0` | `flipperorientation_getFakeYaw` | `api.sensor.angle()` |

---

## Hub Display

| SPIKE Python | Opcode | API Facade |
|---|---|---|
| `hub.light_matrix.show_image(img)` | `flipperdisplay_displayImage` | *(use wrapper.invoke)* |
| `hub.speaker.beep(pitch, dur)` | `flipperDisplay_playSound` | *(use wrapper.invoke)* |

---

## Notes

- Not all SPIKE Python calls have a corresponding Scratch opcode.  The SPIKE
  app uses a different execution model for Python programs vs. Scratch programs.
- This mapping covers the *intersection* used by the AST transpiler; full
  SPIKE Python semantics are not reproduced by the Scratch block graph.
- For a complete list of known opcodes, run `outputllsp3 verified-opcodes`.
