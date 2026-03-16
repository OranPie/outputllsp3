# LEGO Education SPIKE App — Scratch/Blockly & llsp3 Deep Technical Reference

> **Reverse-engineered from** `/Applications/SPIKE.app` (macOS)  
> **Primary source:** `Contents/Resources/platform/web/static/js/index.cd95f90d.js` (6.7 MB minified)  
> **App version string (wm / protocol version):** `18.0.1`

---

## TABLE OF CONTENTS

1. [App Architecture Overview](#1-app-architecture-overview)
2. [.llsp3 File Format](#2-llsp3-file-format)
3. [Scratch Block Execution Architecture](#3-scratch-block-execution-architecture)
4. [Complete Opcode Tables](#4-complete-opcode-tables)
5. [RPC Wire Protocol — scratch.* Methods](#5-rpc-wire-protocol--scratch-methods)
6. [LWP Binary Protocol (BLE)](#6-lwp-binary-protocol-ble)
7. [All Enum Definitions](#7-all-enum-definitions)
8. [Sensor System](#8-sensor-system)
9. [Tunnel Protocol (MicroPython ↔ JS)](#9-tunnel-protocol-micropython--js)
10. [Python Code Generator](#10-python-code-generator)
11. [Block XML Format](#11-block-xml-format)
12. [Native WebSocket API](#12-native-websocket-api)
13. [Horizontal (Icon Blocks) Mode](#13-horizontal-icon-blocks-mode)
14. [Default Constants & Clamping](#14-default-constants--clamping)

---

## 1. App Architecture Overview

### Process Topology

```
┌─────────────────────────────────────────────────────────────────┐
│  SPIKE.app (macOS Electron-like: Swift native shell)            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  WKWebView  (webkit)                                      │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  React/Redux SPA  (platform/web/static/js/*.js)    │  │   │
│  │  │                                                    │  │   │
│  │  │  Scratch VM  <->  Block UI (Blockly-derived)       │  │   │
│  │  │       |                                            │  │   │
│  │  │  E0 (execution engine)                             │  │   │
│  │  │       |  {method, params} RPC objects              │  │   │
│  │  │  cge (WebSocket client)                            │  │   │
│  │  └────────────────┬───────────────────────────────────┘  │   │
│  └───────────────────│───────────────────────────────────────┘   │
│                      │  ws://localhost:2846  (PocketSocket)       │
│  ┌───────────────────▼───────────────────────────────────────┐   │
│  │  Swift WebSocket Server                                    │   │
│  │  ┌──────────────┐   ┌──────────────────────────────────┐  │   │
│  │  │ USB HID/CDC  │   │ CoreBluetooth BLE                 │  │   │
│  │  │ (SPIKE Prime)│   │ (SPIKE Essential / Prime BLE)     │  │   │
│  │  └──────┬───────┘   └──────────────┬───────────────────┘  │   │
│  └─────────│──────────────────────────│─────────────────────┘   │
└────────────│──────────────────────────│─────────────────────────┘
             │                          │
             v USB Serial / HID         v BLE GATT
       SPIKE Prime Hub           SPIKE Essential Hub
       (MicroPython)              (LWP3 over BLE)
```

### Key Source Files

| File | Size | Purpose |
|------|------|---------|
| `platform/web/static/js/index.cd95f90d.js` | 6.7 MB | Main bundle: all block code generators, execution engine, RPC protocol |
| `platform/web/static/js/scratch-vendor.c8a4a5e0.js` | 4.5 MB | Scratch VM engine, block type system, sb3 serialization |
| `platform/web/static/js/165.6f477666.js` | async chunk | Additional extension logic |
| `platform/hosts/appconfig.json` | 3 KB | WebSocket port (2846), AWS, CMS config |
| `platform/web/flipper-hub/flash/*.py` | — | MicroPython hub runtime |
| `platform/content/blt*.json` | up to 2 MB | Lesson content with embedded Scratch XML |

### Webpack Module Map (key modules)

| Module ID | Variable | Contents |
|-----------|----------|----------|
| 88590 | `A` | Main protocol re-export: all enums, tunnel messages, LPF2Sensor |
| 69253 | `wt` | Tunnel protocol message definitions (IDs + formats) |
| 37402 | `U` | Tunnel message field type builders (Em, BX, w_, Z_, Xg, vE...) |
| 41495 | — | Core tunnel messages: Assertion, ProgramAttributes, LatestTunnelValueRequest/Response |
| 42907 | `lt` | All enum wire values: MotorDirection, MotorUnit, PressureOption, etc. |
| 80602 | `et` | HubType, FlipperPhysicalPort, FlipperVirtualPort, SelectionMode |
| 10639 | `po` | DisplayImage, GraphType, LineVariant, SplitMode, YAxisMode |
| 21467 | `k` | `Opcode` enum (all block opcode string keys) |
| 83295 | `I/k` | `OpcodeHorizontal` enum + `opcodesCanRunWithoutHubHorizontal` set |
| 79967 | `h` | Re-exports of all above enums under unified namespace |
| 5157 | — | Version string `"18.0.1"` (exported as `i8`) |

---

## 2. .llsp3 File Format

An `.llsp3` file is a **ZIP archive** (standard deflate). Internal structure:

```
project.llsp3  (ZIP)
├── manifest.json          # required — project metadata
├── projectbody.json       # required — Scratch sb3 project OR Python source
├── monitors.json          # optional — only if manifest.state.hasMonitors = true
├── extraFiles/
│   └── *.json             # optional files listed in manifest.extraFiles[]
└── icon.svg               # project thumbnail
```

### manifest.json Schema

```jsonc
{
  "type": "llsp3",
  "appType": "scratch",        // "scratch" | "python" | "words" | "icons"
  "id": "abc123def456",        // nanoid-12
  "name": "My Project",
  "slotIndex": 0,              // hub memory slot 0–9
  "created": 1700000000000,    // Unix ms
  "lastsaved": 1700000100000,
  "size": 12345,
  "workspaceX": 0,
  "workspaceY": 0,
  "zoomLevel": 0.75,
  "hardware": {
    "id": "flipper",           // hub type string (see table below)
    "type": "flipper"
  },
  "state": { "hasMonitors": false },
  "extensions": ["flippermotor","flippersensors"],
  "extraFiles": [],
  "autoDelete": false,
  "showAllBlocks": false,
  "version": "3.0.0",
  "progress": { "total": 5, "completed": 2 }
}
```

### Hub Type Strings

| manifest string | Internal JS enum key | Physical device |
|-----------------|----------------------|-----------------|
| `"flipper"` | `HubType.Flipper` | SPIKE Prime (USB) |
| `"flipper-pt"` | `HubType.FlipperPT` | SPIKE Prime (pass-through) |
| `"essential"` | (Essential) | SPIKE Essential |
| `"flipper-ble"` | `HubType.Gecko` | SPIKE Prime over BLE |
| `"gecko-atlantis"` | `HubType.GeckoAtlantis` | SPIKE Prime 3 |

### projectbody.json — Scratch Mode (sb3-compatible)

```jsonc
{
  "targets": [ { /* Stage */ }, { /* Sprite */ } ],
  "extensions": ["flippermotor","flippersensors"],
  "meta": { "semver": "3.0.0" },
  "monitors": []
}
```

#### Target Object

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | nanoid-20 |
| `isStage` | bool | true for stage target |
| `name` | string | "Stage" or "Sprite1" |
| `blocks` | object | map of blockId → block |
| `broadcasts` | object | broadcast name → id |
| `variables` | object | varId → [name, value] |
| `lists` | object | listId → [name, value[]] |
| `costumes` | array | always [] in SPIKE |
| `sounds` | array | always [] in SPIKE |
| `volume` | number | always 100 |
| `currentCostume` | number | always 0 |

#### Block Object

| Field | Type | Notes |
|-------|------|-------|
| `opcode` | string | e.g. `"flippermotor_motorTurnForDirection"` |
| `next` | string\|null | next block in stack |
| `parent` | string\|null | parent block (null = top-level) |
| `inputs` | object | inputName → [type, blockId, shadowId?] |
| `fields` | object | fieldName → [value, null] |
| `shadow` | bool | true = shadow/default value block |
| `topLevel` | bool | true = hat block or disconnected block |
| `x`, `y` | number | workspace coords (topLevel only) |

**Input type codes:** `1`=shadow only · `2`=block only · `3`=block+shadow fallback

### projectbody.json — Python Mode

```jsonc
{ "main": "import hub\n# full MicroPython source\n" }
```


---

## 3. Scratch Block Execution Architecture

### Class Hierarchy

```
Ko (base connection class)
└── E0 (main block execution engine — extends Ko)
    ├── motorBlock(port, targetId, fn)
    ├── noArgBlock(targetId, fn)
    ├── valueBlock(targetId, fn)
    └── singleMotorCommand(...)

Gw (OpcodeExtensions — stop handlers per extension)
jw = { opcode: handlerFn, ... }  // dispatch table
```

### Execution Flow

```
Scratch block triggered (hat/event or user click)
        |
        v
jw[opcode](blockArgs, blockContext, E0instance)
        |
        v
Returns { method: "scratch.XYZ", params: {...} }
        |
        v
E0.connection.sendRequest(hubId, method, params)
        |
        v
cge.send(method, { values: params, version: "18.0.1" })
        |
        v
WebSocket frame → ws://localhost:2846
        |
        v
Swift native server → USB/BLE → hub
```

### E0 Helper Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `motorBlock` | `(port, targetId, fn)` | Expands multi-port selectors ("AB" → [A,B]) → parallel motor commands |
| `noArgBlock` | `(targetId, fn)` | Fire-and-forget — calls fn, sends result, ignores return value |
| `valueBlock` | `(targetId, fn)` | Executes fn, sends RPC, returns sensor value to Scratch |
| `singleMotorCommand` | `(port, targetId, fn)` | Passes `{port, speed, stall, stop}` state to fn, tracks motor status |
| `whenSensorChanged` | `(targetId, port, type, mode, delta)` | Subscribes to sensor stream via `scratch.when_sensor_changed` |
| `clearDisplay` | `(targetId)` | Issues `scratch.display_clear` |
| `setMotorAcceleration` | `(targetId, port, accel, decel)` | Stores acceleration profile in local state |
| `setMoveAcceleration` | `(targetId, accelStr)` | Parses `"4000 4000"` format string → `{acceleration, deceleration}` |
| `setMovePair` | `(targetId, portL, portR)` | Stores left/right motor port assignment |
| `getMoveCalibration` | `(targetId)` | Returns cm-per-rotation calibration value |
| `getMotorAcceleration` | `(targetId, port)` | Returns `{acceleration: N, deceleration: N}` for a port |

### State Objects Tracked by E0

| State map key | Default | Description |
|---------------|---------|-------------|
| `motorAcceleration["targetId-port"]` | — | `{acceleration, deceleration}` per port |
| `moveAcceleration["targetId"]` | — | `{acceleration, deceleration}` for move pair |
| `motorStall["targetId-port"]` | `true` | stall detection enabled per port |
| `motorStop["targetId-port"]` | `MotorStop.Brake` | stop method per port |
| `moveStop["targetId"]` | `MotorStop.Brake` | stop method for move pair |
| `movePair["targetId"]` | `["A","B"]` | Left/right motor port assignment |
| `moveSpeed["targetId"]` | 50 | current move speed (%) |
| `moveCalibration["targetId"]` | 17.5 (Flipper), 13.5 (Gecko) | cm per rotation |
| `motorLastStatus["targetId-port"]` | 0 | last motor completion status |


---

## 4. Complete Opcode Tables

### 4.1 `flippermotor` Extension (SPIKE Prime motors)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flippermotor_motorTurnForDirection` | command | Run motor for time/degrees/rotations in direction |
| `flippermotor_motorGoDirectionToPosition` | command | Go to absolute position in direction |
| `flippermotor_motorGoToRelativePosition` | command | (flippermoremotor) Go to relative position |
| `flippermotor_motorSetDegreeCounted` | command | (flippermoremotor) Set degree counted |
| `flippermotor_motorStartDirection` | command | Start motor running in direction indefinitely |
| `flippermotor_motorStop` | command | Stop motor with stop method |
| `flippermotor_motorSetSpeed` | command | Set motor default speed |
| `flippermotor_absolutePosition` | reporter | Read absolute position (-180 to 180 deg) |
| `flippermotor_speed` | reporter | Read current speed (%) |
| `flippermotor_motorSetStopMethod` | command | Set stop method (Float/Brake/Hold) |
| `flippermotor_motorSetAcceleration` | command | Set acceleration/deceleration profile |
| `flippermotor_motorStartPower` | command | Start motor with raw PWM power |

**Fields:**

| Field name | Type | Values |
|-----------|------|--------|
| `PORT` | shadow | `"A"` `"B"` `"C"` `"D"` `"E"` `"F"` — or multi: `"AB"`, `"CD"` |
| `DIRECTION` | field | `"forward"` `"back"` `"clockwise"` `"counterclockwise"` |
| `VALUE` | input | number — degrees/seconds/rotations |
| `UNIT` | field | `"degrees"` `"seconds"` `"rotations"` |
| `SPEED` | input | number -100..100 |
| `STOP` | field | `"0"` (Float) `"1"` (Brake) `"2"` (Hold) |
| `ACCELERATION` | input | `"3000 3000"` (accel_ms decel_ms) |
| `POSITION` | input | number -T0..T0 (T0 = 3,600,000) |
| `STALL` | field | `"true"` `"false"` |
| `POWER` | input | number -100..100 |

### 4.2 `flippermove` Extension (movement pair)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flippermove_move` | command | Move pair for distance/time/rotations |
| `flippermove_steer` | command | Steer movement (steering + speed) |
| `flippermove_stopMove` | command | Stop movement pair |
| `flippermove_startDualSpeed` | command | Start both motors at independent speeds |
| `flippermove_startSteer` | command | Start steering continuously |
| `flippermove_startMove` | command | Start movement pair continuously |
| `flippermove_setMovementPair` | command | Set which ports form the pair |
| `flippermove_movementSpeed` | reporter | Current movement speed |
| `flippermove_setDistance` | command | Set wheel diameter calibration |
| `flippermove_movementSetStopMethod` | command | Set stop method for pair |
| `flippermove_movementSetAcceleration` | command | Set acceleration for pair |

### 4.3 `flippersensors` Extension

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flippersensors_color` | reporter | Color sensor: color name |
| `flippersensors_rawColor` | reporter | Color sensor: raw R/G/B value |
| `flippersensors_iscolor` | Boolean | Color sensor: is color? |
| `flippersensors_reflectivity` | reporter | Color sensor: reflectivity % |
| `flippersensors_isReflectivity` | Boolean | Color sensor: is reflectivity? |
| `flippersensors_force` | reporter | Force sensor: newtons or % |
| `flippersensors_isPressed` | Boolean | Force sensor: is pressed? |
| `flippersensors_distance` | reporter | Distance sensor: cm/inches/% |
| `flippersensors_isDistance` | Boolean | Distance sensor: is at distance? |
| `flippersensors_colorValue` | reporter | Color sensor raw numeric value |

### 4.4 `flipperdisplay` Extension

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flipperdisplay_lightDisplayImageOn` | command | Show image on 5x5 LED matrix |
| `flipperdisplay_lightDisplayImageOnForTime` | command | Show image for N seconds |
| `flipperdisplay_lightDisplayText` | command | Scroll text on 5x5 LED matrix |
| `flipperdisplay_lightDisplayOff` | command | Turn off 5x5 LED matrix |
| `flipperdisplay_lightDisplaySetBrightness` | command | Set pixel brightness |
| `flipperdisplay_lightDisplaySetPixel` | command | Set individual pixel |
| `flipperdisplay_lightDisplayRotate` | command | Rotate display content |
| `flipperdisplay_lightDisplaySetOrientation` | command | Set display orientation |
| `flipperdisplay_lightColorMatrixImageOn` | command | Color matrix: show image |
| `flipperdisplay_lightColorMatrixImageOnForTime` | command | Color matrix: show for time |
| `flipperdisplay_lightColorMatrixOff` | command | Color matrix: off |
| `flipperdisplay_lightColorMatrixSetBrightness` | command | Color matrix: brightness |
| `flipperdisplay_lightColorMatrixSetPixel` | command | Color matrix: set pixel |
| `flipperdisplay_lightColorMatrixRotate` | command | Color matrix: rotate |
| `flipperdisplay_lightColorMatrixSetOrientation` | command | Color matrix: orientation |

### 4.5 `flipperevents` Extension (hat blocks)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flipperevents_whenProgramStarts` | hat | Runs when program starts |
| `flipperevents_whenCondition` | hat | Runs when condition becomes true |
| `flipperevents_whenColor` | hat | Runs when color sensor sees color |
| `flipperevents_whenNearOrFar` | hat | Runs when distance changes threshold |
| `flipperevents_whenDistance` | hat | Runs when distance comparator is met |
| `flipperevents_whenPressed` | hat | Runs when force sensor is pressed |
| `flipperevents_whenButton` | hat | Runs when hub button pressed/released |
| `flipperevents_whenOrientation` | hat | Runs when hub orientation changes |
| `flipperevents_whenGesture` | hat | Runs on gesture (tapped, shake, etc.) |
| `flipperevents_whenTimer` | hat | Runs when timer >= value |
| `flipperevents_timer` | reporter | Current timer value |
| `flipperevents_resetTimer` | command | Reset timer to 0 |
| `flipperevents_whenBroadcast` | hat | Receives broadcast |

### 4.6 `flipperlight` Extension (center button LED)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flipperlight_centerButtonLight` | command | Set center button LED color |
| `flipperlight_ultrasonicLightUp` | command | Light up ultrasonic sensor LEDs |
| `flipperlight_buttonIsPressed` | Boolean | Is hub button pressed? |

### 4.7 `flippersound` Extension

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flippersound_beepForTime` | command | Play beep for time at note/volume |
| `flippersound_beep` | command | Play beep until stopped |
| `flippersound_stopSound` | command | Stop current sound |
| `flippersound_playSound` | command | Play sound file (async) |
| `flippersound_playSoundUntilDone` | command | Play sound file (wait for done) |

### 4.8 `flipperimu` Extension (IMU / orientation)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flipperimu_orientation` | reporter | Hub orientation (string) |
| `flipperimu_orientationAxis` | reporter | Axis angle (pitch/roll/yaw) |
| `flipperimu_setOrientation` | command | Set reference orientation |
| `flipperimu_isorientation` | Boolean | Is hub in orientation? |
| `flipperimu_isMotion` | Boolean | Is hub in motion? |
| `flipperimu_motion` | reporter | Motion gesture name |
| `flipperimu_acceleration` | reporter | Axis acceleration (m/s²) |
| `flipperimu_angularVelocity` | reporter | Axis angular velocity (deg/s) |
| `flipperimu_resetYaw` | command | Reset yaw axis to 0 |

### 4.9 `flippermore` Extension (misc hub operations)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flippermore_port` | reporter | Raw port sensor value |
| `flippermore_stopOtherStacks` | command | Stop all other running scripts |
| `flippermore_assert` | command | Assert (testing only) |
| `flippermore_assertValue` | command | Assert value equals expected |
| `flippermore_assertRange` | command | Assert value in range |
| `flippermore_assertTolerance` | command | Assert value within tolerance |
| `flippermore_assertNormalizedTolerance` | command | Assert normalized tolerance |
| `flippermore_passTest` | command | Signal test passed |
| `flippermore_assertLastTunnelMessage` | command | Assert last tunnel message |
| `flippermore_assertLastTunnelMessageType` | command | Assert last tunnel message type |

### 4.10 `flippermoremotor` Extension (advanced motor)

| Opcode | Block type | Description |
|--------|-----------|-------------|
| `flippermoremotor_motorGoToRelativePosition` | command | Go to relative position |
| `flippermoremotor_motorSetDegreeCounted` | command | Set degree-counted value |

### 4.11 `Opcode` Enum — Full Word Block Opcode Keys

These string keys are used as JavaScript object property names in `jw` dispatch table and also appear in sb3 JSON.

```
buttonIsPressed          lightDisplayImageOn         lightDisplayImageOnForTime
lightDisplayText         lightDisplayOff             lightDisplaySetBrightness
lightDisplaySetPixel     lightDisplayRotate          lightDisplaySetOrientation
lightColorMatrixImageOn  lightColorMatrixImageOnForTime  lightColorMatrixOff
lightColorMatrixSetBrightness  lightColorMatrixSetPixel  lightColorMatrixRotate
lightColorMatrixSetOrientation  centerButtonLight     ultrasonicLightUp
motorAbsolutePosition (="absolutePosition")          motorSetSpeed
motorSetAcceleration     motorDirection (="direction")  motorPosition (="position")
motorPower (="power")    motorTurnForDirection        motorStop
motorSetStopMethod       motorStartDirection          motorGoDirectionToPosition
motorGoToRelativePosition  motorSetDegreeCounted      motorSpeed (="speed")
motorStartPower          beepForTime                  beep
stopSound                playSound                    playSoundUntilDone
color                    rawColor                     iscolor (="isColor")
resetYaw                 reflectivity                 isReflectivity
force                    isPressed                    distance
isDistance               orientation                  orientationAxis
setOrientation           isorientation (="isorientation")  isMotion (="ismotion")
motion                   colorValue                   port
whenNearOrFar            whenDistance                 whenCondition
whenColor                whenGesture                  whenPressed
whenButton               whenOrientation              whenProgramStarts
whenTimer                timer                        resetTimer
acceleration             angularVelocity              move
steer                    stopMove                     movementSetStopMethod
movementSetAcceleration  setMovementPair              movementSpeed
setDistance              startDualSpeed               startSteer
startMove                stop                         isInBetween
stopOtherStacks          assert                       assertValue
assertRange              assertTolerance              assertNormalizedTolerance
passTest                 assertLastTunnelMessage      assertLastTunnelMessageType
```


---

## 5. RPC Wire Protocol — scratch.* Methods

**Protocol version:** `"18.0.1"` (sent in every request envelope)

**WebSocket endpoint:** `ws://localhost:2846`

**Envelope format:**
```jsonc
// Request (JS -> Swift):
{
  "method": "scratch.motor_run_for_degrees",
  "values": { /* params object */ },
  "version": "18.0.1"
}

// Response (Swift -> JS):
{ "id": 42, "result": { ... } }   // or { "id": 42, "error": "..." }
```

### Complete scratch.* Method Reference

#### Motor Control

| Method | Parameters | Notes |
|--------|-----------|-------|
| `scratch.motor_run_for_degrees` | `port, speed, degrees, stall, stop, acceleration, deceleration` | Run motor until degrees reached |
| `scratch.motor_run_timed` | `port, time, speed, stall, stop, acceleration, deceleration` | Run motor for ms |
| `scratch.motor_start` | `port, speed, stall, acceleration, deceleration` | Start indefinite run |
| `scratch.motor_stop` | `port, stop` | Stop motor |
| `scratch.motor_go_direction_to_position` | `port, position, speed, direction, stall, stop, acceleration, deceleration` | Go to absolute position |
| `scratch.motor_go_to_relative_position` | `port, position, speed, stall, stop, acceleration, deceleration` | Go to relative position |
| `scratch.motor_set_position` | `port, offset` | Set degree-counted offset |
| `scratch.motor_pwm` | `port, power, stall` | Raw PWM power |

**Parameter details:**

| Parameter | Type | Range/Values |
|-----------|------|-------------|
| `port` | string | `"A"` `"B"` `"C"` `"D"` `"E"` `"F"` |
| `speed` | int | -100..100 (clamped) |
| `degrees` | int | -3,600,000..3,600,000 |
| `time` | int | 0..60,000 ms (0–60 s clamped) |
| `stall` | bool | true = stall detection active |
| `stop` | int | 0=Float · 1=Brake · 2=Hold |
| `acceleration` | int | 0..10,000 ms (ramp time) |
| `deceleration` | int | 0..10,000 ms (ramp time) |
| `position` | int | -3,600,000..3,600,000 degrees |
| `direction` | string | `"shortest"` `"clockwise"` `"counterclockwise"` |
| `power` | int | -100..100 |
| `offset` | int | clamped to int32 max |

#### Movement Pair

| Method | Parameters | Notes |
|--------|-----------|-------|
| `scratch.move_start_speeds` | `lmotor, rmotor, lspeed, rspeed, acceleration, deceleration` | Start both motors at independent speeds |
| `scratch.move_tank_degrees` | `lmotor, rmotor, lspeed, rspeed, degrees, stop, acceleration, deceleration` | Move pair until degrees |
| `scratch.move_tank_time` | `lmotor, rmotor, lspeed, rspeed, time, stop, acceleration, deceleration` | Move pair for time |
| `scratch.move_stop` | `stop` | Stop movement pair |

**Movement pair expansion:** The `lmotor`/`rmotor` fields are individual port strings (e.g. `"A"`, `"B"`). The `setMovementPair` block sets defaults (default: `["A","B"]`).

**Steering conversion:** Steering input (0=straight, +/- = turn) is converted to lspeed/rspeed via `fromSteeringAtSpeed(steering, speed)` using internal calibration.

#### Display

| Method | Parameters | Notes |
|--------|-----------|-------|
| `scratch.display_image` | `image` | Show image (numeric enum or matrix string) |
| `scratch.display_image_for` | `image, duration` | Show image for ms |
| `scratch.display_text` | `text` | Scroll text |
| `scratch.display_clear` | _(none)_ | Clear display |
| `scratch.display_set_pixel` | `x, y, brightness` | Set one pixel |
| `scratch.display_rotate_direction` | `direction` | Rotate display |
| `scratch.display_rotate_orientation` | `orientation` | Set display orientation |

**Image format:** Integer index (1–20 built-in images) or 25-char brightness string like `"9909999099000009000909990"` (5×5 grid, `0`=off, `9`=full bright).

#### Sound / Beep

| Method | Parameters | Notes |
|--------|-----------|-------|
| `scratch.sound_beep_for_time` | `duration, note, volume` | Beep at MIDI note for ms |
| `scratch.sound_beep` | `note, volume` | Continuous beep |
| `scratch.sound_off` | _(none)_ | Stop beep |
| `scratch.play_sound` | `path, volume, freq, wait` | Play sound file on hub |

**Note format:** MIDI note number (e.g. 60 = middle C).

#### Sensors

| Method | Parameters | Notes |
|--------|-----------|-------|
| `scratch.when_sensor_changed` | `port, mode, default, types, delta` | Subscribe to sensor stream |
| `scratch.reset_yaw` | _(none)_ | Reset IMU yaw to 0 |
| `scratch.set_orientation` | `orientation` | Set reference orientation |
| `scratch.ultrasonic_light_up` | `top_left, top_right, bottom_left, bottom_right` | Set ultrasonic sensor LEDs (0–100%) |
| `scratch.center_button_lights` | `color` | Set center button LED color |

**when_sensor_changed params:**

| Param | Description |
|-------|-------------|
| `port` | Port string `"A"`–`"F"` |
| `mode` | Integer LPF2 mode index (see Sensor Mode table in §8) |
| `default` | Default value to return when sensor absent |
| `types` | Array of LPF2Sensor type IDs this subscription expects |
| `delta` | Minimum change to trigger callback |

#### Connection

| Method | Parameters | Notes |
|--------|-----------|-------|
| `scratch.connect` | `hubId` | Request hub connection |
| `scratch.connectHighlight` | `hubId` | Highlight connection button |


---

## 6. LWP Binary Protocol (BLE)

The LWP (LEGO Wireless Protocol 3) binary layer is used for BLE-connected hubs. It is NOT used for USB connections.

### BLE Service Configuration

| Hub family | Service UUID | Characteristics | Write mode |
|-----------|-------------|-----------------|------------|
| SPIKE Essential / Prime BLE (Gecko) | `00001623-1212-efde-1623-785feabcd123` | Char `00001624-...` | WITH_RESPONSE |
| SPIKE Prime USB-BLE / GeckoAtlantis | `0000fd02-0000-1000-8000-00805f9b34fb` | Tx `0000fd02-0001-...` · Rx `0000fd02-0002-...` | WITHOUT_RESPONSE, MTU=512 |

**Routing rules:**
- `HubType.Gecko` → LWP3 service (classic LEGO service UUID)
- `HubType.Flipper`, `HubType.FlipperPT`, `HubType.GeckoAtlantis` → SPIKE UART service

### LWP Message Structure

```
[length: u8] [hubId: u8=0x00] [messageType: u8] [payload...]
```

**PortOutputCommand (messageType = 0x81):**
```
[portId: u8] [startupAndCompletion: u8] [subCommand: u8] [subCmdPayload...]
```

`startupAndCompletion` constant: `0x10` = ExecuteImmediately + CommandFeedback

### PortOutputCommand SubCommands

| SubCommand hex | Name | Payload |
|----------------|------|---------|
| `0x01` | StartPower | power:int8 |
| `0x02` | StartPower2 | power1:int8, power2:int8 |
| `0x07` | SetAccTime | time:uint16le, profileNo:uint8 |
| `0x08` | SetDecTime | time:uint16le, profileNo:uint8 |
| `0x09` | StartSpeed | speed:int8, maxPower:uint8, useProfile:uint8 |
| `0x0A` | StartSpeed2 | speed1:int8, speed2:int8, maxPower:uint8, useProfile:uint8 |
| `0x0B` | StartSpeedForTime | time:uint16le, speed:int8, maxPower:uint8, endState:uint8, useProfile:uint8 |
| `0x0C` | StartSpeedForTime2 | time:uint16le, speed1:int8, speed2:int8, maxPower:uint8, endState:uint8, useProfile:uint8 |
| `0x0D` | StartSpeedForDegrees | degrees:uint32le, speed:int8, maxPower:uint8, endState:uint8, useProfile:uint8 |
| `0x0E` | StartSpeedForDegrees2 | degrees:uint32le, speed1:int8, speed2:int8, maxPower:uint8, endState:uint8, useProfile:uint8 |
| `0x0F` | GotoAbsolutePosition | absPos:int32le, speed:int8, maxPower:uint8, endState:uint8, useProfile:uint8 |
| `0x10` | GotoAbsolutePosition2 | absPos1:int32le, absPos2:int32le, speed:int8, maxPower:uint8, endState:uint8, useProfile:uint8 |
| `0x51` | WriteDirectModeData | mode:uint8, data... |
| `0x11` | PresetEncoder | position:int32le |

### Key LWP Constants

| Constant | Value | Meaning |
|---------|-------|---------|
| `startupInfo` | `"ExecuteImmediately"` | Start executing as soon as received |
| `completionInfo` | `"CommandFeedback"` | Send feedback when command completes |
| `useProfile` | `"AccAndDec"` (byte `0x03`) | Use both acceleration and deceleration profiles |
| `maxPower` | 100 | Full power (not a speed limit) |

### endState (MotorStop) Encoding

| JS enum | Wire byte | Behaviour |
|---------|-----------|-----------|
| `MotorStop.Float = 0` | `0x03` | Coast: no holding force |
| `MotorStop.Brake = 1` | `0x02` | Active brake then release |
| `MotorStop.Hold = 2` | `0x01` | Hold position actively |

### Send Path

```javascript
// JS side (inside block execution engine):
Ve.hub.send({
  id: hubId,
  message: encode(lwpPortOutputCommand)
})
```

`encode()` serializes the LWP struct to a `Uint8Array`.  
This is sent via WebSocket to the native Swift app which forwards it over BLE GATT.


---

## 7. All Enum Definitions

### 7.1 MotorDirection

Source: module 42907, exported as `lt.xe`, re-exported from `h.MotorDirection`

| Key | Wire string | Meaning |
|-----|------------|---------|
| `Forward` | `"forward"` | Default "forward" direction |
| `Reverse` | `"back"` | Reverse / backward |
| `Clockwise` | `"clockwise"` | Clockwise rotation |
| `CounterClockwise` | `"counterclockwise"` | Counter-clockwise rotation |

**Direction inversion:** The `hw(speed, direction)` function negates speed when direction is `"counterclockwise"`, `"ccw"`, or `"1"`.

### 7.2 MotorPositionDirection

Source: module 42907, `lt.o2`

| Key | Wire string |
|-----|------------|
| `Shortest` | `"shortest"` |
| `Clockwise` | `"clockwise"` |
| `CounterClockwise` | `"counterclockwise"` |

### 7.3 MotorUnit

Source: module 42907, `lt.vD`

| Key | Wire string | Used in |
|-----|------------|---------|
| `Degrees` | `"degrees"` | `motorTurnForDirection`, `move_tank_degrees` |
| `Seconds` | `"seconds"` | `motor_run_timed`, `move_tank_time` |
| `Rotations` | `"rotations"` | Converted to degrees × 360 internally |

### 7.4 MotorStop

Source: module 88590, `To` (= `A.MotorStop`); full bidirectional enum

| Key | Int value | Wire string | LWP byte |
|-----|-----------|------------|---------|
| `Float` | 0 | `"Float"` | `0x03` |
| `Brake` | 1 | `"Brake"` | `0x02` |
| `Hold` | 2 | `"Hold"` | `0x01` |

Default stop method: `MotorStop.Brake`

### 7.5 StopOption (Scratch block field values for STOP field)

Source: module 42907, `lt.zx`

| Key | Wire string |
|-----|------------|
| `All` | `"all"` |
| `This` | `"this stack"` |
| `Other` | `"other stacks"` |
| `Program` | `"program"` |

### 7.6 Acceleration Presets

Source: module 42907, `lt.Rb`

| Key | Wire string | accel_ms | decel_ms |
|-----|------------|----------|---------|
| `Slow` | `"1000 1000"` | 1000 | 1000 |
| `Medium` | `"3000 3000"` | 3000 | 3000 |
| `Fast` | `"10000 10000"` | 10000 | 10000 |

Default motor acceleration: `"3000 3000"` · Default small acceleration: `"2000 2000"`

### 7.7 PressureOption / ForceOption

Source: module 42907, `lt.aG` (PressureOption) and `lt.wu` (ForceOption)

| PressureOption key | Wire string |
|--------------------|------------|
| `PressureChanged` | `"pressurechanged"` |
| `Pressed` | `"pressed"` |
| `HardPressed` | `"hardpressed"` |
| `Released` | `"released"` |

### 7.8 DistanceUnit / DistanceRelative

Source: module 42907, `lt.sf` / `lt.QJ`

| DistanceUnit key | Wire string |
|------------------|------------|
| `Cm` | `"cm"` |
| `Inches` | `"inches"` |
| `Percent` | `"%"` |

| DistanceRelative key | Wire string |
|----------------------|------------|
| `Near` | `"near"` |
| `Far` | `"far"` |
| `Changed` | `"changed"` |

### 7.9 HubAxis (AxisOption)

Source: module 42907, `lt.m9` (HubAxis) and `lt.lW` (AxisOption)

| HubAxis key | Wire string |
|-------------|------------|
| `Pitch` | `"pitch"` |
| `Roll` | `"roll"` |
| `Yaw` | `"yaw"` |

| AxisOption key | Wire string |
|----------------|------------|
| `XAxis` | `"x"` |
| `YAxis` | `"y"` |
| `ZAxis` | `"z"` |

### 7.10 HubOrientation / TiltDirection

Source: `lt.yJ` (TiltDirection); orientation map from JS orientationMap object

**HubOrientation (LWP numeric → string):**

| LWP value | String |
|-----------|--------|
| 1 | `"front"` |
| 2 | `"back"` |
| 3 | `"up"` |
| 4 | `"down"` |
| 5 | `"leftside"` |
| 6 | `"rightside"` |

**TiltDirection (used in hat blocks):**

| Key | Wire string |
|-----|------------|
| `UP` | `"1"` |
| `DOWN` | `"2"` |
| `LEFT` | `"3"` |
| `RIGHT` | `"4"` |
| `ANY` | `"5"` |
| `FLAT` | `"6"` |

### 7.11 ColorFieldOption

Source: module 88590, `Gn.G` (= `A.ColorFieldOption`); module 10639 `ge`

| Key | Integer string | Color name wire string |
|-----|---------------|----------------------|
| `Black` | `"0"` | `"black"` |
| `Violet` | `"1"` | `"violet"` |
| `Purple` | `"2"` | `"purple"` |
| `Blue` | `"3"` | `"blue"` |
| `Azure` | `"4"` | `"azure"` |
| `Turquoise` | `"5"` | `"lightgreen"` |
| `Green` | `"6"` | `"green"` |
| `Yellow` | `"7"` | `"yellow"` |
| `Orange` | `"8"` | `"orange"` |
| `Red` | `"9"` | `"red"` |
| `White` | `"10"` | `"white"` |
| `NoColor` | `"-1"` | `"nocolor"` |
| `Changed` | `"-2"` | `"changed"` |
| `Random` | `"-3"` | `"random"` |

### 7.12 HubType (External String IDs)

Source: module 80602, `I` (HubType enum)

| Key | Wire string | Device |
|-----|------------|--------|
| `Flipper` | `"flipper"` | SPIKE Prime (USB) |
| `FlipperPT` | `"flipper-pt"` | SPIKE Prime (pass-through) |
| `Gecko` | `"flipper-ble"` | SPIKE Prime over BLE |
| `GeckoAtlantis` | `"gecko-atlantis"` | SPIKE Prime 3 |

### 7.13 HubButtons / HubButtonEvents

Source: module 42907, `lt.ns` / `lt.Of`

| HubButtons key | Wire string |
|----------------|------------|
| `Left` | `"left"` |
| `Right` | `"right"` |

| HubButtonEvents key | Wire string |
|---------------------|------------|
| `Pressed` | `"pressed"` |
| `Released` | `"released"` |

### 7.14 Comparator

Source: module 42907, `lt.s2`

| Key | Wire string |
|-----|------------|
| `Less` | `"<"` |
| `Equal` | `"="` |
| `Greater` | `">"` |

### 7.15 SerialProductId / SerialVendorId

Source: module 88590

| Enum | Key | Value |
|------|-----|-------|
| `SerialVendorId` | `LEGO` | 1684 |
| `SerialProductId` | `Flipper` | 9 |
| `SerialProductId` | `FlipperMSD` | 10 |
| `SerialProductId` | `Gecko` | 13 |
| `SerialProductId` | `GeckoMSD` | 14 |
| `SerialProductId` | `Mindstorms` | 16 |

### 7.16 LedImage Presets

Source: module 42907, `lt.$M`

| Key | 25-char matrix (5×5 brightness chars) |
|-----|--------------------------------------|
| `Smiley` | `"9909999099000009000909990"` |
| `Heart` | `"0909099999999990999000900"` |
| `Filled` | `"9999999999999999999999999"` |
| `Blank` | `"0000000000000000000000000"` |

### 7.17 DisplayImage (Built-in Hub Images)

Source: module 10639, `be` (DisplayImage enum)

| Key | Int value |
|-----|-----------|
| `Robot1` | 1 |
| `Robot2` | 2 |
| `Robot3` | 3 |
| `Robot4` | 4 |
| `Robot5` | 5 |
| `Hub1` | 6 |
| `Hub2` | 7 |
| `Hub3` | 8 |
| `Hub4` | 9 |
| `AmusementPark` | 10 |
| `Beach` | 11 |
| `HauntedHouse` | 12 |
| `Carnival` | 13 |
| `Bookshelf` | 14 |
| `Playground` | 15 |
| `Moon` | 16 |
| `Cave` | 17 |
| `Ocean` | 18 |
| `PolarBear` | 19 |
| `Park` | 20 |
| `Random` | -3 |


---

## 8. Sensor System

### 8.1 LPF2Sensor Type IDs

Source: module 88590, `Ct` enum (= `A.LPF2Sensor`)

| Key | Type ID | Device |
|-----|---------|--------|
| `HubVoltageSense` | 20 | Hub internal voltage |
| `HubUILight` | 23 | Hub center LED |
| `FlipperMediumMotor` | 48 | SPIKE Prime Medium Motor (grey) |
| `FlipperLargeMotor` | 49 | SPIKE Prime Large Motor |
| `ThreeAxisGesture` | 54 | Internal IMU gesture sensor |
| `ThreeAxisAcceleration` | 57 | Internal IMU accelerometer |
| `ThreeAxisGyro` | 58 | Internal IMU gyroscope |
| `ThreeAxisOrientation` | 59 | Internal IMU orientation sensor |
| `FlipperColor` | 61 | SPIKE Color Sensor |
| `FlipperDistance` | 62 | SPIKE Distance Sensor |
| `FlipperForce` | 63 | SPIKE Force Sensor |
| `ColorMatrix3x3` | 64 | 3×3 Color Matrix (accessory) |
| `FlipperSmallMotor` | 65 | SPIKE Prime Small Angular Motor |
| `StoneGreyMediumMotor` | 75 | SPIKE Prime Medium Angular Motor |
| `StoneGreyLargeMotor` | 76 | SPIKE Prime Large Angular Motor |

### 8.2 Sensor Modes (LPF2 mode index → data meaning)

#### FlipperColor (type 61)

| Mode | Data | Range | Description |
|------|------|-------|-------------|
| 0 | color | -1..10 | Color index (-1=none) |
| 1 | reflectivity | 0–100 | Reflected light percentage |
| 2 | ambient | 0–255 | Ambient light level |
| 3 | raw_R | 0–255 | Raw red channel |
| 4 | raw_G/B | 0–255 | Raw green/blue channels |

#### FlipperDistance (type 62)

| Mode | Data | Range | Description |
|------|------|-------|-------------|
| 0 | distance_cm | 0–200 | Distance in centimetres |
| 1 | distance_in | 0–79 | Distance in inches |
| 2 | distance_pct | 0–100 | Distance as percentage |

#### FlipperForce (type 63)

| Mode | Data | Range | Description |
|------|------|-------|-------------|
| 0 | force_N | 0–10 | Force in Newtons |
| 1 | pressed | 0–1 | Binary pressed/not pressed |
| 4 | raw | 0–raw | Raw ADC value |

#### FlipperMediumMotor / FlipperLargeMotor (types 48, 49, 75, 76)

| Mode | Data | Description |
|------|------|-------------|
| 0 | power | Actual power % |
| 1 | speed | Actual speed % |
| 2 | position | Absolute position -180..180 deg |
| 3 | abs_position | Degree-counted position |

#### ThreeAxisGyro (type 58)

| Mode | Data | Description |
|------|------|-------------|
| 0 | angular_velocity | x/y/z angular velocity (deg/s) |

#### ThreeAxisAcceleration (type 57)

| Mode | Data | Description |
|------|------|-------------|
| 0 | acceleration | x/y/z acceleration (mG) |

### 8.3 Sensor Subscription Flow

```
1. Hat block (whenSensorChanged) triggers
2. E0.whenSensorChanged(targetId, port, type, mode, delta)
3. -> { method: "scratch.when_sensor_changed",
         params: { port, mode, default: MT(type, mode),
                   types: [typeId], delta } }
4. Native app subscribes to LPF2 sensor notifications on that port/mode
5. When sensor changes by >= delta, native sends notification
6. JS receives notification, triggers hat block continuation
```

### 8.4 PreferredAttachmentType

Source: module 80602, `oe`

| Key | Value |
|-----|-------|
| `Color` | 0 |
| `Force` | 1 |
| `Distance` | 2 |
| `Motor` | 3 |
| `RGB` | 4 |


---

## 9. Tunnel Protocol (MicroPython <-> JS)

The **module tunnel** is the binary communication channel between MicroPython running on the hub and the JavaScript runtime. It is used for real-time data streaming (graphs, displays, variables) and async sensor reading during program execution.

### 9.1 Transport Layer

```
MicroPython on hub
    |
    v  Binary frames via _hub.config["module_tunnel"]
Swift native bridge
    |
    v  JSON/binary WebSocket on localhost:2846
JS runtime
```

### 9.2 Endianness

`TunnelMessageEndianness = "big"` — all multi-byte integers are **big-endian** (matching MicroPython `struct` format `">"`)

### 9.3 Message Frame Format

```
[id: u8] [correlationId: u8?] [field1] [field2] ...
```

- `id` is always the first byte — message type identifier
- `correlationId` is present in **request** messages (`BX`-tagged) but not in fire-and-forget (`Em`-tagged)
- All fields serialized in the order declared in the message format array
- String fields are null-terminated UTF-8 with dynamic length

### 9.4 Field Type Builders (module 37402)

| Builder fn | Size | Signed | Description |
|-----------|------|--------|-------------|
| `w_(name)` | 1 byte | no | uint8 |
| `cS(name)` | 1 byte | yes | int8 |
| `mL(name)` | 2 bytes | no | uint16 |
| `Af(name)` | 2 bytes | yes | int16 |
| `U7(name)` | 4 bytes | no | uint32 |
| `C` | 4 bytes | yes | int32 |
| `PJ(name)` | 2 bytes | no, scale=10 | uint16 / 10 (fixed point) |
| `gl(name)` | 2 bytes | yes, scale=10 | int16 / 10 (fixed point) |
| `vE(name)` | 4 bytes | float | float32 |
| `Xg(name)` | 1 byte | bool | boolean (0/1) |
| `Z_(name)` | variable | — | null-terminated UTF-8 string |
| `Em(id, ...fields)` | — | — | Fire-and-forget message (no correlationId) |
| `BX(id, ...fields)` | — | — | Request/response message (has correlationId) |

### 9.5 Complete Tunnel Message ID Table

Source: module 69253 (wt), sub-modules 41495, k, I, L, G, oe, le

#### Core Messages (module 41495)

| ID | Name | Fields | Direction |
|----|------|--------|-----------|
| 91 | `Assertion` | `success:bool, message:string` | hub→JS |
| 92 | `ProgramAttributes` | `project:string` | JS→hub |
| 93 | `LatestTunnelValueRequest` | `type:u8, field:string` | JS→hub (request) |
| 94 | `LatestTunnelValueResponse` | `success:bool, age:u16, value:string` | hub→JS (response) |

#### Display Messages (sub-module I in 69253)

| ID | Name | Fields |
|----|------|--------|
| 41 | `DisplayImage` | `image:u8` |
| 42 | `DisplayImageForTime` | `image:u8` |
| 43 | `DisplayNextImage` | _(none)_ |
| 44 | `DisplayText` | `text:string` |
| 45 | `DisplayTextForTime` | `text:string` |
| 46 | `DisplayShow` | `fullscreen:bool` |
| 47 | `DisplayHide` | _(none)_ |

> Note: `DisplayImageMessage` (ID 44 in the re-export alias `wt.QV`) is the same as `DisplayText`

#### Graph Messages (sub-module L in 69253)

| ID | Name | Fields |
|----|------|--------|
| 50 | `GraphShow` | `graphType:u8, fullscreen:bool` |
| 51 | `GraphHide` | `graphType:u8` |
| 52 | `GraphClear` | `graphType:u8` |
| 53 | `GraphValue` | `value:float32` (response, `BX`) |
| 54 | `LineGraphClearColor` | `color:u8` |
| 55 | `LineGraphPlot` | `color:u8, x:float32, y:float32` |
| 56 | `LineGraphRequestValue` | `color:u8, option:u8` (request, `BX`) |
| 57 | `BarGraphSetValue` | `color:u8, value:float32` |
| 58 | `BarGraphChange` | `color:u8, delta:float32` |
| 59 | `BarGraphRequestValue` | `color:u8` (request, `BX`) |

#### Music Messages (sub-module G in 69253)

| ID | Name | Fields |
|----|------|--------|
| 1 | `MusicPlayDrumForBeats` | `drum:u8` |
| 2 | `MusicPlayNoteForBeats` | `instrument:u8, note:u8, duration:u32` |
| 3 | `MusicTempoUpdate` | `tempo:u16` |
| 4 | `MusicStopAllNotes` | _(none)_ |
| 5 | `MusicStopAllDrums` | _(none)_ |

#### Sound Messages (sub-module oe in 69253)

| ID | Name | Fields |
|----|------|--------|
| 22 | `SoundPlay` | `crc:u32, volume:u8, pitch:int16, pan:int8` |
| 23 | `SoundPlayUntilDone` | `crc:u32, volume:u8, pitch:int16, pan:int8` (request, `BX`) |
| 24 | `SoundDone` | _(none)_ (response, `BX`) |
| 25 | `SoundStopAll` | _(none)_ |
| 26 | `SoundSetAttributes` | `volume:u8, pitch:int16, pan:int8` |
| 27 | `SoundStop` | _(none)_ (request, `BX`) |

#### Variable/List Messages (sub-module k in 69253)

| ID | Name | Fields |
|----|------|--------|
| 96 | `VariableUpdate` | `name:string, value:string` |
| 97 | `ListAddItem` | `name:string, item:string` |
| 98 | `ListRemoveItem` | `name:string, index:u8` |
| 99 | `ListInsertItem` | `name:string, item:string, index:u8` |
| 100 | `ListReplaceItem` | `name:string, item:string, index:u8` |
| 101 | `ListClear` | `name:string` |

#### Weather Messages (sub-module le in 69253)

| ID | Name | Fields |
|----|------|--------|
| 31 | `WeatherAtOffsetRequest` | `days:u16, hours:u16, location:string` (request) |
| 33 | `WeatherForecast` | `temperature:int16/10, precipitation:u16/10, condition:u8, windDirection:string, windSpeed:u16/10, pressure:u16/10, offset:u16, location:string` (response) |

### 9.6 Sound CRC Format

The `crc` field for `SoundPlay`/`SoundPlayUntilDone` is a CRC32 of the sound name string, padded to a multiple of 4 bytes:
```python
def _padcrc(s):
    b = str(s).encode("utf8")
    r = len(b) % 4
    return _crc32(b if r == 0 else b + b"\0" * (4 - r))
```

### 9.7 GraphType Enum

| Key | Value | Description |
|-----|-------|-------------|
| `Line` | 1 | Line graph |
| `Bar` | 2 | Bar graph |

### 9.8 GraphColor (for graph messages)

| Key | Value |
|-----|-------|
| `Red` | 0 |
| `Yellow` | 1 |
| `Azure` | 2 |
| `Blue` | 3 |
| `Green` | 4 |
| `Violet` | 5 |


---

## 10. Python Code Generator

When a Scratch project is compiled for execution, the JS engine generates a complete MicroPython program that runs on the hub. This section documents the full source structure.

### 10.1 Entry Point: UB(programAttributes)

`UB` is the master Python program generator function. It assembles sections in this order:

```
GB()            → import block
zB()            → tunnel setup
jB(attributes)  → program attributes send
VB()            → graph/utility functions
WB()            → linegraph module class
YB()            → bargraph module class
QB()            → display module class
XB()            → sound module class
KB()            → music module class
[user blocks]   → compiled block code
```

### 10.2 GB() — Import Block

```python
import hub as _hub
import binascii
import collections
import errno
import micropython
import struct
import utime
```

### 10.3 zB() — Tunnel Setup

```python
try:
    _tunnel = _hub.config["module_tunnel"]
except ImportError:
    import sys
    class MockTunnel:
        def send(self, data):
            print("MockTunnel.send:\n\traw: {}\n\thex: {}\n\tdec: {}".format(
                data, data.hex(" ").upper(), " ".join(str(b) for b in data)))
        def callback(self, cb): pass
        def connected(self): return False
    sys.modules['tunnel'] = MockTunnel()

_correlation_id = 0
_responses = {}
_in_flight = 0
_tx = 8192 // 8           # transmit buffer size
_nx = _tx // 4            # throughput limit bytes/sec

def _tunnel_callback(data):
    global _correlation_id, _responses, _in_flight
    # parse response, route by correlation_id
    ...

_tunnel.callback(_tunnel_callback)

def _pack(fmt, id_, *values):
    return struct.pack(">" + fmt, id_, *values)

def _send(fmt, id_, *values):
    _tunnel.send(_pack(fmt, id_, *values))

def _request(fmt, id_, *values):
    # sends with correlationId, awaits response
    ...

def is_connected():
    return _tunnel.connected()
```

### 10.4 jB(t) — Program Attributes

Sends the project metadata to the hub at program start:
```python
_tunnel.send(bytes([ProgramAttributes.id, *kB.from(t, "utf8"), 0]))
```
Where `ProgramAttributes.id = 92` and `t` is the JSON-serialized project attributes string.

### 10.5 VB() — Utility Functions

```python
async def _unpack_graph_value(response):
    b = await response
    return _unpack(">Bf", b)[-1]   # big-endian: u8 id + float32 value

def _padcrc(s):
    b = str(s).encode("utf8")
    r = len(b) % 4
    return binascii.crc32(b if r == 0 else b + b"\0" * (4 - r))
```

### 10.6 Module Class Builders

Each module (linegraph, bargraph, display, sound, music) is emitted as a Python class with `@staticmethod` methods that return tunnel `_send()` or `_request()` calls.

**Template pattern:**
```python
class linegraph(__static):
    PURPLE = _const(0)
    BLUE   = _const(1)
    AZURE  = _const(2)
    GREEN  = _const(3)
    YELLOW = _const(4)
    RED    = _const(5)

    @staticmethod
    def clear(color):
        return _send("BB", 54, color)    # LineGraphClearColor id=54

    @staticmethod
    def plot(color, x, y):
        return _send("BBff", 55, color, x, y)    # LineGraphPlot id=55

    @staticmethod
    def get_value(color, option):
        return _request("BBB", 56, color, option)  # LineGraphRequestValue id=56
```

```python
class bargraph(__static):
    PURPLE = _const(0)
    ...
    @staticmethod
    def set_value(color, value):
        return _send("BBf", 57, color, value)   # BarGraphSetValue id=57

    @staticmethod
    def change(color, value):
        return _send("BBf", 58, color, value)   # BarGraphChange id=58
```

```python
class display(__static):
    IMAGE_ROBOT1 = _const(1)
    IMAGE_ROBOT2 = _const(2)
    ...
    IMAGE_RANDOM = _const(21)   # len(DisplayImage entries)

    @staticmethod
    def image(image):
        return _send("BB", 41, image)    # DisplayImage id=41

    @staticmethod
    def text(text):
        return _send("Bs", 44, text)     # DisplayText id=44

    @staticmethod
    def show(fullscreen=False):
        return _send("BB", 46, 1 if fullscreen else 0)

    @staticmethod
    def hide():
        return _send("B", 47)
```

```python
class sound(__static):
    @staticmethod
    def play(sound, volume=100, pitch=0, pan=0):
        return _request("BIBHB", 23, _padcrc(sound), volume, pitch, pan)

    @staticmethod
    def stop():
        return _send("B", 25)

    @staticmethod
    def set_attributes(volume, pitch, pan):
        return _send("BHB", 26, volume, pitch, pan)
```

```python
class music(__static):
    DRUM_BASS   = _const(...)
    DRUM_SNARE  = _const(...)
    ...
    @staticmethod
    def play_drum(drum):
        return _send("BB", 1, drum)

    @staticmethod
    def play_instrument(instrument, note=60, duration=250):
        return _send("BBBI", 2, instrument, note, duration)
```

### 10.7 Motor Initialization Block: FB(timeout=500)

Emitted before user code when motor blocks are present:
```python
async def initialize_motors():
    for p in range(6):
        try:
            if device.id(p) in (65, 48, 49, 75, 76):  # known motor type IDs
                await runloop.until(lambda: device.ready(p), timeout=500)
        except OSError:  # ENODEV
            pass
runloop.run(initialize_motors())
```

### 10.8 Code Generator DSL (JS side)

The intermediate representation before Python string emission uses a DSL:

| Function | Signature | Output Python |
|----------|-----------|---------------|
| `xn(mod, method, args, ctx)` | module.method call | `mod.method(arg1, arg2)` |
| `Lu(ctx, mod, field, type)` | field accessor | `mod.field` |
| `Wr(name, value)` | named kwarg | `name=value` |
| `Ma(ctx, method, args)` | motor_pair call | `motor_pair.method(args)` |
| `Ut(opcode, ctx, type)` | typed int value | integer expression |
| `en(...)` | line emitter | single Python statement line |
| `bl(mod, field)` | field builder | `mod.field` |
| `Th(name, ...body)` | module builder | `{name: str, body: [...]}` |
| `Ui(...lines)` | static method wrapper | `["@staticmethod", line1, ...]` |
| `sx(prefix, entries)` | constant entries | `PREFIX_NAME = _const(value)` |
| `$S(...lines)` | raw lines array | pass-through |
| `ib(line, indent)` | indent a line | `"  " * indent + line` |


---

## 11. Block XML Format

The Scratch XML embedded in `.llsp3` projectbody or in content JSON files uses a Blockly-derived format.

### 11.1 Root Element

```xml
<xml xmlns="http://www.w3.org/1999/xhtml"
     blockversion="23"
     ishorizontal="false"
     displaymonitorincludedimages="11">
  <!-- block stacks -->
</xml>
```

| Attribute | Values | Notes |
|-----------|--------|-------|
| `blockversion` | 9, 10, 23 | Schema version for migrations |
| `ishorizontal` | `"true"` `"false"` | Horizontal (icon) vs vertical (word) mode |
| `displaymonitorincludedimages` | integer | DisplayImage enum value shown in monitor |

### 11.2 Block Element Structure

```xml
<block type="flippermotor_motorTurnForDirection" id="~abc123" x="100" y="200">
  <field name="DIRECTION">forward</field>
  <field name="UNIT">degrees</field>
  <value name="PORT">
    <shadow type="flippermotor_multiple-port-selector">
      <field name="field_flippermotor_multiple-port-selector">A</field>
    </shadow>
  </value>
  <value name="VALUE">
    <shadow type="math_number">
      <field name="NUM">90</field>
    </shadow>
  </value>
  <value name="ACCELERATION">
    <shadow type="flippermotor_acceleration-selector">
      <field name="field_flippermotor_acceleration-selector">3000 3000</field>
    </shadow>
  </value>
  <next>
    <block type="..." id="...">
      <!-- next block -->
    </block>
  </next>
</block>
```

### 11.3 Shadow (Default Value) Block Types

| Shadow type | Field name | Example value |
|------------|-----------|---------------|
| `flippermotor_multiple-port-selector` | `field_flippermotor_multiple-port-selector` | `"A"` |
| `flippermotor_single-port-selector` | `field_flippermotor_single-port-selector` | `"A"` |
| `flippermotor_acceleration-selector` | `field_flippermotor_acceleration-selector` | `"3000 3000"` |
| `flippersound_sound-selector` | `field_flippersound_sound-selector` | `{"name":"Goal Cheer","location":"device"}` |
| `math_number` | `NUM` | `"90"` |
| `math_positive_number` | `NUM` | `"50"` |
| `math_integer` | `NUM` | `"0"` |
| `math_angle` | `NUM` | `"90"` |
| `text` | `TEXT` | `"Hello"` |
| `colour_picker` | `COLOUR` | `"#ff0000"` |

### 11.4 Key Block XML Examples

#### motorTurnForDirection

```xml
<block type="flippermotor_motorTurnForDirection" id="someId">
  <field name="DIRECTION">forward</field>
  <field name="UNIT">degrees</field>
  <value name="PORT">
    <shadow type="flippermotor_multiple-port-selector">
      <field name="field_flippermotor_multiple-port-selector">A</field>
    </shadow>
  </value>
  <value name="VALUE">
    <shadow type="math_positive_number">
      <field name="NUM">90</field>
    </shadow>
  </value>
  <value name="ACCELERATION">
    <shadow type="flippermotor_acceleration-selector">
      <field name="field_flippermotor_acceleration-selector">3000 3000</field>
    </shadow>
  </value>
</block>
```

#### motorStop

```xml
<block type="flippermotor_motorStop" id="someId">
  <field name="STOP">1</field>
  <value name="PORT">
    <shadow type="flippermotor_multiple-port-selector">
      <field name="field_flippermotor_multiple-port-selector">A</field>
    </shadow>
  </value>
</block>
```

#### flippersensors_iscolor (Boolean)

```xml
<block type="flippersensors_iscolor" id="someId">
  <field name="COLOR">9</field>
  <value name="PORT">
    <shadow type="flippermotor_single-port-selector">
      <field name="field_flippermotor_single-port-selector">A</field>
    </shadow>
  </value>
</block>
```

#### flipperevents_whenProgramStarts (hat)

```xml
<block type="flipperevents_whenProgramStarts" id="someId" x="50" y="50">
  <next>
    <block type="flippermotor_motorTurnForDirection" id="...">
      <!-- ... -->
    </block>
  </next>
</block>
```

#### flippermove_move

```xml
<block type="flippermove_move" id="someId">
  <field name="DIRECTION">forward</field>
  <field name="UNIT">degrees</field>
  <value name="VALUE">
    <shadow type="math_positive_number">
      <field name="NUM">100</field>
    </shadow>
  </value>
  <value name="SPEED">
    <shadow type="math_number">
      <field name="NUM">50</field>
    </shadow>
  </value>
  <value name="STEERING">
    <shadow type="math_number">
      <field name="NUM">0</field>
    </shadow>
  </value>
  <value name="ACCELERATION">
    <shadow type="flippermotor_acceleration-selector">
      <field name="field_flippermotor_acceleration-selector">3000 3000</field>
    </shadow>
  </value>
</block>
```

#### flipperdisplay_lightDisplayImageOn

```xml
<block type="flipperdisplay_lightDisplayImageOn" id="someId">
  <value name="MATRIX">
    <shadow type="flipperdisplay_led-image-selector">
      <field name="field_flipperdisplay_led-image-selector">9909999099000009000909990</field>
    </shadow>
  </value>
</block>
```

#### Sound selector field (JSON format)

```xml
<block type="flippersound_playSound" id="someId">
  <value name="SOUND">
    <shadow type="flippersound_sound-selector">
      <field name="field_flippersound_sound-selector">{"name":"Goal Cheer","location":"device"}</field>
    </shadow>
  </value>
</block>
```

### 11.5 Block Versions and Migrations

| blockversion | What changed |
|-------------|-------------|
| 9 | Original format |
| 10 | Added acceleration fields |
| 23 | Current version — added new motor variants |

Migrations are handled by `runSb3Migrations()` and `runXmlSnippetMigrations()` (module 95880).

### 11.6 Block ID Format

Block IDs are nanoid-like random strings. They allow special characters including `~`, `|`, `(`, `)`, `.`. Example: `~abc123XYZ`, `|q(Fy.abc`. The length is typically 8–20 characters.


---

## 12. Native WebSocket API

The JS app communicates with the Swift native layer via a WebSocket on `ws://localhost:2846`. Two categories of messages exist: **RPC methods** (JS calls native) and **Notification events** (native pushes to JS).

### 12.1 cge Class (WebSocket RPC Client)

```javascript
// JS pseudo-code
class cge {
  constructor(url) { this.ws = new WebSocket(url) }

  send(method, params) {
    return this.ws.send(JSON.stringify({
      method,
      values: params,
      version: "18.0.1"
    }))
  }
}

const ep = new cge("ws://localhost:2846")  // singleton
```

### 12.2 qt Enum — Native RPC Methods (JS → Swift)

Source: module 88590, `qt` object extracted as `cP` in main bundle

| URL | Method | Purpose |
|-----|--------|---------|
| `/api/v1/hubs` | GET | List connected hubs |
| `/api/v1/hubs/:id/connect` | POST | Connect to hub |
| `/api/v1/hubs/:id/disconnect` | POST | Disconnect from hub |
| `/api/v1/hubs/:id/program/start` | POST | Start running a program |
| `/api/v1/hubs/:id/program/stop` | POST | Stop running program |
| `/api/v1/hubs/:id/program/download` | POST | Download program to hub |
| `/api/v1/hubs/:id/program/slots` | GET | Get program slot info |
| `/api/v1/hubs/:id/name` | PUT | Set hub name |
| `/api/v1/hubs/:id/firmware/update` | POST | Start firmware update |
| `/api/v1/hubs/:id/firmware/info` | GET | Get firmware version info |
| `/api/v1/hubs/:id/storage` | GET | Get hub storage info |
| `/api/v1/hubs/:id/sensor/:port` | GET | Get sensor value |
| `/api/v1/hubs/:id/motor/:port/position` | GET | Get motor absolute position |
| `/api/v1/settings` | GET/PUT | App settings |
| `/api/v1/projects` | GET | List local projects |
| `/api/v1/projects/:id` | GET/PUT/DELETE | Project CRUD |
| `/api/v1/projects/export` | POST | Export project to file |
| `/api/v1/projects/import` | POST | Import project from file |
| `/api/v1/sounds` | GET | List available sounds |
| `/api/v1/sounds/record` | POST | Start sound recording |
| `/api/v1/localization` | GET | Locale strings |
| `/api/v1/analytics/event` | POST | Log analytics event |
| `/api/v1/debug` | GET | Debug info |
| _(+ ~30 more)_ | — | Notifications, monitoring, etc. |

### 12.3 Ot Enum — Native Notification Events (Swift → JS)

| Event URL | Payload | Trigger |
|-----------|---------|---------|
| `/notifications/hubs/connected` | `{hubId, hubInfo}` | Hub connected via USB/BLE |
| `/notifications/hubs/disconnected` | `{hubId}` | Hub disconnected |
| `/notifications/hubs/updated` | `{hubId, ...changes}` | Hub state changed |
| `/notifications/hubs/buttonPressed` | `{hubId, button}` | Hub button pressed |
| `/notifications/hubs/program/started` | `{hubId}` | Program started running |
| `/notifications/hubs/program/stopped` | `{hubId, reason}` | Program stopped |
| `/notifications/hubs/program/error` | `{hubId, error}` | Runtime error |
| `/notifications/hubs/firmware/progress` | `{hubId, progress}` | Firmware update progress |
| `/notifications/hubs/firmware/done` | `{hubId}` | Firmware update complete |
| `/notifications/hubs/sensor/changed` | `{hubId, port, value}` | Sensor value changed |
| `/notifications/hubs/tunnel/data` | `{hubId, data: Uint8Array}` | Tunnel message from hub |
| `/notifications/projects/changed` | `{}` | Project list changed |
| `/notifications/settings/changed` | `{key, value}` | Setting changed |

### 12.4 Hub Info Object (from /notifications/hubs/connected)

```jsonc
{
  "id": "hubUniqueId",
  "name": "My SPIKE Hub",
  "type": "flipper",            // HubType string
  "firmwareVersion": "3.x.x",
  "hardwareVersion": "0.x.x",
  "battery": 85,                // percent
  "rssi": -65,                  // dBm (BLE only)
  "ports": {
    "A": { "type": 48, "present": true },    // type = LPF2Sensor ID
    "B": { "type": 49, "present": true },
    "C": { "type": null, "present": false },
    // ...
  }
}
```


---

## 13. Horizontal (Icon Blocks) Mode

SPIKE supports two visual programming modes:
- **Vertical (Word blocks):** Standard Scratch-like blocks with text labels
- **Horizontal (Icon blocks):** Simplified blocks with icons, targeted at younger learners

### 13.1 Mode Detection

```xml
<xml ... ishorizontal="true">
```

The `ishorizontal` XML attribute on the root element and the manifest `appType` field distinguish modes.

### 13.2 OpcodeHorizontal Enum

Source: module 83295, `k` (= `h.OpcodeHorizontal`)

These are the opcode **string keys** (NOT full `namespace_opcode` form) for horizontal mode blocks:

```
ledMatrix                     ledImage
ledMatrixOn                   ledMatrixRandom
ledRandom                     motorTurnClockwiseRotations
motorTurnCounterClockwiseRotations  motorSetSpeed
motorStop                     playAnimalSoundUntilDone
playEffectSoundUntilDone      playMusicSoundUntilDone
recordSound                   playRecordedSound
stopSound                     isColor (="iscolor")
whenColor                     whenCloserThan
whenProgramStarts             whenBroadcast
broadcast                     whenTilted
whenPressed                   whenLouderThan
moveForward                   moveBackward
moveTurnClockwiseRotations    moveTurnCounterClockwiseRotations
moveSetSpeed                  moveStop
displaySetImageWithBuiltInDelay  displaySetMonitorFullscreen
displayWriteWithBuiltInDelay  barGraphChangeValue
barGraphClearData             barGraphViewMode
stopOtherStacks
```

### 13.3 Horizontal Extension Namespaces

Full opcode form for horizontal blocks uses `horizontal` prefix + extension name:

| Namespace | Opcodes |
|-----------|---------|
| `horizontalmotor` | `motorTurnClockwiseRotations`, `motorTurnCounterClockwiseRotations`, `motorSetSpeed`, `motorStop` |
| `horizontalmove` | `moveForward`, `moveBackward`, `moveTurnClockwiseRotations`, `moveTurnCounterClockwiseRotations`, `moveSetSpeed`, `moveStop` |
| `horizontalsound` | `playAnimalSoundUntilDone`, `playEffectSoundUntilDone`, `playMusicSoundUntilDone`, `recordSound`, `playRecordedSound` |
| `horizontaldisplay` | `ledImage`, `ledMatrix`, `ledMatrixOn`, `ledMatrixRandom`, `ledRandom` |
| `horizontaldisplaymonitor` | `displaySetImageWithBuiltInDelay`, `displaySetMonitorFullscreen`, `displayWriteWithBuiltInDelay` |
| `horizontalbargraphmonitor` | `barGraphChangeValue`, `barGraphClearData`, `barGraphViewMode` |
| `horizontalevents` | `whenProgramStarts`, `whenBroadcast`, `broadcast`, `whenCloserThan`, `whenColor`, `whenPressed`, `whenTilted`, `whenLouderThan` |
| `horizontalcontrol` | `stopOtherStacks` |
| `horizontallight` | (LED control) |
| `horizontaldisplaymonitor` | (display monitor) |
| `horizontalsupermonitor` | (super monitor) |

### 13.4 Opcodes That Can Run Without Hub (Horizontal)

Source: module 83295, `I` (= `h.opcodesCanRunWithoutHubHorizontal`)

These opcodes run even when no hub is connected:
```
whenProgramStarts    stopOtherStacks      broadcast
whenBroadcast        whenLouderThan       recordSound
playRecordedSound    playAnimalSoundUntilDone
playEffectSoundUntilDone  playMusicSoundUntilDone
displaySetImageWithBuiltInDelay  displaySetMonitorFullscreen
displayWriteWithBuiltInDelay     barGraphChangeValue
barGraphClearData    barGraphViewMode
```

### 13.5 Sound Categories (Horizontal Mode)

Horizontal mode has three sound categories, each with their own shadow type:

| Category | Example sounds |
|----------|---------------|
| Animal sounds | Cat meow, Dog bark, ... |
| Effect sounds | Beep, Laser, ... |
| Music sounds | Drum beats, Notes, ... |


---

## 14. Default Constants & Clamping

### 14.1 Default State Values

Source: `rr` (DEFAULT_* constants) in main bundle

| Constant | Value | Description |
|---------|-------|-------------|
| `DEFAULT_VOLUME` | 100 | Default beep/sound volume % |
| `DEFAULT_SPEED` | 75 | Default motor speed % |
| `DEFAULT_MOVE_SPEED` | 50 | Default movement pair speed % |
| `DEFAULT_MOVE_PAIR` | `["A", "B"]` | Default motor port pair |
| `DEFAULT_MOTOR_STALL` | `true` | Stall detection on by default |
| `DEFAULT_MOTOR_STOP` | `MotorStop.Brake` (=1) | Default stop method |
| `DEFAULT_MOTOR_LAST_STATUS` | 0 | No status yet |
| `DEFAULT_MOVE_LAST_STATUS` | 0 | No status yet |
| `DEFAULT_FLIPPER_MOVE_CALIBRATION` | 17.5 | cm per rotation (SPIKE Prime) |
| `DEFAULT_GECKO_MOVE_CALIBRATION` | 13.5 | cm per rotation (Essential/BLE) |

### 14.2 Clamping Functions (bt object)

Source: `bt` utilities in main bundle

| Function | Formula | Description |
|---------|---------|-------------|
| `bt.clampSpeed(v)` | `Math.round(clamp(v, -100, 100))` | Speed percent -100..100 |
| `bt.clampAcceleration(v)` | `Math.round(clamp(v, 0, 10000))` | Acceleration ms 0..10000 |
| `bt.clampIntMax(v)` | `clamp(v, -2147483647, 2147483647)` | Int32 range |
| `bt.clamp(v, lo, hi)` | `Math.max(lo, Math.min(hi, v))` | Generic clamp |
| `bt.convertBrightnessScale(v, max=9)` | `Math.round(clamp(v,0,100) * max / 100)` | 0–100% → 0–9 brightness |

### 14.3 Key Numeric Constants

| Constant | Value | Description |
|---------|-------|-------------|
| `T0` | 3,600,000 | Max degrees value (10,000 rotations) |
| Max time | 60,000 ms | Max time for motor/move blocks (60 s) |
| Min time | 0 ms | Minimum time |
| Max beep note | MIDI 120+ | MIDI note range |
| `_tx` (tunnel buffer) | 1024 bytes | Transmit buffer size |
| `_nx` (throughput) | 256 bytes/sec | Tunnel rate limit |

### 14.4 Acceleration Field Format

The `ACCELERATION` block field is a space-separated two-integer string:
```
"accel_ms decel_ms"     e.g. "3000 3000"
```

Parsed by `setMoveAcceleration(targetId, accelStr)` and `setMotorAcceleration(targetId, port, accel, decel)`:
```javascript
const [n, o] = e.split(" ")
{
  acceleration: bt.clampAcceleration(sr.toNumber(n)),
  deceleration: bt.clampAcceleration(sr.toNumber(o))
}
```

These values are passed directly as `{acceleration: N, deceleration: N}` in RPC params.

### 14.5 Display Monitor Default State

```jsonc
{
  "programStartTime": undefined,
  "programStopTime": undefined,
  "projectType": undefined,
  "display": {
    "visible": false,
    "viewMode": "In window",      // ViewMode.Window
    "type": "image",              // DisplayType.Image
    "content": "",
    "hideImage": false,
    "includedImages": [11],       // DisplayImage.Beach
    "showImageSelector": false
  },
  "linegraph": {
    "visible": false,
    "viewMode": "In window",
    "lineVariant": 0,             // LineVariant.Line
    "data": [],
    "splitMode": 0,               // SplitMode.CombinedView
    "yAxisMode": 0,               // YAxisMode.Single
    "resetTimerTime": undefined
  },
  "bargraph": {
    "visible": false,
    "viewMode": "In window",
    "data": {
      "0": 0,    // Red
      "1": 0,    // Yellow
      "2": 0,    // Azure
      "3": 0,    // Blue
      "4": 0,    // Green
      "5": 0     // Violet
    }
  }
}
```

---

## 15. Extension IDs

The `extensions` array in `projectbody.json` and `manifest.json` lists which SPIKE extensions the project uses.

### 15.1 Word Block Extension IDs

Source: module 67117 (`ExtensionIds`)

| Extension ID | Description |
|-------------|-------------|
| `"flippermotor"` | Motor control (Turn/GoTo/Start/Stop/Speed) |
| `"flippermoremotor"` | Advanced motor (GoToRelative, SetDegreeCounted) |
| `"flippermove"` | Movement pair control |
| `"flippersensors"` | Color/Distance/Force sensors |
| `"flipperevents"` | Event/hat blocks |
| `"flipperlight"` | Hub LED + ultrasonic lights |
| `"flipperdisplay"` | 5x5 LED matrix display |
| `"flippersound"` | Sound/beep playback |
| `"flipperimu"` | IMU / orientation / gestures |
| `"flippermore"` | Misc: port, stopOtherStacks, assert |
| `"flippermorecolor"` | Color matrix accessory |

### 15.2 Horizontal Extension IDs

Source: module 21588 (`HorizontalExtensionIds`)

```
"horizontalmotor"        "horizontalmove"
"horizontalsound"        "horizontaldisplay"
"horizontaldisplaymonitor"  "horizontalbargraphmonitor"
"horizontalevents"       "horizontalcontrol"
"horizontallight"        "horizontalsupermonitor"
"horizontalany"
```

### 15.3 Extension Prefix

The horizontal extension prefix string: `"horizontal"` — used to distinguish vertical vs horizontal block namespaces.

---

## 16. Project Migration

The app performs automatic migrations on older project files when loading.

### 16.1 currentProjectVersion

The current project version expected by the JS engine is exported from module 95880 as `currentProjectVersion`.

### 16.2 Migration Functions

| Function | Description |
|---------|-------------|
| `runSb3Migrations(sb3)` | Migrate sb3 JSON to current schema |
| `runXmlSnippetMigrations(xml)` | Migrate embedded XML block programs |

These handle:
- Adding new required fields (acceleration, stallDetection)
- Renaming opcodes (e.g. old motor opcodes → new ones)
- Adjusting block argument names across version bumps
- blockversion attribute updates (9→10→23)

---

## 17. Summary: Data Flow Cheat Sheet

```
User places block in editor
        |
        v (Blockly XML serialization)
<block type="flippermotor_motorTurnForDirection">
  <field name="DIRECTION">forward</field>
  <value name="VALUE"><shadow type="math_number">
    <field name="NUM">90</field>
  </shadow></value>
</block>
        |
        v (saved to .llsp3 ZIP)
projectbody.json → { targets: [ { blocks: { "id": {
  opcode: "flippermotor_motorTurnForDirection",
  fields: { DIRECTION: ["forward", null] },
  inputs: { VALUE: [1, "shadowId"] }
} } } ] }
        |
        v (run button pressed)
jw["flippermotor_motorTurnForDirection"](args, ctx, E0)
  -> reads args.DIRECTION = "forward"
  -> reads args.UNIT = "degrees"
  -> reads VALUE input = 90
  -> calls MQ("degrees", "forward", speed=75, value=90,
              motorState, accelerationObj)
  -> returns { method: "scratch.motor_run_for_degrees",
               params: { port:"A", speed:75, degrees:90,
                         stall:true, stop:1,
                         acceleration:3000, deceleration:3000 } }
        |
        v
cge.send("scratch.motor_run_for_degrees",
  { values: { port:"A", ... }, version: "18.0.1" })
        |
        v WebSocket ws://localhost:2846
Swift native app
        |
        v USB serial / BLE GATT
SPIKE Prime Hub MicroPython
  -> hub.port.A.motor.run_for_degrees(90, 75, ...)
```

