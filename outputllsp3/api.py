"""High-level authoring facades built on top of ``LLSP3Project``.

Each facade is a frozen dataclass wrapping a ``project`` reference.  They
provide domain-specific helpers that generate the correct Scratch blocks without
requiring callers to know opcode names or block-field layouts.

Facade classes
--------------
- ``VarsAPI``        – variable declare / get / set / change
- ``ListsAPI``       – list declare, append, clear, item, contains, setitem, delete, insert
- ``OpsAPI``         – arithmetic, comparison, string, boolean operators, random, round, mathop
- ``WaitAPI``        – wait-for-seconds / wait-for-milliseconds blocks
- ``SensorAPI``      – IMU axes, timer, loudness, button, color, distance, force, reflectivity
- ``MotorAPI``       – individual motor control (run, stop, run_for_degrees, speed, …)
- ``MoveAPI``        – drive-base control (forward, turn, pair setup, steer, …)
- ``LightAPI``       – 5×5 display (show_text, show_image, set_pixel, clear, …)
- ``SoundAPI``       – speaker (beep, play, stop, …)
- ``FlowAPI``        – alias for :class:`flow.FlowBuilder` (procedure, call, if, loops, …)
- ``DrivebaseAPI``   – PID-runtime installer and high-level robot helpers
- ``RobotAPI``       – high-level robot API (straight_cm, turn_deg, pivot, stop, …)

Aggregate
---------
- ``API``       – top-level dataclass combining all sub-facades; also exposes
  short aliases ``v/o/m/s/f/db/e`` for interactive use and a
  ``namespace()`` context-manager for temporary scoped variable prefixing.
- ``RobotAPI``  – re-exported from the drivebase layer for convenience.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from contextlib import contextmanager
import inspect
from math import pi
from typing import Any

from .enums import ENUMS
from .wrapper import ScratchWrapper
from .spikepython import SpikePythonAPI


@dataclass
class VarsAPI:
    """Variable facade.

    Use this when you want explicit control over namespaced variables.
    For most robot programs, `add/get/set/change` are enough.
    """
    project: Any

    def add(self, name: str, value: Any = 0, *, namespace: str | None = None, raw: bool = False) -> str:
        try:
            return self.project.variable_id(name, namespace=namespace, raw=raw)
        except Exception:
            return self.project.add_variable(name, value, namespace=namespace, raw=raw)


    def ensure(self, name: str, value: Any = 0, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.add(name, value, namespace=namespace, raw=raw)

    def add_many(self, mapping: dict[str, Any], *, namespace: str | None = None, raw: bool = False) -> dict[str, str]:
        return {name: self.add(name, value, namespace=namespace, raw=raw) for name, value in mapping.items()}
    def get(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str: return self.project.variable(name, namespace=namespace, raw=raw)
    def set(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self.project.set_variable(name, value, namespace=namespace, raw=raw)
    def change(self, name: str, value: Any, *, namespace: str | None = None, raw: bool = False) -> str: return self.project.change_variable(name, value, namespace=namespace, raw=raw)


@dataclass
class ListsAPI:
    """List facade. Lists are declared resources like variables, but list operations return blocks.

    Canonical methods: ``add``, ``ensure``, ``append``, ``clear``, ``length``,
    ``get_item``, ``set_item``, ``delete_item``, ``insert_item``, ``contains``.
    Old names (``item``, ``setitem``, ``delete``, ``insert``) are deprecated.
    """
    project: Any

    def add(self, name: str, value: list[Any] | None = None, *, namespace: str | None = None, raw: bool = False) -> str:
        try:
            return self.project.list_id(name, namespace=namespace, raw=raw)
        except Exception:
            return self.project.add_list(name, value or [], namespace=namespace, raw=raw)

    def ensure(self, name: str, value: list[Any] | None = None, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.add(name, value=value, namespace=namespace, raw=raw)

    def append(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_append(name, item, namespace=namespace, raw=raw)

    def clear(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_clear(name, namespace=namespace, raw=raw)

    def length(self, name: str, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_length(name, namespace=namespace, raw=raw)

    def get_item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_item(name, index, namespace=namespace, raw=raw)

    def item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        warnings.warn("item() is deprecated; use get_item()", DeprecationWarning, stacklevel=2)
        return self.get_item(name, index, namespace=namespace, raw=raw)

    def contains(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_contains(name, item, namespace=namespace, raw=raw)

    def set_item(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_replace(name, index, item, namespace=namespace, raw=raw)

    def setitem(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        warnings.warn("setitem() is deprecated; use set_item()", DeprecationWarning, stacklevel=2)
        return self.set_item(name, index, item, namespace=namespace, raw=raw)

    def delete_item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_delete(name, index, namespace=namespace, raw=raw)

    def delete(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        warnings.warn("delete() is deprecated; use delete_item()", DeprecationWarning, stacklevel=2)
        return self.delete_item(name, index, namespace=namespace, raw=raw)

    def insert_item(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_insert(name, index, item, namespace=namespace, raw=raw)

    def insert(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        warnings.warn("insert() is deprecated; use insert_item()", DeprecationWarning, stacklevel=2)
        return self.insert_item(name, index, item, namespace=namespace, raw=raw)


@dataclass
class OpsAPI:
    """Arithmetic, comparison, string, and boolean operator facade."""
    project: Any

    def add(self, a: Any, b: Any) -> str: return self.project.add(a, b)
    def sub(self, a: Any, b: Any) -> str: return self.project.sub(a, b)
    def mul(self, a: Any, b: Any) -> str: return self.project.mul(a, b)
    def div(self, a: Any, b: Any) -> str: return self.project.div(a, b)
    def mod(self, a: Any, b: Any) -> str: return self.project.mod(a, b)
    def lt(self, a: Any, b: Any) -> str: return self.project.lt(a, b)
    def gt(self, a: Any, b: Any) -> str: return self.project.gt(a, b)
    def eq(self, a: Any, b: Any) -> str: return self.project.eq(a, b)
    def or_(self, a: Any, b: Any) -> str: return self.project.or_(a, b)
    def and_(self, a: Any, b: Any) -> str: return self.project.and_(a, b)
    def not_(self, value: Any) -> str: return self.project.not_(value)
    def abs(self, value: Any) -> str: return self.project.mathop("abs", value)
    def round(self, value: Any) -> str: return self.project.round_(value)
    def join(self, a: Any, b: Any) -> str: return self.project.join(a, b)
    def length_of(self, value: Any) -> str: return self.project.length_of(value)
    def letter_of(self, index: Any, value: Any) -> str: return self.project.letter_of(index, value)
    def str_contains(self, string: Any, substring: Any) -> str: return self.project.str_contains(string, substring)
    def random(self, from_: Any, to: Any) -> str: return self.project.random(from_, to)
    def mathop(self, op: str, value: Any) -> str: return self.project.mathop(op, value)


@dataclass
class MoveAPI:
    """Drive-base facade for the most common pair-drive actions."""
    project: Any
    _wrapper: Any = None

    def _w(self):
        if self._wrapper is None:
            from .wrapper import ScratchWrapper
            self._wrapper = ScratchWrapper(self.project)
        return self._wrapper

    def set_pair(self, pair: str = "AB") -> str: return self.project.set_movement_pair(str(pair))

    def set_motor_pair(self, pair: str = "AB") -> str:
        warnings.warn("set_motor_pair() is deprecated; use set_pair()", DeprecationWarning, stacklevel=2)
        return self.set_pair(pair)

    def pair(self, pair: str = "AB") -> str:
        warnings.warn("pair() is deprecated; use set_pair()", DeprecationWarning, stacklevel=2)
        return self.set_pair(pair)

    def dual_speed(self, left: Any, right: Any) -> str: return self.project.start_dual_speed(left, right)

    def start_dual_speed(self, left: Any, right: Any) -> str:
        warnings.warn("start_dual_speed() is deprecated; use dual_speed()", DeprecationWarning, stacklevel=2)
        return self.dual_speed(left, right)

    def dual_power(self, left: Any, right: Any) -> str: return self.project.start_dual_power(left, right)

    def start_dual_power(self, left: Any, right: Any) -> str:
        warnings.warn("start_dual_power() is deprecated; use dual_power()", DeprecationWarning, stacklevel=2)
        return self.dual_power(left, right)

    def stop(self) -> str: return self.project.stop_moving()

    def stop_move(self) -> str:
        warnings.warn("stop_move() is deprecated; use stop()", DeprecationWarning, stacklevel=2)
        return self.stop()
    def steer(self, steering: Any, speed: Any) -> str: return self._w().flippermoremove.start_steer_at_speed(STEERING=steering, SPEED=speed)
    def steer_for_distance(self, steering: Any, distance: Any, speed: Any, unit: str = "degrees") -> str: return self._w().flippermoremove.steer_distance_at_speed(STEERING=steering, DISTANCE=distance, UNIT=unit, SPEED=speed)


@dataclass
class SensorAPI:
    """Sensor facade for IMU, button, color, distance, force, and timer."""
    project: Any
    _wrapper: Any = None

    def _w(self):
        if self._wrapper is None:
            from .wrapper import ScratchWrapper
            self._wrapper = ScratchWrapper(self.project)
        return self._wrapper

    def reset_yaw(self) -> str: return self.project.reset_yaw()
    def reset(self) -> str: return self.reset_yaw()
    def angle(self, axis: Any = ENUMS.OrientationAxis.YAW) -> str:
        if str(axis) == "yaw":
            return self.project.yaw()
        return self.project.add_block("flippersensors_orientationAxis", fields={"AXIS": [str(axis), None]})
    def yaw(self) -> str: return self.angle(ENUMS.OrientationAxis.YAW)
    def pitch(self) -> str: return self.angle(ENUMS.OrientationAxis.PITCH)
    def roll(self) -> str: return self.angle(ENUMS.OrientationAxis.ROLL)
    def timer(self) -> str: return self._w().flippersensors.timer()
    def reset_timer(self) -> str: return self._w().flippersensors.reset_timer()
    def loudness(self) -> str: return self._w().flippersensors.loudness()
    def button_pressed(self, button: str = "center") -> str: return self._w().flippersensors.button_is_pressed(BUTTON=button, EVENT="pressed")
    def color(self, port: Any) -> str: return self._w().flippersensors.color(PORT=str(port))
    def is_color(self, port: Any, value: Any) -> str: return self._w().flippersensors.is_color(PORT=str(port), VALUE=value)
    def distance(self, port: Any) -> str: return self._w().flippersensors.distance(PORT=str(port))
    def is_distance(self, port: Any, comparator: Any, value: Any) -> str: return self._w().flippersensors.is_distance(PORT=str(port), COMPARATOR=comparator, VALUE=value)
    def force(self, port: Any) -> str: return self._w().flippersensors.force(PORT=str(port))
    def is_pressed(self, port: Any) -> str: return self._w().flippersensors.is_pressed(PORT=str(port), OPTION="pressed")
    def reflectivity(self, port: Any) -> str: return self._w().flippersensors.reflectivity(PORT=str(port))


@dataclass
class MotorAPI:
    """Individual motor facade backed by project helpers and the wrapper."""
    project: Any
    _wrapper: Any = None

    def _w(self):
        if self._wrapper is None:
            from .wrapper import ScratchWrapper
            self._wrapper = ScratchWrapper(self.project)
        return self._wrapper

    def relative_position(self, port: Any) -> str: return self.project.motor_relative_position(str(port))
    def set_relative_position(self, port: Any, value: Any) -> str: return self.project.motor_set_relative_position(str(port), value)
    def reset_relative_position(self, port: Any, value: Any = 0) -> str: return self.set_relative_position(port, value)
    def run(self, port: Any, speed: Any) -> str: return self._w().flippermoremotor.motor_start_speed(PORT=str(port), SPEED=speed)
    def run_power(self, port: Any, power: Any) -> str: return self._w().flippermoremotor.motor_start_power(PORT=str(port), POWER=power)
    def stop(self, port: Any) -> str: return self._w().flippermotor.motor_stop(PORT=str(port))
    def run_for_degrees(self, port: Any, degrees: Any, speed: Any) -> str: return self._w().flippermoremotor.motor_turn_for_speed(PORT=str(port), VALUE=degrees, UNIT="degrees", SPEED=speed)
    def run_for_seconds(self, port: Any, seconds: Any, speed: Any) -> str: return self._w().flippermoremotor.motor_turn_for_speed(PORT=str(port), VALUE=seconds, UNIT="seconds", SPEED=speed)
    def set_stop_mode(self, port: Any, mode: str = "brake") -> str: return self._w().flippermoremotor.motor_set_stop_method(PORT=str(port), STOP=mode)
    def run_for_direction(self, port: Any, direction: Any, value: Any, unit: str = "degrees") -> str:
        """Run motor for a given amount in a given direction (no speed arg — uses configured speed)."""
        return self._w().flippermotor.motor_turn_for_direction(PORT=str(port), DIRECTION=str(direction), VALUE=value, UNIT=unit)
    def go_to_position(self, port: Any, direction: Any, position: Any) -> str:
        """Move motor to an absolute position via the given direction."""
        return self._w().flippermotor.motor_go_direction_to_position(PORT=str(port), DIRECTION=str(direction), VALUE=position, UNIT="degrees")
    def absolute_position(self, port: Any) -> str: return self._w().flippermotor.absolute_position(PORT=str(port))
    def speed(self, port: Any) -> str: return self._w().flippermotor.speed(PORT=str(port))


@dataclass
class WaitAPI:
    """Timing facade.

    Use `wait.ms(...)` for SPIKE-style sleeps or `wait.seconds(...)` for direct control.
    """
    project: Any
    def seconds(self, value: Any) -> str:
        """Emit a ``control_wait`` block.  *value* may be a float literal or
        a block ID returned from an arithmetic expression builder."""
        return self.project.wait(value)

    def ms(self, value: Any) -> str:
        """Emit a ``control_wait`` block for *value* milliseconds.

        *value* may be an integer literal **or** a block ID (e.g. the result
        of ``ops.mul(...)`` or a variable reporter).  Block IDs are converted
        to seconds automatically via a ``/ 1000`` operator block; literals are
        divided in Python at build time.
        """
        if isinstance(value, str) and value in self.project.blocks:
            return self.project.wait(self.project.div(value, 1000))
        return self.project.wait(float(value) / 1000.0)

    def sleep(self, value: float) -> str:
        warnings.warn("sleep() is deprecated; use seconds()", DeprecationWarning, stacklevel=2)
        return self.seconds(value)

    def sleep_ms(self, value: int) -> str:
        warnings.warn("sleep_ms() is deprecated; use ms()", DeprecationWarning, stacklevel=2)
        return self.ms(value)

    def __call__(self, value: float) -> str: return self.seconds(value)


@dataclass
class LightAPI:
    """Display / light-matrix facade for the SPIKE hub 5×5 display."""
    project: Any
    _wrapper: Any = None

    def _w(self):
        if self._wrapper is None:
            from .wrapper import ScratchWrapper
            self._wrapper = ScratchWrapper(self.project)
        return self._wrapper

    def show_text(self, text: Any) -> str: return self._w().flipperlight.light_display_text(TEXT=text)
    def show_image(self, image: Any) -> str: return self._w().flipperlight.light_display_image_on(MATRIX=str(image))
    def show_image_for(self, image: Any, seconds: Any) -> str: return self._w().flipperlight.light_display_image_on_for_time(MATRIX=str(image), VALUE=seconds)
    def set_pixel(self, x: Any, y: Any, brightness: Any) -> str: return self._w().flipperlight.light_display_set_pixel(X=x, Y=y, BRIGHTNESS=brightness)
    def clear(self) -> str: return self._w().flipperlight.light_display_off()
    def set_brightness(self, brightness: Any) -> str: return self._w().flipperlight.light_display_set_brightness(BRIGHTNESS=brightness)
    def set_center_button(self, color: Any) -> str: return self._w().flipperlight.center_button_light(COLOR=color)


@dataclass
class SoundAPI:
    """Sound facade for the SPIKE hub speaker."""
    project: Any
    _wrapper: Any = None

    def _w(self):
        if self._wrapper is None:
            from .wrapper import ScratchWrapper
            self._wrapper = ScratchWrapper(self.project)
        return self._wrapper

    def beep(self, note: Any = 60) -> str: return self._w().flippersound.beep(NOTE=note)
    def beep_for(self, note: Any, seconds: Any) -> str: return self._w().flippersound.beep_for_time(NOTE=note, DURATION=seconds)
    def play(self, sound: Any) -> str: return self._w().flippersound.play_sound(SOUND=sound)
    def play_until_done(self, sound: Any) -> str: return self._w().flippersound.play_sound_until_done(SOUND=sound)
    def stop(self) -> str: return self._w().flippersound.stop_sound()


@dataclass
class DrivebaseAPI:
    """High-level drivebase facade.

    `install_pid_runtime()` injects a reusable set of procedures for straight drive,
    turning, and pivots. This is the quickest way to bootstrap a robot program.
    """
    project: Any
    api: Any

    def install_pid_runtime(
        self,
        *,
        motor_pair: str = "AB",
        wheel_diameter_mm: float = 62.4,
        left_dir: int = 1,
        right_dir: int = -1,
        kp_straight: float = 22.0,
        ki_straight: float = 0.0,
        kd_straight: float = 34.0,
        kp_turn: float = 10.0,
        ki_turn: float = 0.0,
        kd_turn: float = 18.0,
        kd_alpha: float = 1.0,
        integral_max: float = 150.0,
        speed_mid: int = 420,
        speed_turn: int = 260,
        speed_pivot: int = 220,
    ) -> dict[str, str]:
        """Install PID drivebase runtime procedures.

        Parameters
        ----------
        kp_straight / ki_straight / kd_straight:
            PID gains for straight-line heading correction.  ``ki`` defaults
            to 0 (pure PD) — enable only when you need steady-state correction.
        kp_turn / ki_turn / kd_turn:
            PID gains for tank-turn and pivot manoeuvres.
        kd_alpha:
            EMA smoothing factor for the derivative term (0 < alpha ≤ 1).
            ``1.0`` (default) = no smoothing; ``0.3`` = heavy low-pass filter.
            Lower values reduce sensor noise amplification at the cost of
            slightly slower derivative response.
        integral_max:
            Anti-windup clamp: INTEGRAL is clamped to ``[-integral_max,
            integral_max]`` every tick.  Prevents runaway accumulation.
        speed_mid / speed_turn / speed_pivot:
            Default operating speeds (deg/s) stored as SPIKE variables so
            they can be adjusted at run-time without recompiling.
        """
        P = self.project
        flow = self.api.flow
        vars = self.api.vars
        ops = self.api.ops
        move = self.api.move
        sensor = self.api.sensor
        motor = self.api.motor
        wait = self.api.wait

        var_ns = self.api.current_namespace()

        for name, value in {
            "LEFT_DIR":              left_dir,
            "RIGHT_DIR":             right_dir,
            "DRIVE_FACTOR_DEG_PER_CM": (3600 / (pi * wheel_diameter_mm)),
            "KP_STRAIGHT":           kp_straight,
            "KI_STRAIGHT":           ki_straight,
            "KD_STRAIGHT":           kd_straight,
            "KP_TURN":               kp_turn,
            "KI_TURN":               ki_turn,
            "KD_TURN":               kd_turn,
            "KD_ALPHA":              kd_alpha,
            "INTEGRAL_MAX":          integral_max,
            "TURN_TOLERANCE_DEG":    1.2,
            "TARGET_HEADING":        0,
            "TOTAL_DEG":             0,
            "TRAVELED":              0,
            "ERROR":                 0,
            "LAST_ERROR":            0,
            "DERIVATIVE":            0,
            "DERIV_SMOOTH":          0,
            "INTEGRAL":              0,
            "CORRECTION":            0,
            "BASE":                  0,
            "LEFT_SPEED":            0,
            "RIGHT_SPEED":           0,
            "CMD":                   0,
            "SPEED_MID":             speed_mid,
            "SPEED_TURN":            speed_turn,
            "SPEED_PIVOT":           speed_pivot,
        }.items():
            vars.add(name, value, namespace=var_ns)

        def V(name: str) -> str: return vars.get(name, namespace=var_ns)
        def SET(name: str, value: Any) -> str: return vars.set(name, value, namespace=var_ns)
        def ARG(name: str) -> str: return P.arg(name)
        def ABS(x: Any) -> str: return ops.abs(x)
        def ADD(a: Any, b: Any) -> str: return ops.add(a, b)
        def SUB(a: Any, b: Any) -> str: return ops.sub(a, b)
        def MUL(a: Any, b: Any) -> str: return ops.mul(a, b)
        def DIV(a: Any, b: Any) -> str: return ops.div(a, b)
        def GT(a: Any, b: Any) -> str: return ops.gt(a, b)
        def LT(a: Any, b: Any) -> str: return ops.lt(a, b)

        # === Procedure 1: SetDriveSpeed ===
        flow.procedure(
            "SetDriveSpeed", ["left_speed", "right_speed"],
            SET("LEFT_SPEED", MUL(ARG("left_speed"), V("LEFT_DIR"))),
            SET("RIGHT_SPEED", MUL(ARG("right_speed"), V("RIGHT_DIR"))),
            move.dual_speed(V("LEFT_SPEED"), V("RIGHT_SPEED")),
            x=700, y=120,
        )

        # === Procedure 2: StopDrive ===
        flow.procedure("StopDrive", [], move.stop(), x=700, y=300)

        # === Procedure 3: ResetDrive ===
        flow.procedure(
            "ResetDrive", [],
            sensor.reset_yaw(),
            motor.set_relative_position("A", 0),
            motor.set_relative_position("B", 0),
            x=700, y=450,
        )

        # === Procedure 4: MoveStraightDeg — PID heading-hold loop ===
        #
        # Each iteration:
        #   1. Measure distance traveled (avg of both encoder absolutes).
        #   2. Error  = TARGET_HEADING − yaw.
        #   3. Raw derivative = ERROR − LAST_ERROR.
        #   4. EMA-smoothed derivative: DERIV_SMOOTH += (raw − DERIV_SMOOTH) × KD_ALPHA.
        #      α=1 → no filtering; α<1 → exponential low-pass (reduces noise).
        #   5. Integral with anti-windup: clamp to ±INTEGRAL_MAX.
        #   6. CORRECTION = Kp×E + Ki×I + Kd×DERIV_SMOOTH.
        #   7. Clamp CORRECTION to [−BASE, BASE] — prevents wheel reversal.
        #   8. Apply differential: left += correction, right −= correction.
        loop_body = [
            SET("TRAVELED", DIV(
                ADD(ABS(motor.relative_position("A")), ABS(motor.relative_position("B"))), 2)),
            SET("ERROR", SUB(V("TARGET_HEADING"), sensor.angle())),
            SET("DERIVATIVE", SUB(V("ERROR"), V("LAST_ERROR"))),
            SET("DERIV_SMOOTH", ADD(V("DERIV_SMOOTH"),
                                   MUL(SUB(V("DERIVATIVE"), V("DERIV_SMOOTH")), V("KD_ALPHA")))),
            SET("INTEGRAL", ADD(V("INTEGRAL"), V("ERROR"))),
            flow.if_(GT(V("INTEGRAL"),  V("INTEGRAL_MAX")),  SET("INTEGRAL",  V("INTEGRAL_MAX"))),
            flow.if_(LT(V("INTEGRAL"), SUB(0, V("INTEGRAL_MAX"))), SET("INTEGRAL", SUB(0, V("INTEGRAL_MAX")))),
            SET("CORRECTION", ADD(
                ADD(MUL(V("KP_STRAIGHT"), V("ERROR")), MUL(V("KI_STRAIGHT"), V("INTEGRAL"))),
                MUL(V("KD_STRAIGHT"), V("DERIV_SMOOTH")))),
            SET("BASE", ARG("drive_speed")),
            flow.if_(GT(V("CORRECTION"),  V("BASE")),         SET("CORRECTION",  V("BASE"))),
            flow.if_(LT(V("CORRECTION"), SUB(0, V("BASE"))), SET("CORRECTION", SUB(0, V("BASE")))),
            SET("LEFT_SPEED",  ADD(V("BASE"), V("CORRECTION"))),
            SET("RIGHT_SPEED", SUB(V("BASE"), V("CORRECTION"))),
            flow.call("SetDriveSpeed", V("LEFT_SPEED"), V("RIGHT_SPEED")),
            SET("LAST_ERROR", V("ERROR")),
            wait.ms(20),
        ]
        flow.procedure(
            "MoveStraightDeg", ["target_deg", "drive_speed"],
            flow.call("ResetDrive"),
            wait.ms(80),
            SET("TARGET_HEADING", sensor.angle()),
            SET("TOTAL_DEG", ABS(ARG("target_deg"))),
            SET("LAST_ERROR",   0),
            SET("DERIV_SMOOTH", 0),
            SET("INTEGRAL",     0),
            flow.repeat_until(GT(V("TRAVELED"), V("TOTAL_DEG")), *loop_body),
            flow.call("StopDrive"),
            x=700, y=700,
        )

        # === Procedure 5: MoveStraightCm ===
        flow.procedure(
            "MoveStraightCm", ["distance_cm", "drive_speed"],
            flow.call("MoveStraightDeg",
                      MUL(ARG("distance_cm"), V("DRIVE_FACTOR_DEG_PER_CM")),
                      ARG("drive_speed")),
            x=700, y=1120,
        )

        # === Procedure 6: TurnDeg — tank-turn PID loop ===
        #
        # Same EMA + integral structure as the straight loop, but both motors
        # run in opposite directions.  LAST_ERROR is pre-seeded so the first
        # derivative is 0 rather than a spike.
        turn_body = [
            SET("ERROR", SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIVATIVE", SUB(V("ERROR"), V("LAST_ERROR"))),
            SET("DERIV_SMOOTH", ADD(V("DERIV_SMOOTH"),
                                   MUL(SUB(V("DERIVATIVE"), V("DERIV_SMOOTH")), V("KD_ALPHA")))),
            SET("INTEGRAL", ADD(V("INTEGRAL"), V("ERROR"))),
            flow.if_(GT(V("INTEGRAL"),  V("INTEGRAL_MAX")),  SET("INTEGRAL",  V("INTEGRAL_MAX"))),
            flow.if_(LT(V("INTEGRAL"), SUB(0, V("INTEGRAL_MAX"))), SET("INTEGRAL", SUB(0, V("INTEGRAL_MAX")))),
            SET("CMD", ADD(
                ADD(MUL(V("KP_TURN"), V("ERROR")), MUL(V("KI_TURN"), V("INTEGRAL"))),
                MUL(V("KD_TURN"), V("DERIV_SMOOTH")))),
            flow.call("SetDriveSpeed", SUB(0, V("CMD")), V("CMD")),
            SET("LAST_ERROR", V("ERROR")),
            wait.ms(20),
        ]
        flow.procedure(
            "TurnDeg", ["target_angle_deg", "max_speed"],
            sensor.reset_yaw(),
            wait.ms(80),
            SET("LAST_ERROR",   SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIV_SMOOTH", 0),
            SET("INTEGRAL",     0),
            flow.repeat_until(
                LT(ABS(SUB(ARG("target_angle_deg"), sensor.angle())), V("TURN_TOLERANCE_DEG")),
                *turn_body),
            flow.call("StopDrive"),
            x=700, y=1360,
        )

        # === Procedures 7 & 8: PivotLeftDeg / PivotRightDeg — single-motor PD ===
        #
        # Replaced open-loop (constant speed until tolerance) with PD control:
        # CMD scales naturally to zero as the robot approaches the target angle,
        # reducing overshoot without needing manual speed tuning.  Reuses the
        # turn gains (KP_TURN / KD_TURN) since the angular dynamics are similar.
        pivot_left_body = [
            SET("ERROR", SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIVATIVE", SUB(V("ERROR"), V("LAST_ERROR"))),
            SET("DERIV_SMOOTH", ADD(V("DERIV_SMOOTH"),
                                   MUL(SUB(V("DERIVATIVE"), V("DERIV_SMOOTH")), V("KD_ALPHA")))),
            SET("CMD", ADD(MUL(V("KP_TURN"), V("ERROR")), MUL(V("KD_TURN"), V("DERIV_SMOOTH")))),
            flow.call("SetDriveSpeed", 0, V("CMD")),
            SET("LAST_ERROR", V("ERROR")),
            wait.ms(20),
        ]
        flow.procedure(
            "PivotLeftDeg", ["target_angle_deg", "max_speed"],
            sensor.reset_yaw(),
            wait.ms(80),
            SET("LAST_ERROR",   SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIV_SMOOTH", 0),
            flow.repeat_until(
                LT(ABS(SUB(ARG("target_angle_deg"), sensor.angle())), V("TURN_TOLERANCE_DEG")),
                *pivot_left_body),
            flow.call("StopDrive"),
            x=700, y=1690,
        )

        pivot_right_body = [
            SET("ERROR", SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIVATIVE", SUB(V("ERROR"), V("LAST_ERROR"))),
            SET("DERIV_SMOOTH", ADD(V("DERIV_SMOOTH"),
                                   MUL(SUB(V("DERIVATIVE"), V("DERIV_SMOOTH")), V("KD_ALPHA")))),
            SET("CMD", ADD(MUL(V("KP_TURN"), V("ERROR")), MUL(V("KD_TURN"), V("DERIV_SMOOTH")))),
            flow.call("SetDriveSpeed", V("CMD"), 0),
            SET("LAST_ERROR", V("ERROR")),
            wait.ms(20),
        ]
        flow.procedure(
            "PivotRightDeg", ["target_angle_deg", "max_speed"],
            sensor.reset_yaw(),
            wait.ms(80),
            SET("LAST_ERROR",   SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIV_SMOOTH", 0),
            flow.repeat_until(
                LT(ABS(SUB(ARG("target_angle_deg"), sensor.angle())), V("TURN_TOLERANCE_DEG")),
                *pivot_right_body),
            flow.call("StopDrive"),
            x=700, y=1960,
        )

        return {
            "motor_pair":        motor_pair,
            "move_straight_deg": "MoveStraightDeg",
            "move_straight_cm":  "MoveStraightCm",
            "turn_deg":          "TurnDeg",
            "pivot_left_deg":    "PivotLeftDeg",
            "pivot_right_deg":   "PivotRightDeg",
        }




@dataclass
class RobotAPI:
    """Higher-level robot facade focused on coding ergonomics.

    Typical workflow:
    - `api.r.install_pid(...)` once
    - `api.f.start(api.r.setup(), api.r.straight_cm(...), api.r.turn_deg(...))`

    This facade reduces repeated `flow.call(...)` boilerplate around the drivebase runtime.
    """
    project: Any
    api: Any
    _runtime_cache: dict[str, dict[str, Any]] | None = None

    def _cache(self) -> dict[str, dict[str, Any]]:
        if self._runtime_cache is None:
            self._runtime_cache = {}
        return self._runtime_cache

    def install_pid(self, **kwargs: Any) -> dict[str, Any]:
        ns = self.api.current_namespace()
        runtime = self.api.drivebase.install_pid_runtime(**kwargs)
        runtime = dict(runtime)
        runtime['namespace'] = ns
        runtime['pair'] = kwargs.get('motor_pair', 'AB')
        self._cache()[ns] = runtime
        return runtime

    def runtime(self) -> dict[str, Any]:
        ns = self.api.current_namespace()
        cache = self._cache()
        if ns not in cache:
            cache[ns] = {'namespace': ns, 'pair': 'AB', 'move_straight_cm': 'MoveStraightCm', 'move_straight_deg': 'MoveStraightDeg', 'turn_deg': 'TurnDeg', 'pivot_left_deg': 'PivotLeftDeg', 'pivot_right_deg': 'PivotRightDeg'}
        return cache[ns]

    def setup(self, pair: str | None = None) -> str:
        rt = self.runtime()
        return self.api.move.pair(pair or rt.get('pair', 'AB'))

    def straight_cm(self, distance_cm: Any, speed: Any | None = None) -> str:
        rt = self.runtime()
        speed = self.api.vars.get('SPEED_MID', namespace=rt['namespace']) if speed is None else speed
        return self.api.flow.call(rt['move_straight_cm'], distance_cm, speed)

    def straight_deg(self, target_deg: Any, speed: Any | None = None) -> str:
        rt = self.runtime()
        speed = self.api.vars.get('SPEED_MID', namespace=rt['namespace']) if speed is None else speed
        return self.api.flow.call(rt['move_straight_deg'], target_deg, speed)

    def turn_deg(self, angle_deg: Any, speed: Any | None = None) -> str:
        rt = self.runtime()
        speed = self.api.vars.get('SPEED_TURN', namespace=rt['namespace']) if speed is None else speed
        return self.api.flow.call(rt['turn_deg'], angle_deg, speed)

    def pivot_left_deg(self, angle_deg: Any, speed: Any | None = None) -> str:
        rt = self.runtime()
        speed = self.api.vars.get('SPEED_PIVOT', namespace=rt['namespace']) if speed is None else speed
        return self.api.flow.call(rt['pivot_left_deg'], angle_deg, speed)

    def pivot_right_deg(self, angle_deg: Any, speed: Any | None = None) -> str:
        rt = self.runtime()
        speed = self.api.vars.get('SPEED_PIVOT', namespace=rt['namespace']) if speed is None else speed
        return self.api.flow.call(rt['pivot_right_deg'], angle_deg, speed)

    def pause_ms(self, value: int) -> str:
        return self.api.wait.ms(value)

    def demo_square(self, cm: Any = 20, turns: int = 4) -> list[str]:
        seq = []
        for _ in range(int(turns)):
            seq.extend([self.straight_cm(cm), self.pause_ms(150), self.turn_deg(90), self.pause_ms(150)])
        return seq


@dataclass
class API:
    """Top-level facade container.

    Main entrypoints:
    - `api.spike` / `api.spikepython`
    - `api.wrapper` / `api.scratch`
    - `api.flow`
    - `api.vars`
    - `api.ops`
    - `api.light`
    - `api.sound`
    - `api.drivebase`
    """
    project: Any

    _namespace_override: str | None = None

    def current_namespace(self) -> str:
        if self._namespace_override:
            return self._namespace_override
        for frame_info in inspect.stack()[1:]:
            g = frame_info.frame.f_globals
            modname = g.get("__name__", "")
            if modname.startswith("outputllsp3"):
                continue
            base = str(g.get("__outputllsp3_namespace__", self.project.default_namespace))
            if getattr(self.project, "function_namespace_mode", False):
                fn = frame_info.function
                if fn and fn not in {"build", "<module>"}:
                    return self.project.sanitize_namespace(f"{base}__{fn}")
            return base
        return self.project.default_namespace

    @contextmanager
    def namespace(self, name: str):
        prev = self._namespace_override
        base = self.current_namespace()
        self._namespace_override = self.project.sanitize_namespace(f"{base}__{name}" if base else name)
        try:
            yield self._namespace_override
        finally:
            self._namespace_override = prev

    def __post_init__(self):
        from .flow import FlowBuilder
        from .project.layout import LayoutManager
        self.vars = VarsAPI(self.project)
        self.lists = ListsAPI(self.project)
        self.ops = OpsAPI(self.project)
        self.move = MoveAPI(self.project)
        self.sensor = SensorAPI(self.project)
        self.motor = MotorAPI(self.project)
        self.wait = WaitAPI(self.project)
        self.light = LightAPI(self.project)
        self.sound = SoundAPI(self.project)
        self.flow = FlowBuilder(self.project, LayoutManager())
        self.drivebase = DrivebaseAPI(self.project, self)
        self.wrapper = ScratchWrapper(self.project)
        self.scratch = self.wrapper
        self.spikepython = SpikePythonAPI(self.project, self.wrapper)
        self.spike = self.spikepython
        self.enums = ENUMS
        self.e = self.enums
        self.v = self.vars
        self.ls = self.lists
        self.o = self.ops
        self.m = self.move
        self.s = self.sensor
        self.motors = self.motor
        self.sleep = self.wait
        self.f = self.flow
        self.db = self.drivebase
        self.robot = RobotAPI(self.project, self)
        self.r = self.robot
        from .stdlib import StdLib
        self.stdlib = StdLib(self)

    def raw(self, opcode: str, **kwargs: Any) -> str:
        return self.project.add_block(opcode, **kwargs)

    def relayout(self) -> None:
        """Re-compute all top-level block positions based on actual stack depths.

        Call this after all blocks have been built to eliminate overlap and
        ensure procedures are arranged in a tidy grid.  Delegates to
        ``LayoutManager.relayout(project.blocks)``.
        """
        if self.flow.layout is not None:
            self.flow.layout.relayout(self.project.blocks)

    @property
    def layout(self):
        """The ``LayoutManager`` used by this API instance."""
        return self.flow.layout

    def seq(self, *items: Any) -> list[str]:
        return self.flow.seq(*items)

    def const(self, name: str, value: Any, *, namespace: str | None = None) -> str:
        return self.vars.add(name, value, namespace=namespace)

    def consts(self, mapping: dict[str, Any], *, namespace: str | None = None) -> dict[str, str]:
        return self.vars.add_many(mapping, namespace=namespace)

    def ns(self, name: str):
        return self.namespace(name)
