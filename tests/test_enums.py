"""Tests for the expanded hardware enums in outputllsp3.enums."""
import pytest
from outputllsp3.enums import (
    Port, MotorPort, MotorPair, Button, OrientationAxis, Axis,
    LightImage, Color, ColorValue, StopMode, Direction, Comparator,
    ENUMS,
)


class TestPort:
    def test_values(self):
        assert str(Port.A) == "A"
        assert str(Port.F) == "F"

    def test_is_str(self):
        assert isinstance(Port.A, str)
        assert Port.B == "B"


class TestAxis:
    def test_alias(self):
        assert Axis is OrientationAxis

    def test_values(self):
        assert str(Axis.YAW) == "yaw"
        assert str(Axis.PITCH) == "pitch"
        assert str(Axis.ROLL) == "roll"

    def test_xyz(self):
        assert Axis.X == "x"
        assert Axis.Y == "y"
        assert Axis.Z == "z"

    def test_all_six(self):
        names = {m.name for m in Axis}
        assert names == {"YAW", "PITCH", "ROLL", "X", "Y", "Z"}


class TestLightImage:
    def test_full_set(self):
        expected = {
            "HEART", "HEART_SMALL", "HAPPY", "SAD", "ANGRY", "SURPRISED",
            "SILLY", "FABULOUS", "MEH", "YES", "NO", "TRIANGLE",
            "TRIANGLE_LEFT", "ARROW_RIGHT", "ARROW_LEFT", "ARROW_UP",
            "ARROW_DOWN", "SQUARE", "SQUARE_SMALL", "TARGET", "TSHIRT",
            "ROLLERSKATE", "DUCK", "HOUSE", "TORTOISE", "BUTTERFLY",
            "STICKFIGURE", "GHOST", "SWORD", "GIRAFFE", "SKULL",
            "UMBRELLA", "SNAKE", "ROBOT",
        }
        actual = {img.value for img in LightImage}
        assert expected == actual

    def test_is_str(self):
        assert str(LightImage.HEART) == "HEART"


class TestColor:
    def test_palette(self):
        for name in ("BLACK", "VIOLET", "BLUE", "AZURE", "CYAN", "GREEN",
                     "YELLOW", "ORANGE", "RED", "MAGENTA", "WHITE", "NONE"):
            assert hasattr(Color, name)

    def test_backward_compat_alias(self):
        assert ColorValue is Color

    def test_is_str(self):
        assert str(Color.RED) == "RED"
        assert Color.GREEN == "GREEN"


class TestStopMode:
    def test_values(self):
        assert str(StopMode.COAST) == "coast"
        assert str(StopMode.BRAKE) == "brake"
        assert str(StopMode.HOLD) == "hold"


class TestAxis:
    def test_alias(self):
        assert Axis is OrientationAxis

    def test_xyz(self):
        assert Axis.X == "x"
        assert Axis.Y == "y"
        assert Axis.Z == "z"

    def test_all_six(self):
        names = {m.name for m in Axis}
        assert names == {"YAW", "PITCH", "ROLL", "X", "Y", "Z"}


class TestDirection:
    def test_values(self):
        assert str(Direction.CLOCKWISE) == "clockwise"
        assert str(Direction.COUNTERCLOCKWISE) == "counterclockwise"

    def test_shortest(self):
        assert Direction.SHORTEST == "shortest"
        assert str(Direction.SHORTEST) == "shortest"

    def test_all_three(self):
        assert {m.name for m in Direction} == {"CLOCKWISE", "COUNTERCLOCKWISE", "SHORTEST"}

    def test_shortest(self):
        assert Direction.SHORTEST == "shortest"
        assert str(Direction.SHORTEST) == "shortest"

    def test_all_three(self):
        assert {m.name for m in Direction} == {"CLOCKWISE", "COUNTERCLOCKWISE", "SHORTEST"}


class TestComparator:
    def test_values(self):
        assert str(Comparator.LESS_THAN) == "less than"
        assert str(Comparator.EQUAL) == "equal to"
        assert str(Comparator.GREATER_THAN) == "greater than"


class TestEnumsNamespace:
    def test_has_new_members(self):
        assert ENUMS.Color is Color
        assert ENUMS.StopMode is StopMode
        assert ENUMS.Direction is Direction
        assert ENUMS.Comparator is Comparator
        assert ENUMS.Axis is Axis

    def test_backward_compat(self):
        assert ENUMS.ColorValue is Color
        assert ENUMS.Port is Port


class TestFlatExport:
    def test_importable_from_package(self):
        from outputllsp3 import (
            Port, Color, StopMode, Direction, Comparator, Axis, LightImage
        )
        assert Color.RED == "RED"
        assert StopMode.BRAKE == "brake"
