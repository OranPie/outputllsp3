"""Safe enum wrappers for SPIKE hardware constants (ports, motor pairs, buttons, etc.).

All enums inherit from ``StrEnum`` so they stringify cleanly to their value when
embedded in block mutation JSON without any extra ``str()`` conversion.

Public API
----------
- ``MotorPair``  – ordered two-port pair used by drive-base blocks (``AB``, ``BA``, …)
- ``MotorPort``  – single port letter (``A`` – ``F``)
- ``Port``       – alias for ``MotorPort``
- ``Button``     – hub button identifiers (``LEFT``, ``CENTER``, ``RIGHT``)
- ``MotorPairId`` – logical pair index (``PAIR_1``)
- ``OrientationAxis`` – IMU axis names (``yaw``, ``pitch``, ``roll``)
- ``LightImage`` – built-in 5×5 light-matrix images
- ``ColorValue`` – named color identifiers
- ``ENUMS``      – frozen namespace collecting all enum classes for legacy ``build(…, enums)`` call
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MotorPair(StrEnum):
    AB = "AB"
    BA = "BA"
    AC = "AC"
    CA = "CA"
    AD = "AD"
    DA = "DA"
    BC = "BC"
    CB = "CB"
    BD = "BD"
    DB = "DB"
    CD = "CD"
    DC = "DC"


class MotorPort(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class Port(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class Button(StrEnum):
    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"


class MotorPairId(StrEnum):
    PAIR_1 = "PAIR_1"


class OrientationAxis(StrEnum):
    YAW = "yaw"
    PITCH = "pitch"
    ROLL = "roll"


class LightImage(StrEnum):
    HEART = "HEART"
    HEART_SMALL = "HEART_SMALL"


class ColorValue(StrEnum):
    MAGENTA = "MAGENTA"
    VIOLET = "violet"


@dataclass(frozen=True)
class EnumsNamespace:
    MotorPair: type[MotorPair] = MotorPair
    MotorPort: type[MotorPort] = MotorPort
    Port: type[Port] = Port
    Button: type[Button] = Button
    MotorPairId: type[MotorPairId] = MotorPairId
    OrientationAxis: type[OrientationAxis] = OrientationAxis
    LightImage: type[LightImage] = LightImage
    ColorValue: type[ColorValue] = ColorValue


ENUMS = EnumsNamespace()
