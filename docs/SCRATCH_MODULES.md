# Scratch Module Coverage

This document lists the Scratch / SPIKE-Scratch extension modules that
`outputllsp3` currently covers, with their primary opcodes.

Run `outputllsp3 verified-opcodes --full` to see the complete list of
verified opcodes extracted from the bundled `block_reference.llsp3`.

---

## Core Scratch Modules

These opcodes belong to the standard Scratch 3 VM and are always available.

### `control` — Program flow

| Opcode | Description |
|--------|-------------|
| `control_wait` | Wait N seconds |
| `control_repeat` | Repeat N times |
| `control_if` | If … do … |
| `control_if_else` | If … do … else … |
| `control_repeat_until` | Repeat until condition |
| `control_stop` | Stop (this script / all / other) |

### `operator` — Arithmetic and logic

| Opcode | Description |
|--------|-------------|
| `operator_add` / `subtract` / `multiply` / `divide` | Arithmetic |
| `operator_mod` | Modulo |
| `operator_mathop` | Math functions (abs, round, sqrt, …) |
| `operator_random` | Pick random N to M |
| `operator_equals` / `lt` / `gt` | Comparison |
| `operator_and` / `or` / `not` | Boolean logic |
| `operator_join` / `letter_of` / `length` | String ops |
| `operator_contains` | String contains |

### `data` — Variables and lists

| Opcode | Description |
|--------|-------------|
| `data_variable` | Variable reporter |
| `data_setvariableto` | Set variable |
| `data_changevariableby` | Change variable |
| `data_listcontents` | List reporter |
| `data_addtolist` | Add to list |
| `data_deleteoflist` | Delete item |
| `data_insertatlist` | Insert at index |
| `data_replaceitemoflist` | Replace item |
| `data_itemoflist` | Item reporter |
| `data_itemnumoflist` | Item number reporter |
| `data_lengthoflist` | Length reporter |
| `data_listcontainsitem` | Contains reporter |

### `procedures` — Custom blocks

| Opcode | Description |
|--------|-------------|
| `procedures_definition` | Custom block hat |
| `procedures_prototype` | Signature declaration |
| `procedures_call` | Call block |
| `argument_reporter_string_number` | Parameter reporter |

---

## SPIKE Extension Modules

These opcodes are injected by the SPIKE app as Scratch 3 extensions.

### `flipperevents` — Program triggers

| Opcode | Description |
|--------|-------------|
| `flipperevents_whenProgramStarts` | When program starts (hat) |

### `flippermove` — Drive-base (motor pair)

| Opcode | Description |
|--------|-------------|
| `flippermove_setMovementPair` | Set motor pair (A–F) |
| `flippermove_stopMove` | Stop drive |

### `flippermoremove` — Drive-base advanced

| Opcode | Description |
|--------|-------------|
| `flippermoremove_startDualSpeed` | Set dual speed (left, right) |
| `flippermoremove_startDualPower` | Set dual power (left, right) |

### `flippermotor` — Individual motor

| Opcode | Description |
|--------|-------------|
| `flippermotor_motorRun` | Run motor at speed |
| `flippermotor_motorStop` | Stop motor |

### `flippermoremotor` — Motor advanced

| Opcode | Description |
|--------|-------------|
| `flippermoremotor_motorSetDegreeCounted` | Set relative position |
| `flippermoremotor_motorGetDegreeCounted` | Get relative position |

### `flipperorientation` — IMU / orientation

| Opcode | Description |
|--------|-------------|
| `flipperorientation_resetOrientation` | Reset yaw |
| `flipperorientation_getFakeYaw` | Read yaw angle |

### `flippercontrol` — SPIKE timing

| Opcode | Description |
|--------|-------------|
| `flippercontrol_waitForMS` | Wait N milliseconds |

---

## Module Coverage Summary

| Module | Covered in API | Coverage level |
|--------|---------------|----------------|
| `control` | ✓ `api.flow.*` | Full |
| `operator` | ✓ `api.ops.*` | Full |
| `data` | ✓ `api.vars.*`, `api.lists.*` | Full |
| `procedures` | ✓ `api.flow.procedure/call` | Full |
| `flipperevents` | ✓ `api.flow.start` | Full |
| `flippermove` | ✓ `api.move.*` | Full |
| `flippermoremove` | ✓ `api.move.dual_speed/power` | Full |
| `flippermotor` | ✓ `api.motor.run/stop` | Full |
| `flippermoremotor` | ✓ `api.motor.relative_position` | Full |
| `flipperorientation` | ✓ `api.sensor.reset_yaw/angle` | Full |
| `flippercontrol` | ✓ `api.wait.ms` | Full |
| `flipperdisplay` | Partial (via `wrapper.invoke`) | Partial |
| `flipperDisplay` (sound) | Partial (via `wrapper.invoke`) | Partial |
