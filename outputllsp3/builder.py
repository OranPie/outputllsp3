"""Fluent builder facade for LLSP3 projects.

``SpikeBuilder`` provides a single entry-point with typed sub-namespaces so
callers can write clean, readable code without knowing about block IDs,
opcodes, or internal JSON structure.

Example usage::

    from outputllsp3 import SpikeBuilder, LLSP3Project, Port, MotorPair, Color

    project = LLSP3Project('ok.llsp3', 'strings.json')
    b = SpikeBuilder(project)

    b.setup(motor_pair=MotorPair.AB)
    b.flow.start(
        b.motor.run(Port.A, 50),
        b.sensor.reset_yaw(),
        b.move.dual_speed(20, 20),
        b.wait.seconds(1),
        b.move.stop(),
    )
    b.flow.proc("Square", ["side", "speed"], [
        b.move.dual_speed("side", "speed"),
        b.wait.seconds(1),
        b.move.stop(),
    ])
    project.save('out.llsp3')

Sub-namespaces
--------------
- ``b.motor``  – individual motor control
- ``b.move``   – drive-pair control
- ``b.sensor`` – all sensors (IMU, color, distance, force, button, timer)
- ``b.light``  – 5×5 display
- ``b.sound``  – speaker
- ``b.flow``   – control flow (start, proc, call, if_, forever, loops, …)
- ``b.vars``   – variable declare / get / set / change
- ``b.lists``  – list operations
- ``b.ops``    – arithmetic, comparison, string, boolean operators
- ``b.wait``   – timing helpers
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .enums import (
    MotorPair,
    Port,
    Color,
    StopMode,
    Direction,
    Comparator,
    LightImage,
    Button,
    Axis,
    OrientationAxis,
)
from .api import (
    API,
    VarsAPI,
    ListsAPI,
    OpsAPI,
    MotorAPI,
    MoveAPI,
    SensorAPI,
    LightAPI,
    SoundAPI,
    WaitAPI,
)
from .flow import FlowBuilder


# ---------------------------------------------------------------------------
# Port validation helpers
# ---------------------------------------------------------------------------

_VALID_PORTS = {p.value for p in Port}
_VALID_PAIRS = {p.value for p in MotorPair}


def _port(value: Any) -> str:
    """Coerce a Port enum or string to its string value, with validation."""
    s = str(value)
    if s not in _VALID_PORTS:
        raise ValueError(
            f"Invalid port {value!r}. Expected one of {sorted(_VALID_PORTS)} "
            f"or a Port enum member (e.g. Port.A)."
        )
    return s


def _pair(value: Any) -> str:
    """Coerce a MotorPair enum or string to its string value, with validation."""
    s = str(value)
    if s not in _VALID_PAIRS:
        raise ValueError(
            f"Invalid motor pair {value!r}. Expected e.g. 'AB' or MotorPair.AB."
        )
    return s


# ---------------------------------------------------------------------------
# Sub-builders
# ---------------------------------------------------------------------------

@dataclass
class _MotorBuilder:
    """Individual motor control facade with typed signatures."""
    _api: MotorAPI

    def run(self, port: Port | str, speed: Any) -> str:
        return self._api.run(_port(port), speed)

    def run_with_power(self, port: Port | str, power: Any) -> str:
        return self._api.run_power(_port(port), power)

    def stop(self, port: Port | str) -> str:
        return self._api.stop(_port(port))

    def run_for_degrees(self, port: Port | str, degrees: Any, speed: Any) -> str:
        return self._api.run_for_degrees(_port(port), degrees, speed)

    def run_for_seconds(self, port: Port | str, seconds: Any, speed: Any) -> str:
        return self._api.run_for_seconds(_port(port), seconds, speed)

    def set_stop_mode(self, port: Port | str, mode: StopMode | str = StopMode.BRAKE) -> str:
        return self._api.set_stop_mode(_port(port), str(mode))

    def position(self, port: Port | str) -> str:
        """Return the motor's relative position (block ID)."""
        return self._api.relative_position(_port(port))

    def set_position(self, port: Port | str, value: Any = 0) -> str:
        return self._api.set_relative_position(_port(port), value)

    def absolute_position(self, port: Port | str) -> str:
        return self._api.absolute_position(_port(port))

    def speed(self, port: Port | str) -> str:
        return self._api.speed(_port(port))


@dataclass
class _MoveBuilder:
    """Drive-pair control facade."""
    _api: MoveAPI

    def set_pair(self, pair: MotorPair | str = MotorPair.AB) -> str:
        return self._api.set_pair(_pair(pair))

    def dual_speed(self, left: Any, right: Any) -> str:
        return self._api.dual_speed(left, right)

    def dual_power(self, left: Any, right: Any) -> str:
        return self._api.dual_power(left, right)

    def stop(self) -> str:
        return self._api.stop()

    def steer(self, steering: Any, speed: Any) -> str:
        return self._api.steer(steering, speed)

    def steer_for_distance(
        self, steering: Any, distance: Any, speed: Any, unit: str = "degrees"
    ) -> str:
        return self._api.steer_for_distance(steering, distance, speed, unit)


