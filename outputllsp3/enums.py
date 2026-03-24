"""Safe enum wrappers for SPIKE hardware constants (ports, motor pairs, buttons, etc.).

All enums inherit from ``StrEnum`` so they stringify cleanly to their value when
embedded in block mutation JSON without any extra ``str()`` conversion.

Public API
----------
- ``MotorPair``       – ordered two-port pair used by drive-base blocks (``AB``, ``BA``, …)
- ``MotorPort``       – single port letter (``A`` – ``F``)
- ``Port``            – alias for ``MotorPort``
- ``Button``          – hub button identifiers (``LEFT``, ``CENTER``, ``RIGHT``)
- ``MotorPairId``     – logical pair index (``PAIR_1``)
- ``OrientationAxis`` – IMU axis names (``yaw``, ``pitch``, ``roll``)
- ``Axis``            – clean alias for ``OrientationAxis``
- ``LightImage``      – built-in 5×5 light-matrix images (all 34 SPIKE images)
- ``Color``           – named color identifiers (full SPIKE palette)
- ``ColorValue``      – backward-compat alias for ``Color``
- ``StopMode``        – motor stop behaviour (``coast``, ``brake``, ``hold``)
- ``Direction``       – motor rotation direction (``clockwise``, ``counterclockwise``)
- ``Comparator``      – comparison operators for sensor threshold checks
- ``ENUMS``           – frozen namespace collecting all enum classes for legacy calls
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


# Port is the primary name; MotorPort is kept as an alias
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


# Axis is a cleaner alias for OrientationAxis
Axis = OrientationAxis


class LightImage(StrEnum):
    """All 34 built-in 5×5 light-matrix images available on SPIKE Prime / Essential."""
    HEART = "HEART"
    HEART_SMALL = "HEART_SMALL"
    HAPPY = "HAPPY"
    SAD = "SAD"
    ANGRY = "ANGRY"
    SURPRISED = "SURPRISED"
    SILLY = "SILLY"
    FABULOUS = "FABULOUS"
    MEH = "MEH"
    YES = "YES"
    NO = "NO"
    TRIANGLE = "TRIANGLE"
    TRIANGLE_LEFT = "TRIANGLE_LEFT"
    ARROW_RIGHT = "ARROW_RIGHT"
    ARROW_LEFT = "ARROW_LEFT"
    ARROW_UP = "ARROW_UP"
    ARROW_DOWN = "ARROW_DOWN"
    SQUARE = "SQUARE"
    SQUARE_SMALL = "SQUARE_SMALL"
    TARGET = "TARGET"
    TSHIRT = "TSHIRT"
    ROLLERSKATE = "ROLLERSKATE"
    DUCK = "DUCK"
    HOUSE = "HOUSE"
    TORTOISE = "TORTOISE"
    BUTTERFLY = "BUTTERFLY"
    STICKFIGURE = "STICKFIGURE"
    GHOST = "GHOST"
    SWORD = "SWORD"
    GIRAFFE = "GIRAFFE"
    SKULL = "SKULL"
    UMBRELLA = "UMBRELLA"
    SNAKE = "SNAKE"
    ROBOT = "ROBOT"


class Color(StrEnum):
    """Named color identifiers for the SPIKE color sensor and hub button light."""
    BLACK = "BLACK"
    VIOLET = "VIOLET"
    BLUE = "BLUE"
    AZURE = "AZURE"
    CYAN = "CYAN"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    MAGENTA = "MAGENTA"
    WHITE = "WHITE"
    NONE = "NONE"


# ColorValue is kept as a backward-compat alias
ColorValue = Color


class StopMode(StrEnum):
    """Motor stop behaviour after a run command completes."""
    COAST = "coast"
    BRAKE = "brake"
    HOLD = "hold"


class Direction(StrEnum):
    """Motor rotation direction."""
    CLOCKWISE = "clockwise"
    COUNTERCLOCKWISE = "counterclockwise"


class Comparator(StrEnum):
    """Comparison operators used in sensor threshold blocks."""
    LESS_THAN = "less than"
    EQUAL = "equal to"
    GREATER_THAN = "greater than"


@dataclass(frozen=True)
class EnumsNamespace:
    MotorPair: type[MotorPair] = MotorPair
    MotorPort: type[MotorPort] = MotorPort
    Port: type[Port] = Port
    Button: type[Button] = Button
    MotorPairId: type[MotorPairId] = MotorPairId
    OrientationAxis: type[OrientationAxis] = OrientationAxis
    Axis: type[OrientationAxis] = OrientationAxis
    LightImage: type[LightImage] = LightImage
    Color: type[Color] = Color
    ColorValue: type[Color] = Color
    StopMode: type[StopMode] = StopMode
    Direction: type[Direction] = Direction
    Comparator: type[Comparator] = Comparator


ENUMS = EnumsNamespace()
