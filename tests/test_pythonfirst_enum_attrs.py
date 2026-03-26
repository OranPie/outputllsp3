"""Tests verifying that the python-first compiler const-evals all StrEnum attrs.

Covers Direction, StopMode, Axis, Color, LightImage, Comparator, Port, MotorPair.
"""
from __future__ import annotations

import ast

import pytest

from outputllsp3.pythonfirst.compiler import _ENUM_ATTRS


class TestEnumAttrsDict:
    """_ENUM_ATTRS must cover all members of every exported StrEnum."""

    def test_axis_members(self):
        for name in ("YAW", "PITCH", "ROLL", "X", "Y", "Z"):
            key = f"Axis.{name}"
            assert key in _ENUM_ATTRS, f"{key!r} missing from _ENUM_ATTRS"

    def test_axis_orientation_alias(self):
        assert _ENUM_ATTRS["OrientationAxis.YAW"] == "yaw"
        assert _ENUM_ATTRS["OrientationAxis.X"] == "x"

    def test_direction_members(self):
        assert _ENUM_ATTRS["Direction.CLOCKWISE"] == "clockwise"
        assert _ENUM_ATTRS["Direction.COUNTERCLOCKWISE"] == "counterclockwise"
        assert _ENUM_ATTRS["Direction.SHORTEST"] == "shortest"

    def test_stop_mode_members(self):
        assert _ENUM_ATTRS["StopMode.COAST"] == "coast"
        assert _ENUM_ATTRS["StopMode.BRAKE"] == "brake"
        assert _ENUM_ATTRS["StopMode.HOLD"] == "hold"

    def test_color_members(self):
        for name in ("BLACK", "VIOLET", "BLUE", "AZURE", "CYAN", "GREEN",
                     "YELLOW", "ORANGE", "RED", "MAGENTA", "WHITE", "NONE"):
            key = f"Color.{name}"
            assert key in _ENUM_ATTRS, f"{key!r} missing from _ENUM_ATTRS"
            assert _ENUM_ATTRS[key] == name

    def test_light_image_members(self):
        for name in ("HEART", "HAPPY", "SAD", "YES", "NO", "SKULL", "ROBOT"):
            key = f"LightImage.{name}"
            assert key in _ENUM_ATTRS, f"{key!r} missing from _ENUM_ATTRS"

    def test_comparator_members(self):
        assert _ENUM_ATTRS["Comparator.LESS_THAN"] == "less than"
        assert _ENUM_ATTRS["Comparator.EQUAL"] == "equal to"
        assert _ENUM_ATTRS["Comparator.GREATER_THAN"] == "greater than"

    def test_port_members(self):
        for letter in ("A", "B", "C", "D", "E", "F"):
            assert _ENUM_ATTRS[f"Port.{letter}"] == letter

    def test_motor_pair_members(self):
        assert _ENUM_ATTRS["MotorPair.AB"] == "AB"
        assert _ENUM_ATTRS["MotorPair.BA"] == "BA"


class TestCompilerConstEval:
    """The compiler's const_eval must resolve enum attribute nodes to their values."""

    def _ctx(self):
        from pathlib import Path
        from outputllsp3 import LLSP3Project
        from outputllsp3.pythonfirst.compiler import PythonFirstContext
        from outputllsp3.workflow import discover_defaults
        d = discover_defaults(".")
        project = LLSP3Project(d["template"], d["strings"])
        return PythonFirstContext(project=project, source_path=Path("test.py"))

    def _attr(self, dotted: str) -> ast.Attribute:
        """Build a bare ast.Attribute node from a dotted name like 'Direction.CLOCKWISE'."""
        parts = dotted.split(".", 1)
        return ast.Attribute(value=ast.Name(id=parts[0], ctx=ast.Load()), attr=parts[1], ctx=ast.Load())

    def test_direction_clockwise(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("Direction.CLOCKWISE")) == "clockwise"

    def test_direction_shortest(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("Direction.SHORTEST")) == "shortest"

    def test_stop_mode_brake(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("StopMode.BRAKE")) == "brake"

    def test_axis_yaw(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("Axis.YAW")) == "yaw"

    def test_axis_x(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("Axis.X")) == "x"

    def test_color_red(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("Color.RED")) == "RED"

    def test_light_image_heart(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("LightImage.HEART")) == "HEART"

    def test_port_a(self):
        ctx = self._ctx()
        assert ctx.const_eval(self._attr("Port.A")) == "A"


class TestCompilerRoundTrip:
    """Enum-rich python-first source must compile without errors."""

    def _compile(self, src: str) -> None:
        import os, tempfile
        from pathlib import Path
        from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
        from outputllsp3.workflow import discover_defaults
        reset_pythonfirst_registry()
        d = discover_defaults(".")
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(src)
            py = f.name
        llsp3 = py.replace(".py", "_rt.llsp3")
        try:
            transpile_pythonfirst_file(py, template=d["template"], strings=d["strings"], out=llsp3)
            assert Path(llsp3).exists(), "No .llsp3 output produced"
        finally:
            os.unlink(py)
            if Path(llsp3).exists():
                os.unlink(llsp3)

    def test_direction_enum_compiles(self):
        self._compile("""\
from outputllsp3 import robot, run, port, Direction

@run.main
def main():
    robot.run_motor(port.A, Direction.CLOCKWISE)
""")

    def test_stop_mode_enum_compiles(self):
        self._compile("""\
from outputllsp3 import robot, run, port, StopMode

@run.main
def main():
    robot.set_stop_mode(port.A, StopMode.BRAKE)
""")

    def test_axis_enum_compiles(self):
        self._compile("""\
from outputllsp3 import robot, run, port, Axis

@run.main
def main():
    x = robot.angle(Axis.YAW)
""")
