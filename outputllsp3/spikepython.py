from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _PortNamespace:
    A: str = 'A'
    B: str = 'B'
    C: str = 'C'
    D: str = 'D'
    E: str = 'E'
    F: str = 'F'


@dataclass(frozen=True)
class _ButtonNamespace:
    LEFT: str = 'left'
    CENTER: str = 'center'
    RIGHT: str = 'right'


@dataclass
class HubAPI:
    port: _PortNamespace = _PortNamespace()
    button: _ButtonNamespace = _ButtonNamespace()


@dataclass
class RunloopAPI:
    project: Any
    def sleep_ms(self, value: int) -> str:
        return self.project.wait(value / 1000.0)
    def sleep(self, seconds: float) -> str:
        return self.project.wait(seconds)
    def until(self, condition_block_id: Any, *body: Any) -> str:
        # Nearest LLSP3 lowering for `await runloop.until(lambda: ...)`.
        return self.project.repeat_until(condition_block_id, self.project.chain_inline(*body) if body else None)
    def run(self, main_result: Any) -> Any:
        return main_result


@dataclass
class ButtonAPI:
    project: Any
    wrapper: Any
    LEFT: str = 'left'
    CENTER: str = 'center'
    RIGHT: str = 'right'
    def pressed(self, button: Any = 'center') -> str:
        # Nearest lowering for `button.pressed(button.LEFT)`.
        return self.wrapper.flippersensors.button_is_pressed(BUTTON=str(button), EVENT='pressed')


@dataclass
class LightMatrixAPI:
    project: Any
    wrapper: Any
    IMAGE_HEART: str = 'HEART'
    IMAGE_HEART_SMALL: str = 'HEART_SMALL'
    def write(self, text: Any) -> str:
        return self.wrapper.flipperlight.light_display_text(TEXT=text)
    def clear(self) -> str:
        return self.wrapper.flipperlight.light_display_off()
    def show_image(self, image: Any) -> str:
        return self.wrapper.flipperlight.light_display_image_on(MATRIX=str(image))
    def show_image_for_time(self, image: Any, seconds: Any) -> str:
        return self.wrapper.flipperlight.light_display_image_on_for_time(MATRIX=str(image), VALUE=seconds)
    def set_pixel(self, x: Any, y: Any, brightness: Any) -> str:
        return self.wrapper.flipperlight.light_display_set_pixel(X=x, Y=y, BRIGHTNESS=brightness)
    def set_brightness(self, brightness: Any) -> str:
        return self.wrapper.flipperlight.light_display_set_brightness(BRIGHTNESS=brightness)
    def rotate(self, direction: Any) -> str:
        return self.wrapper.flipperlight.light_display_rotate(DIRECTION=direction)
    def set_orientation(self, orientation: Any) -> str:
        return self.wrapper.flipperlight.light_display_set_orientation(ORIENTATION=orientation)


@dataclass
class SoundAPI:
    project: Any
    wrapper: Any
    def play(self, sound: Any) -> str:
        return self.wrapper.flippersound.play_sound(SOUND=sound)
    def play_until_done(self, sound: Any) -> str:
        return self.wrapper.flippersound.play_sound_until_done(SOUND=sound)
    def beep(self, note: Any, duration_ms: int | None = None) -> str:
        if duration_ms is None:
            return self.wrapper.flippersound.beep(NOTE=note)
        return self.wrapper.flippersound.beep_for_time(NOTE=note, DURATION=(duration_ms / 1000.0))
    def stop(self) -> str:
        return self.wrapper.flippersound.stop_sound()


@dataclass
class ColorSensorAPI:
    project: Any
    wrapper: Any
    def color(self, port: Any) -> str:
        return self.wrapper.flippersensors.color(PORT=str(port))
    def is_color(self, port: Any, value: Any) -> str:
        return self.wrapper.flippersensors.is_color(PORT=str(port), VALUE=value)
    def reflected_light(self, port: Any) -> str:
        return self.wrapper.flippersensors.reflectivity(PORT=str(port))


@dataclass
class ForceSensorAPI:
    project: Any
    wrapper: Any
    def pressed(self, port: Any) -> str:
        return self.wrapper.flippersensors.is_pressed(PORT=str(port), OPTION='pressed')
    def force(self, port: Any, unit: str = '%') -> str:
        return self.wrapper.flippersensors.force(PORT=str(port), UNIT=unit)


@dataclass
class DistanceSensorAPI:
    project: Any
    wrapper: Any
    def distance(self, port: Any, unit: str = 'mm') -> str:
        return self.wrapper.flippersensors.distance(PORT=str(port), UNIT=unit)
    def is_distance(self, port: Any, comparator: Any, value: Any, unit: str = 'mm') -> str:
        return self.wrapper.flippersensors.is_distance(PORT=str(port), COMPARATOR=comparator, VALUE=value, UNIT=unit)
    def show(self, port: Any, value: Any) -> str:
        # Nearest lowering for official `distance_sensor.show(...)` examples.
        return self.wrapper.flipperlight.ultrasonic_light_up(PORT=str(port), VALUE=value)