@dataclass
class _SensorBuilder:
    """Sensor facade with typed port/button/axis parameters."""
    _api: SensorAPI

    def reset_yaw(self) -> str:
        return self._api.reset_yaw()

    def yaw(self) -> str:
        return self._api.yaw()

    def pitch(self) -> str:
        return self._api.pitch()

    def roll(self) -> str:
        return self._api.roll()

    def angle(self, axis: Axis | str = Axis.YAW) -> str:
        return self._api.angle(axis)

    def timer(self) -> str:
        return self._api.timer()

    def reset_timer(self) -> str:
        return self._api.reset_timer()

    def loudness(self) -> str:
        return self._api.loudness()

    def button_pressed(self, button: Button | str = Button.CENTER) -> str:
        return self._api.button_pressed(str(button).lower())

    def color(self, port: Port | str) -> str:
        return self._api.color(_port(port))

    def color_is(self, port: Port | str, value: Color | str) -> str:
        return self._api.is_color(_port(port), str(value))

    def distance(self, port: Port | str) -> str:
        return self._api.distance(_port(port))

    def distance_is(self, port: Port | str, comparator: Comparator | str, value: Any) -> str:
        return self._api.is_distance(_port(port), str(comparator), value)

    def force(self, port: Port | str) -> str:
        return self._api.force(_port(port))

    def force_is_pressed(self, port: Port | str) -> str:
        return self._api.is_pressed(_port(port))

    def reflectivity(self, port: Port | str) -> str:
        return self._api.reflectivity(_port(port))


@dataclass
class _LightBuilder:
    """5×5 display facade."""
    _api: LightAPI

    def show_text(self, text: Any) -> str:
        return self._api.show_text(text)

    def show_image(self, image: LightImage | str) -> str:
        return self._api.show_image(str(image))

    def show_image_for(self, image: LightImage | str, seconds: Any) -> str:
        return self._api.show_image_for(str(image), seconds)

    def set_pixel(self, x: Any, y: Any, brightness: Any) -> str:
        return self._api.set_pixel(x, y, brightness)

    def clear(self) -> str:
        return self._api.clear()

    def set_brightness(self, brightness: Any) -> str:
        return self._api.set_brightness(brightness)

    def set_center_button(self, color: Color | str) -> str:
        return self._api.set_center_button(str(color))


@dataclass
class _SoundBuilder:
    """Speaker facade."""
    _api: SoundAPI

    def beep(self, note: Any = 60) -> str:
        return self._api.beep(note)

    def beep_for(self, note: Any, seconds: Any) -> str:
        return self._api.beep_for(note, seconds)

    def play(self, sound: Any) -> str:
        return self._api.play(sound)

    def play_until_done(self, sound: Any) -> str:
        return self._api.play_until_done(sound)

    def stop(self) -> str:
        return self._api.stop()


# ---------------------------------------------------------------------------
# Main SpikeBuilder
# ---------------------------------------------------------------------------

class SpikeBuilder:
    """Fluent builder facade for LLSP3 projects.

    All sub-namespaces accept typed enum values (``Port.A``, ``Color.RED``,
    etc.) and validate inputs eagerly so errors surface at call time rather
    than at save time.

    Parameters
    ----------
    project:
        An ``LLSP3Project`` instance to build into.
    """

    def __init__(self, project: Any) -> None:
        self._project = project
        self._api = API(project)

        self.motor  = _MotorBuilder(self._api.motor)
        self.move   = _MoveBuilder(self._api.move)
        self.sensor = _SensorBuilder(self._api.sensor)
        self.light  = _LightBuilder(self._api.light)
        self.sound  = _SoundBuilder(self._api.sound)
        self.flow   = self._api.flow
        self.vars   = self._api.vars
        self.lists  = self._api.lists
        self.ops    = self._api.ops
        self.wait   = self._api.wait

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def setup(
        self,
        *,
        motor_pair: MotorPair | str = MotorPair.AB,
        left_port: Port | str | None = None,
        right_port: Port | str | None = None,
        left_dir: int = 1,
        right_dir: int = -1,
    ) -> list[str]:
        """One-liner robot setup.

        Sets the movement pair and (optionally) resets individual motor
        positions and directions.

        Returns a list of block IDs that should be included in a
        ``flow.start(...)`` body if you want the setup to run at program start.
        """
        blocks: list[str] = [self.move.set_pair(motor_pair)]
        if left_port is not None:
            blocks.append(self.motor.set_position(_port(left_port), 0))
        if right_port is not None:
            blocks.append(self.motor.set_position(_port(right_port), 0))
        return blocks

    @property
    def project(self) -> Any:
        """The underlying ``LLSP3Project`` instance."""
        return self._project

    @property
    def api(self) -> API:
        """The underlying ``API`` facade instance."""
        return self._api
