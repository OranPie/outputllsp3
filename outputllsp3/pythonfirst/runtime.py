"""Runtime stub classes for Python-first mode.

These classes are instantiated as module-level singletons (``robot``, ``run``,
``port``, ``ls``) so that Python-first source files can be imported and
syntax-checked without executing real LEGO SPIKE hardware calls.  All
methods either return ``None`` (side-effect stubs) or raise ``RuntimeError``
(expression stubs that must only appear in compiled contexts).
"""
from __future__ import annotations

from typing import Any

from ..enums import Port as _PortEnum


class _RuntimeListProxy:
    def __init__(self, name: str) -> None:
        self.name = name

    def append(self, item: Any): return None
    def clear(self): return None
    def insert(self, index: int, item: Any): return None
    def remove(self, item: Any): return None

    def pop(self, index: int = -1):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")

    def contains(self, item: Any):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")

    def get(self, index: int):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")

    def set(self, index: int, value: Any): return None

    def __len__(self):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")

    def __contains__(self, item: Any):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")

    def __getitem__(self, index: int):
        raise RuntimeError("outputllsp3 Python-first lists are compiled, not executed directly")

    def __setitem__(self, index: int, value: Any): return None


class _ListModule:
    def list(self, name: str) -> _RuntimeListProxy:
        return _RuntimeListProxy(name)


class _RunModule:
    def main(self, fn):
        fn.__outputllsp3_main__ = True
        return fn

    def _event_decorator(self, kind: str, **kwargs):
        """Generic stub for @run.when_*(…) decorators."""
        def decorator(fn):
            fn.__outputllsp3_event__ = kind
            fn.__outputllsp3_event_kwargs__ = kwargs
            return fn
        return decorator

    def when_broadcast(self, message: str):
        return self._event_decorator('broadcast', message=message)

    def when_condition(self, condition):
        """Decorator stub — marks a function as a whenCondition handler."""
        return self._event_decorator('condition', condition=condition)

    def when_button(self, button: str = 'left', action: str = 'pressed'):
        return self._event_decorator('button', button=button, action=action)

    def when_gesture(self, gesture: str = 'tapped'):
        return self._event_decorator('gesture', gesture=gesture)

    def when_orientation(self, value: str = 'front'):
        return self._event_decorator('orientation', value=value)

    def when_tilted(self, direction: str = 'any'):
        return self._event_decorator('tilted', direction=direction)

    def when_timer(self, threshold: float = 5.0):
        return self._event_decorator('timer', threshold=threshold)

    def when_color(self, port, color: str = 'any'):
        return self._event_decorator('color', port=port, color=color)

    def when_pressed(self, port, option: str = 'pressed'):
        return self._event_decorator('pressed', port=port, option=option)

    def when_near_or_far(self, port, option: str = 'near'):
        return self._event_decorator('near_or_far', port=port, option=option)

    def when_distance(self, port, comparator: str = 'less_than', value: float = 10):
        return self._event_decorator('distance', port=port, comparator=comparator, value=value)

    def when_distance_closer_than(self, value: float = 10):
        return self._event_decorator('distance_closer_than', value=value)

    def when_louder_than(self, value: float = 50):
        return self._event_decorator('louder_than', value=value)

    def broadcast(self, message: str): return None
    def broadcast_and_wait(self, message: str): return None
    def sleep_ms(self, ms: int): return None
    def sleep(self, seconds: float): return None


class _RobotModule:
    def proc(self, fn):
        fn.__outputllsp3_proc__ = True
        return fn

    def use_pair(self, right: Any, left: Any): return None
    def set_direction(self, *, left: int = 1, right: int = -1): return None
    def forward_cm(self, distance_cm: Any, speed: Any | None = None): return None
    def forward_deg(self, target_deg: Any, speed: Any | None = None): return None
    def backward_cm(self, distance_cm: Any, speed: Any | None = None): return None
    def turn_deg(self, angle_deg: Any, speed: Any | None = None): return None
    def pivot_left(self, angle_deg: Any, speed: Any | None = None): return None
    def pivot_right(self, angle_deg: Any, speed: Any | None = None): return None
    def stop(self): return None
    def pause_ms(self, ms: int): return None
    def show_text(self, text: Any): return None
    def show_image(self, image: Any): return None
    def clear_display(self): return None
    def beep(self, note: Any = 60, seconds: Any | None = None): return None
    def stop_sound(self): return None
    def reset_yaw(self): return None
    def run_motor(self, port: Any, speed: Any): return None
    def stop_motor(self, port: Any): return None
    def motor_run_for_degrees(self, port: Any, degrees: Any, speed: Any): return None

    def angle(self, axis: Any = "yaw"):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def motor_relative_position(self, port: Any):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def motor_speed(self, port: Any):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def color(self, port: Any):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def distance(self, port: Any):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def force(self, port: Any):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def reflectivity(self, port: Any):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def button_pressed(self, button: str = "center"):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def button_released(self, button: str = "center"):
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    def show_monitor(self, name: str, *, visible: bool = True,
                     slider_min: Any = None, slider_max: Any = None,
                     discrete: bool = True) -> None:
        """Stub — mark a variable as visible in the SPIKE App monitor panel."""
        return None

    def note(self, text: str, *, floating: bool = False) -> None:
        """Stub — attach a Scratch comment to the surrounding block at compile time."""
        return None


class _PortModule:
    A = _PortEnum.A.value
    B = _PortEnum.B.value
    C = _PortEnum.C.value
    D = _PortEnum.D.value
    E = _PortEnum.E.value
    F = _PortEnum.F.value


class _StdlibModule:
    """Runtime stub for ``stdlib.*`` calls in Python-first source files.

    Side-effect stubs (statements) return ``None``.  Result-variable
    properties raise ``RuntimeError`` — they are replaced by variable
    reporter blocks at compile time.
    """

    # -- math procedures ------------------------------------------------
    def clamp(self, value: Any, lo: Any, hi: Any): return None
    def map_range(self, v: Any, from_lo: Any, from_hi: Any, to_lo: Any, to_hi: Any): return None
    def sign(self, value: Any): return None
    def min_val(self, a: Any, b: Any): return None
    def max_val(self, a: Any, b: Any): return None
    def lerp(self, a: Any, b: Any, t: Any): return None
    def deadzone(self, value: Any, threshold: Any): return None
    def smooth(self, prev: Any, curr: Any, alpha: Any): return None

    # -- timing procedures ----------------------------------------------
    def wait_or_timeout(self, timeout_ms: Any): return None
    def set_wait_done(self, value: Any = 1): return None
    def reset_wait(self): return None

    # -- display procedures ---------------------------------------------
    def countdown(self, n: Any): return None
    def flash_text(self, text: Any, times: Any): return None

    # -- sensor procedures ----------------------------------------------
    def smooth_yaw(self, samples: Any): return None

    # -- result variable accessors (raise at runtime, compiled at build) -
    @property
    def clamp_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def map_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def sign_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def min_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def max_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def lerp_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def deadzone_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def smooth_result(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def wait_done(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")

    @property
    def sensor_yaw(self) -> Any:
        raise RuntimeError("outputllsp3 Python-first expressions are compiled, not executed directly")


# Module-level singletons used by Python-first source files
robot = _RobotModule()
run = _RunModule()
port = _PortModule()
ls = _ListModule()
stdlib = _StdlibModule()