@dataclass
class MotorAPI:
    project: Any
    wrapper: Any

    HOLD: str = 'hold'
    BRAKE: str = 'brake'
    COAST: str = 'coast'

    def run(self, port: Any, speed: Any) -> str:
        return self.wrapper.flippermoremotor.motor_start_speed(PORT=str(port), SPEED=speed)

    def run_power(self, port: Any, power: Any) -> str:
        return self.wrapper.flippermoremotor.motor_start_power(PORT=str(port), POWER=power)

    def stop(self, port: Any) -> str:
        return self.wrapper.flippermotor.motor_stop(PORT=str(port))

    def relative_position(self, port: Any) -> str:
        return self.project.motor_relative_position(str(port))

    def reset_relative_position(self, port: Any, value: Any = 0) -> str:
        return self.project.motor_set_relative_position(str(port), value)

    def run_for_degrees(self, port: Any, degrees: Any, speed: Any, stop: Any | None = None) -> str:
        blocks = [self.wrapper.flippermoremotor.motor_turn_for_speed(PORT=str(port), VALUE=degrees, UNIT='degrees', SPEED=speed)]
        if stop is not None:
            blocks.append(self.wrapper.flippermoremotor.motor_set_stop_method(PORT=str(port), STOP=stop))
        return self.project.chain_inline(*blocks)

    def run_for_rotations(self, port: Any, rotations: Any, speed: Any, stop: Any | None = None) -> str:
        blocks = [self.wrapper.flippermoremotor.motor_turn_for_speed(PORT=str(port), VALUE=rotations, UNIT='rotations', SPEED=speed)]
        if stop is not None:
            blocks.append(self.wrapper.flippermoremotor.motor_set_stop_method(PORT=str(port), STOP=stop))
        return self.project.chain_inline(*blocks)

    def run_for_seconds(self, port: Any, seconds: Any, speed: Any, stop: Any | None = None) -> str:
        blocks = [self.wrapper.flippermoremotor.motor_turn_for_speed(PORT=str(port), VALUE=seconds, UNIT='seconds', SPEED=speed)]
        if stop is not None:
            blocks.append(self.wrapper.flippermoremotor.motor_set_stop_method(PORT=str(port), STOP=stop))
        return self.project.chain_inline(*blocks)

    def run_to_relative_position(self, port: Any, position: Any, speed: Any) -> str:
        return self.wrapper.flippermoremotor.motor_go_to_relative_position(PORT=str(port), POSITION=position, SPEED=speed)

    def run_to_absolute_position(self, port: Any, position: Any, speed: Any) -> str:
        # Nearest LLSP3 lowering: use relative-position command family when absolute-position block shape is not bundled.
        return self.wrapper.flippermotor.motor_go_direction_to_position(PORT=str(port), VALUE=position, DIRECTION='shortest path', UNIT='degrees', SPEED=speed)

    def set_stop_mode(self, port: Any, stop: Any = 'brake') -> str:
        return self.wrapper.flippermoremotor.motor_set_stop_method(PORT=str(port), STOP=stop)


@dataclass
class MotorPairAPI:
    project: Any
    wrapper: Any

    PAIR_1: str = 'PAIR_1'

    def pair(self, pair_id: Any, left_port: Any, right_port: Any) -> str:
        # LLSP3 bundled references expose a single movement-pair selector rather than PAIR_1 lifecycle management.
        return self.project.set_movement_pair(f"{left_port}{right_port}")

    def move(self, pair_id: Any, steering: Any, velocity: Any = 500) -> str:
        return self.wrapper.flippermoremove.start_steer_at_speed(STEERING=steering, SPEED=velocity)

    def stop(self, pair_id: Any) -> str:
        return self.project.stop_moving()

    def move_for_time(self, pair_id: Any, ms: Any, steering: Any, velocity: Any = 500) -> str:
        return self.project.chain_inline(
            self.wrapper.flippermoremove.start_steer_at_speed(STEERING=steering, SPEED=velocity),
            self.project.wait(float(ms) / 1000.0),
            self.project.stop_moving(),
        )

    def move_for_degrees(self, pair_id: Any, degrees: Any, steering: Any, velocity: Any = 500) -> str:
        return self.wrapper.flippermoremove.steer_distance_at_speed(STEERING=steering, DISTANCE=degrees, UNIT='degrees', SPEED=velocity)


class _TiltAnglesReporter:
    def __init__(self, motion_sensor: 'MotionSensorAPI'):
        self.motion_sensor = motion_sensor
    def __getitem__(self, index: int) -> str:
        if index == 0:
            return self.motion_sensor.project.mul(self.motion_sensor.project.yaw(), 10)
        raise NotImplementedError('Only tilt_angles()[0] is currently mapped')


@dataclass
class MotionSensorAPI:
    project: Any
    def reset_yaw(self, value: Any = 0) -> str:
        return self.project.reset_yaw()
    def yaw_deg(self) -> str:
        return self.project.yaw()
    def tilt_angles_index(self, index: int = 0) -> str:
        if index != 0:
            raise NotImplementedError('Only tilt_angles()[0] is currently mapped')
        return self.project.mul(self.project.yaw(), 10)
    def tilt_angles(self) -> _TiltAnglesReporter:
        return _TiltAnglesReporter(self)


@dataclass
class SpikePythonAPI:
    project: Any
    wrapper: Any
    def __post_init__(self):
        self.hub = HubAPI()
        self.port = self.hub.port
        self.button = ButtonAPI(self.project, self.wrapper)
        self.light_matrix = LightMatrixAPI(self.project, self.wrapper)
        self.sound = SoundAPI(self.project, self.wrapper)
        self.app = type('AppFacade', (), {'sound': SoundAPI(self.project, self.wrapper)})()
        self.runloop = RunloopAPI(self.project)
        self.motor = MotorAPI(self.project, self.wrapper)
        self.motion_sensor = MotionSensorAPI(self.project)
        self.motor_pair = MotorPairAPI(self.project, self.wrapper)
        self.color_sensor = ColorSensorAPI(self.project, self.wrapper)
        self.force_sensor = ForceSensorAPI(self.project, self.wrapper)
        self.distance_sensor = DistanceSensorAPI(self.project, self.wrapper)
