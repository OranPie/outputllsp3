from __future__ import annotations

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
    """List facade. Lists are declared resources like variables, but list operations return blocks."""
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

    def item(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_item(name, index, namespace=namespace, raw=raw)

    def contains(self, name: str, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_contains(name, item, namespace=namespace, raw=raw)

    def setitem(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_replace(name, index, item, namespace=namespace, raw=raw)

    def delete(self, name: str, index: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_delete(name, index, namespace=namespace, raw=raw)

    def insert(self, name: str, index: Any, item: Any, *, namespace: str | None = None, raw: bool = False) -> str:
        return self.project.list_insert(name, index, item, namespace=namespace, raw=raw)


@dataclass
class OpsAPI:
    """Arithmetic and comparison facade."""
    project: Any

    def add(self, a: Any, b: Any) -> str: return self.project.add(a, b)
    def sub(self, a: Any, b: Any) -> str: return self.project.sub(a, b)
    def mul(self, a: Any, b: Any) -> str: return self.project.mul(a, b)
    def div(self, a: Any, b: Any) -> str: return self.project.div(a, b)
    def lt(self, a: Any, b: Any) -> str: return self.project.lt(a, b)
    def gt(self, a: Any, b: Any) -> str: return self.project.gt(a, b)
    def eq(self, a: Any, b: Any) -> str: return self.project.eq(a, b)
    def or_(self, a: Any, b: Any) -> str: return self.project.or_(a, b)
    def and_(self, a: Any, b: Any) -> str: return self.project.and_(a, b)
    def not_(self, value: Any) -> str: return self.project.not_(value)
    def abs(self, value: Any) -> str: return self.project.mathop("abs", value)


@dataclass
class MoveAPI:
    """Drive-base facade for the most common pair-drive actions."""
    project: Any
    def set_pair(self, pair: str = "AB") -> str: return self.project.set_movement_pair(str(pair))
    def set_motor_pair(self, pair: str = "AB") -> str: return self.set_pair(pair)
    def pair(self, pair: str = "AB") -> str: return self.set_pair(pair)
    def dual_speed(self, left: Any, right: Any) -> str: return self.project.start_dual_speed(left, right)
    def start_dual_speed(self, left: Any, right: Any) -> str: return self.dual_speed(left, right)
    def dual_power(self, left: Any, right: Any) -> str: return self.project.start_dual_power(left, right)
    def start_dual_power(self, left: Any, right: Any) -> str: return self.dual_power(left, right)
    def stop(self) -> str: return self.project.stop_moving()
    def stop_move(self) -> str: return self.stop()


@dataclass
class SensorAPI:
    """Sensor facade with a convenience yaw helper."""
    project: Any
    def reset_yaw(self) -> str: return self.project.reset_yaw()
    def reset(self) -> str: return self.reset_yaw()
    def angle(self, axis: Any = ENUMS.OrientationAxis.YAW) -> str:
        if str(axis) == "yaw":
            return self.project.yaw()
        return self.project.add_block("flippersensors_orientationAxis", fields={"AXIS": [str(axis), None]})
    def yaw(self) -> str: return self.angle(ENUMS.OrientationAxis.YAW)


@dataclass
class MotorAPI:
    """Low-level motor facade backed by project helpers."""
    project: Any
    def relative_position(self, port: Any) -> str: return self.project.motor_relative_position(str(port))
    def set_relative_position(self, port: Any, value: Any) -> str: return self.project.motor_set_relative_position(str(port), value)
    def reset_relative_position(self, port: Any, value: Any = 0) -> str: return self.set_relative_position(port, value)


@dataclass
class WaitAPI:
    """Timing facade.

    Use `wait.ms(...)` for SPIKE-style sleeps or `wait.seconds(...)` for direct control.
    """
    project: Any
    def seconds(self, value: float) -> str: return self.project.wait(value)
    def ms(self, value: int) -> str: return self.project.wait(value / 1000.0)
    def sleep(self, value: float) -> str: return self.seconds(value)
    def sleep_ms(self, value: int) -> str: return self.ms(value)
    def __call__(self, value: float) -> str: return self.seconds(value)


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
        kd_straight: float = 34.0,
        kp_turn: float = 10.0,
        kd_turn: float = 18.0,
        speed_mid: int = 420,
        speed_turn: int = 260,
        speed_pivot: int = 220,
    ) -> dict[str, str]:
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
            "LEFT_DIR": left_dir,
            "RIGHT_DIR": right_dir,
            "DRIVE_FACTOR_DEG_PER_CM": (3600 / (pi * wheel_diameter_mm)),
            "KP_STRAIGHT": kp_straight,
            "KD_STRAIGHT": kd_straight,
            "KP_TURN": kp_turn,
            "KD_TURN": kd_turn,
            "TURN_TOLERANCE_DEG": 1.2,
            "TARGET_HEADING": 0,
            "TOTAL_DEG": 0,
            "TRAVELED": 0,
            "ERROR": 0,
            "LAST_ERROR": 0,
            "DERIVATIVE": 0,
            "CORRECTION": 0,
            "BASE": 0,
            "LEFT_SPEED": 0,
            "RIGHT_SPEED": 0,
            "CMD": 0,
            "SPEED_MID": speed_mid,
            "SPEED_TURN": speed_turn,
            "SPEED_PIVOT": speed_pivot,
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

        flow.procedure(
            "SetDriveSpeed", ["left_speed", "right_speed"],
            SET("LEFT_SPEED", MUL(ARG("left_speed"), V("LEFT_DIR"))),
            SET("RIGHT_SPEED", MUL(ARG("right_speed"), V("RIGHT_DIR"))),
            move.dual_speed(V("LEFT_SPEED"), V("RIGHT_SPEED")),
            x=700, y=120,
        )
        flow.procedure("StopDrive", [], move.stop(), x=700, y=300)
        flow.procedure("ResetDrive", [], sensor.reset_yaw(), motor.set_relative_position("A", 0), motor.set_relative_position("B", 0), x=700, y=450)
        loop_body = [
            SET("TRAVELED", DIV(ADD(ABS(motor.relative_position("A")), ABS(motor.relative_position("B"))), 2)),
            SET("ERROR", SUB(V("TARGET_HEADING"), sensor.angle())),
            SET("DERIVATIVE", SUB(V("ERROR"), V("LAST_ERROR"))),
            SET("CORRECTION", ADD(MUL(V("KP_STRAIGHT"), V("ERROR")), MUL(V("KD_STRAIGHT"), V("DERIVATIVE")))),
            SET("BASE", ARG("drive_speed")),
            SET("LEFT_SPEED", ADD(V("BASE"), V("CORRECTION"))),
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
            flow.repeat_until(GT(V("TRAVELED"), V("TOTAL_DEG")), *loop_body),
            flow.call("StopDrive"),
            x=700, y=700,
        )
        flow.procedure(
            "MoveStraightCm", ["distance_cm", "drive_speed"],
            flow.call("MoveStraightDeg", MUL(ARG("distance_cm"), V("DRIVE_FACTOR_DEG_PER_CM")), ARG("drive_speed")),
            x=700, y=1120,
        )
        turn_body = [
            SET("ERROR", SUB(ARG("target_angle_deg"), sensor.angle())),
            SET("DERIVATIVE", SUB(V("ERROR"), V("LAST_ERROR"))),
            SET("CMD", ADD(MUL(V("KP_TURN"), V("ERROR")), MUL(V("KD_TURN"), V("DERIVATIVE")))),
            flow.call("SetDriveSpeed", SUB(0, V("CMD")), V("CMD")),
            SET("LAST_ERROR", V("ERROR")),
            wait.ms(20),
        ]
        flow.procedure(
            "TurnDeg", ["target_angle_deg", "max_speed"],
            sensor.reset_yaw(),
            wait.ms(80),
            SET("LAST_ERROR", SUB(ARG("target_angle_deg"), sensor.angle())),
            flow.repeat_until(LT(ABS(SUB(ARG("target_angle_deg"), sensor.angle())), 1.2), *turn_body),
            flow.call("StopDrive"),
            x=700, y=1360,
        )
        flow.procedure(
            "PivotLeftDeg", ["target_angle_deg", "max_speed"],
            sensor.reset_yaw(),
            wait.ms(80),
            flow.repeat_until(LT(ABS(SUB(ARG("target_angle_deg"), sensor.angle())), 1.2), flow.call("SetDriveSpeed", 0, ARG("max_speed")), wait.ms(20)),
            flow.call("StopDrive"),
            x=700, y=1690,
        )
        flow.procedure(
            "PivotRightDeg", ["target_angle_deg", "max_speed"],
            sensor.reset_yaw(),
            wait.ms(80),
            flow.repeat_until(LT(ABS(SUB(ARG("target_angle_deg"), sensor.angle())), 1.2), flow.call("SetDriveSpeed", ARG("max_speed"), 0), wait.ms(20)),
            flow.call("StopDrive"),
            x=700, y=1960,
        )
        return {
            "motor_pair": motor_pair,
            "move_straight_deg": "MoveStraightDeg",
            "move_straight_cm": "MoveStraightCm",
            "turn_deg": "TurnDeg",
            "pivot_left_deg": "PivotLeftDeg",
            "pivot_right_deg": "PivotRightDeg",
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
        self.vars = VarsAPI(self.project)
        self.lists = ListsAPI(self.project)
        self.ops = OpsAPI(self.project)
        self.move = MoveAPI(self.project)
        self.sensor = SensorAPI(self.project)
        self.motor = MotorAPI(self.project)
        self.wait = WaitAPI(self.project)
        self.flow = FlowBuilder(self.project)
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

    def raw(self, opcode: str, **kwargs: Any) -> str:
        return self.project.add_block(opcode, **kwargs)

    def seq(self, *items: Any) -> list[str]:
        return self.flow.seq(*items)

    def const(self, name: str, value: Any, *, namespace: str | None = None) -> str:
        return self.vars.add(name, value, namespace=namespace)

    def consts(self, mapping: dict[str, Any], *, namespace: str | None = None) -> dict[str, str]:
        return self.vars.add_many(mapping, namespace=namespace)

    def ns(self, name: str):
        return self.namespace(name)
