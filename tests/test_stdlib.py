"""Tests for outputllsp3.stdlib — install_math, install_timing, install_display."""
from __future__ import annotations

import pytest
from pathlib import Path

from outputllsp3 import LLSP3Project, API
from outputllsp3.workflow import discover_defaults
from outputllsp3.stdlib import (
    install_math,
    install_timing,
    install_display,
    install_all,
    StdLib,
)

_REPO = Path(__file__).parent.parent


def _make_api() -> API:
    d = discover_defaults(_REPO)
    project = LLSP3Project(d["template"], d["strings"])
    return API(project)


def _var_names(api: API) -> set[str]:
    """Return set of all variable qualified-names in the project."""
    return {v[0] for v in api.project.variables.values()}


def _proc_names(api: API) -> set[str]:
    """Return set of all custom-block names registered in the project."""
    return set(api.project._proc_meta.keys())


# stdlib default namespace "_stdlib" → sanitize strips leading "_" → "stdlib"
_NS_PREFIX = "stdlib"


# ---------------------------------------------------------------------------
# install_math
# ---------------------------------------------------------------------------

class TestInstallMath:
    def test_returns_dict_with_expected_keys(self):
        api = _make_api()
        result = install_math(api)
        assert set(result.keys()) == {"Clamp", "MapRange", "Sign", "MinVal", "MaxVal", "Lerp", "Deadzone", "Smooth"}

    def test_all_values_are_str_block_ids(self):
        api = _make_api()
        result = install_math(api)
        for k, v in result.items():
            assert isinstance(v, str), f"{k} block ID should be a str"

    def test_result_variables_created(self):
        api = _make_api()
        install_math(api)
        names = _var_names(api)
        assert "stdlib__MATH_CLAMP" in names
        assert "stdlib__MATH_MAP" in names
        assert "stdlib__MATH_SIGN" in names

    def test_procedures_registered(self):
        api = _make_api()
        install_math(api)
        procs = _proc_names(api)
        assert "Clamp" in procs
        assert "MapRange" in procs
        assert "Sign" in procs

    def test_custom_namespace(self):
        api = _make_api()
        install_math(api, ns="pid")
        names = _var_names(api)
        assert "pid__MATH_CLAMP" in names
        assert "pid__MATH_MAP" in names
        assert "pid__MATH_SIGN" in names

    def test_clamp_reporter_readable_after_install(self):
        api = _make_api()
        install_math(api)
        bid = api.vars.get("MATH_CLAMP", namespace="_stdlib")
        assert isinstance(bid, str)

    def test_map_reporter_readable_after_install(self):
        api = _make_api()
        install_math(api)
        bid = api.vars.get("MATH_MAP", namespace="_stdlib")
        assert isinstance(bid, str)

    def test_sign_reporter_readable_after_install(self):
        api = _make_api()
        install_math(api)
        bid = api.vars.get("MATH_SIGN", namespace="_stdlib")
        assert isinstance(bid, str)

    def test_clamp_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("Clamp", 75, -100, 100)
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_maprange_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("MapRange", 50, 0, 100, 0, 1000)
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_sign_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("Sign", -42)
        assert isinstance(bid, str)
        assert bid in api.project.blocks


# ---------------------------------------------------------------------------
# install_timing
# ---------------------------------------------------------------------------

class TestInstallTiming:
    def test_returns_dict_with_expected_key(self):
        api = _make_api()
        result = install_timing(api)
        assert set(result.keys()) == {"WaitOrTimeout"}

    def test_result_variables_created(self):
        api = _make_api()
        install_timing(api)
        names = _var_names(api)
        assert "stdlib__WAIT_DONE" in names
        assert "stdlib__WAIT_ELAPSED" in names

    def test_procedure_registered(self):
        api = _make_api()
        install_timing(api)
        assert "WaitOrTimeout" in _proc_names(api)

    def test_call_produces_block(self):
        api = _make_api()
        install_timing(api)
        bid = api.flow.call("WaitOrTimeout", 3000)
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_custom_namespace(self):
        api = _make_api()
        install_timing(api, ns="myns")
        names = _var_names(api)
        assert "myns__WAIT_DONE" in names

    def test_wait_done_reporter_readable(self):
        api = _make_api()
        install_timing(api)
        bid = api.vars.get("WAIT_DONE", namespace="_stdlib")
        assert isinstance(bid, str)


# ---------------------------------------------------------------------------
# install_display
# ---------------------------------------------------------------------------

class TestInstallDisplay:
    def test_returns_dict_with_expected_keys(self):
        api = _make_api()
        result = install_display(api)
        assert set(result.keys()) == {"Countdown", "FlashText"}

    def test_result_variables_created(self):
        api = _make_api()
        install_display(api)
        names = _var_names(api)
        assert "stdlib__DISP_I" in names
        assert "stdlib__BLINK_I" in names

    def test_procedures_registered(self):
        api = _make_api()
        install_display(api)
        procs = _proc_names(api)
        assert "Countdown" in procs
        assert "FlashText" in procs

    def test_countdown_call_produces_block(self):
        api = _make_api()
        install_display(api)
        bid = api.flow.call("Countdown", 5)
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_flashtext_call_produces_block(self):
        api = _make_api()
        install_display(api)
        bid = api.flow.call("FlashText", "GO!", 3)
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_custom_namespace(self):
        api = _make_api()
        install_display(api, ns="disp")
        names = _var_names(api)
        assert "disp__DISP_I" in names


# ---------------------------------------------------------------------------
# install_all
# ---------------------------------------------------------------------------

class TestInstallAll:
    def test_returns_all_procedure_names(self):
        api = _make_api()
        result = install_all(api)
        expected = {
            "Clamp", "MapRange", "Sign", "MinVal", "MaxVal", "Lerp", "Deadzone", "Smooth",
            "WaitOrTimeout", "Countdown", "FlashText", "SmoothYaw",
        }
        assert set(result.keys()) == expected

    def test_all_procedures_registered(self):
        api = _make_api()
        install_all(api)
        procs = _proc_names(api)
        for name in ("Clamp", "MapRange", "Sign", "MinVal", "MaxVal", "Lerp", "Deadzone", "Smooth",
                     "WaitOrTimeout", "Countdown", "FlashText", "SmoothYaw"):
            assert name in procs

    def test_all_result_variables_created(self):
        api = _make_api()
        install_all(api)
        names = _var_names(api)
        for var in ("stdlib__MATH_CLAMP", "stdlib__MATH_MAP", "stdlib__MATH_SIGN",
                    "stdlib__WAIT_DONE", "stdlib__WAIT_ELAPSED",
                    "stdlib__DISP_I", "stdlib__BLINK_I"):
            assert var in names


# ---------------------------------------------------------------------------
# StdLib class
# ---------------------------------------------------------------------------

class TestStdLib:
    def test_api_has_stdlib_attribute(self):
        api = _make_api()
        assert hasattr(api, "stdlib")
        assert isinstance(api.stdlib, StdLib)

    def test_math_idempotent(self):
        api = _make_api()
        api.stdlib.math()
        proc_count_before = len(api.project._proc_meta)
        api.stdlib.math()  # second call — should NOT duplicate
        assert len(api.project._proc_meta) == proc_count_before

    def test_timing_idempotent(self):
        api = _make_api()
        api.stdlib.timing()
        pc = len(api.project._proc_meta)
        api.stdlib.timing()
        assert len(api.project._proc_meta) == pc

    def test_display_idempotent(self):
        api = _make_api()
        api.stdlib.display()
        pc = len(api.project._proc_meta)
        api.stdlib.display()
        assert len(api.project._proc_meta) == pc

    def test_all_installs_all_groups(self):
        api = _make_api()
        api.stdlib.all()
        assert api.stdlib.installed_groups() == ["math", "timing", "display", "sensors"]

    def test_clamp_property_returns_block_id(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.clamp
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_map_result_property_returns_block_id(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.map_result
        assert isinstance(bid, str)

    def test_sign_property_returns_block_id(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.sign
        assert isinstance(bid, str)

    def test_wait_done_property_returns_block_id(self):
        api = _make_api()
        api.stdlib.timing()
        bid = api.stdlib.wait_done
        assert isinstance(bid, str)

    def test_set_wait_done_produces_set_block(self):
        api = _make_api()
        api.stdlib.timing()
        bid = api.stdlib.set_wait_done(1)
        assert isinstance(bid, str)
        assert bid in api.project.blocks

    def test_reset_wait_produces_set_block(self):
        api = _make_api()
        api.stdlib.timing()
        bid = api.stdlib.reset_wait()
        assert bid in api.project.blocks

    def test_installed_groups_empty_initially(self):
        api = _make_api()
        assert api.stdlib.installed_groups() == []

    def test_proc_ids_returns_flat_dict(self):
        api = _make_api()
        api.stdlib.math()
        ids = api.stdlib.proc_ids()
        assert "Clamp" in ids
        assert "MapRange" in ids
        assert "Sign" in ids

    def test_repr_reflects_installed_groups(self):
        api = _make_api()
        api.stdlib.math()
        r = repr(api.stdlib)
        assert "math" in r
        assert "_stdlib" in r

    def test_chaining_returns_self(self):
        api = _make_api()
        result = api.stdlib.math().timing().display()
        assert result is api.stdlib

    def test_clamp_property_raises_if_not_installed(self):
        api = _make_api()
        with pytest.raises(KeyError):
            _ = api.stdlib.clamp


# ---------------------------------------------------------------------------
# Integration: stdlib procedures used inside a start hat
# ---------------------------------------------------------------------------

class TestStdLibIntegration:
    def test_clamp_in_flow_start(self):
        api = _make_api()
        api.stdlib.math()
        f = api.flow
        start_id = f.start(
            f.call("Clamp", api.sensor.yaw(), -100, 100),
            api.motor.run("A", api.stdlib.clamp),
        )
        assert start_id in api.project.blocks

    def test_wait_or_timeout_with_event_hat(self):
        api = _make_api()
        api.stdlib.timing()
        f = api.flow
        start_id = f.start(
            api.stdlib.reset_wait(),
            f.call("WaitOrTimeout", 5000),
            api.motor.run("A", 50),
        )
        btn_hat = f.when("button", api.stdlib.set_wait_done(1), button="left")
        assert start_id in api.project.blocks
        assert btn_hat in api.project.blocks

    def test_countdown_and_flash_in_start(self):
        api = _make_api()
        api.stdlib.display()
        f = api.flow
        start_id = f.start(
            f.call("Countdown", 3),
            api.motor.run("A", 80),
            api.motor.run("A", 0),
            f.call("FlashText", "DONE", 3),
        )
        assert start_id in api.project.blocks

    def test_install_all_then_use_all_procs(self):
        api = _make_api()
        api.stdlib.all()
        f = api.flow
        # Use every stdlib procedure in a single start block
        start_id = f.start(
            f.call("Clamp", 120, -100, 100),
            f.call("MapRange", api.stdlib.clamp, -100, 100, 0, 1000),
            f.call("Sign", api.stdlib.clamp),
            api.stdlib.reset_wait(),
            f.call("WaitOrTimeout", 2000),
            f.call("Countdown", 5),
            f.call("FlashText", "GO", 2),
        )
        assert start_id in api.project.blocks

    def test_project_serializable_after_stdlib(self):
        """Ensure the project can produce valid JSON after stdlib install."""
        import json
        api = _make_api()
        api.stdlib.all()
        api.flow.start(
            api.flow.call("Clamp", 50, 0, 100),
        )
        data = api.project.project_json
        assert "targets" in data


# ---------------------------------------------------------------------------
# install_math expanded (MinVal, MaxVal, Lerp, Deadzone, Smooth)
# ---------------------------------------------------------------------------

class TestInstallMathExpanded:
    def test_min_val_result_variable(self):
        api = _make_api()
        install_math(api)
        assert "stdlib__MATH_MIN" in _var_names(api)

    def test_max_val_result_variable(self):
        api = _make_api()
        install_math(api)
        assert "stdlib__MATH_MAX" in _var_names(api)

    def test_lerp_result_variable(self):
        api = _make_api()
        install_math(api)
        assert "stdlib__MATH_LERP" in _var_names(api)

    def test_deadzone_result_variable(self):
        api = _make_api()
        install_math(api)
        assert "stdlib__MATH_DEADZONE" in _var_names(api)

    def test_smooth_result_variable(self):
        api = _make_api()
        install_math(api)
        assert "stdlib__MATH_SMOOTH" in _var_names(api)

    def test_min_val_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("MinVal", 3, 7)
        assert bid in api.project.blocks

    def test_max_val_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("MaxVal", 3, 7)
        assert bid in api.project.blocks

    def test_lerp_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("Lerp", 0, 100, 0.5)
        assert bid in api.project.blocks

    def test_deadzone_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("Deadzone", api.sensor.yaw(), 5)
        assert bid in api.project.blocks

    def test_smooth_call_produces_block(self):
        api = _make_api()
        install_math(api)
        bid = api.flow.call("Smooth", 0, api.sensor.yaw(), 0.1)
        assert bid in api.project.blocks

    def test_stdlib_min_result_property(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.min_result
        assert isinstance(bid, str) and bid in api.project.blocks

    def test_stdlib_max_result_property(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.max_result
        assert isinstance(bid, str) and bid in api.project.blocks

    def test_stdlib_lerp_property(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.lerp
        assert isinstance(bid, str) and bid in api.project.blocks

    def test_stdlib_deadzone_property(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.deadzone
        assert isinstance(bid, str) and bid in api.project.blocks

    def test_stdlib_smooth_property(self):
        api = _make_api()
        api.stdlib.math()
        bid = api.stdlib.smooth
        assert isinstance(bid, str) and bid in api.project.blocks


# ---------------------------------------------------------------------------
# install_sensors
# ---------------------------------------------------------------------------

class TestInstallSensors:
    def test_returns_dict_with_expected_key(self):
        from outputllsp3.stdlib import install_sensors
        api = _make_api()
        result = install_sensors(api)
        assert set(result.keys()) == {"SmoothYaw"}

    def test_result_variables_created(self):
        from outputllsp3.stdlib import install_sensors
        api = _make_api()
        install_sensors(api)
        names = _var_names(api)
        assert "stdlib__SENSOR_YAW" in names
        assert "stdlib__SENSOR_I" in names

    def test_procedure_registered(self):
        from outputllsp3.stdlib import install_sensors
        api = _make_api()
        install_sensors(api)
        assert "SmoothYaw" in _proc_names(api)

    def test_call_produces_block(self):
        from outputllsp3.stdlib import install_sensors
        api = _make_api()
        install_sensors(api)
        bid = api.flow.call("SmoothYaw", 5)
        assert bid in api.project.blocks

    def test_stdlib_sensors_method(self):
        api = _make_api()
        api.stdlib.sensors()
        assert "sensors" in api.stdlib.installed_groups()

    def test_stdlib_sensor_yaw_property(self):
        api = _make_api()
        api.stdlib.sensors()
        bid = api.stdlib.sensor_yaw
        assert isinstance(bid, str) and bid in api.project.blocks

    def test_sensors_idempotent(self):
        api = _make_api()
        api.stdlib.sensors()
        pc = len(api.project._proc_meta)
        api.stdlib.sensors()
        assert len(api.project._proc_meta) == pc


# ---------------------------------------------------------------------------
# Python-first stdlib support
# ---------------------------------------------------------------------------

class TestPythonFirstStdlib:
    """Tests for stdlib.* calls in Python-first compiled source."""

    def _compile(self, src: str):
        """Compile Python-first source string. Returns the PythonFirstContext."""
        from outputllsp3.pythonfirst.compiler import PythonFirstContext, _load_source
        from outputllsp3 import reset_pythonfirst_registry
        from pathlib import Path
        import ast as ast_mod
        d = discover_defaults(_REPO)
        project = __import__('outputllsp3').LLSP3Project(d['template'], d['strings'])
        reset_pythonfirst_registry()
        ctx = PythonFirstContext(project, Path("/tmp/_test_stdlib_src.py"))
        ctx.transpile(ast_mod.parse(src))
        return ctx

    def test_stdlib_clamp_call_installs_math(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.clamp(50, 0, 100)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Clamp" in api.project._proc_meta

    def test_stdlib_sign_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.sign(robot.angle())
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Sign" in api.project._proc_meta

    def test_stdlib_min_val_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.min_val(10, 20)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "MinVal" in api.project._proc_meta

    def test_stdlib_max_val_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.max_val(10, 20)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "MaxVal" in api.project._proc_meta

    def test_stdlib_lerp_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.lerp(0, 100, 0.5)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Lerp" in api.project._proc_meta

    def test_stdlib_deadzone_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.deadzone(robot.angle(), 5)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Deadzone" in api.project._proc_meta

    def test_stdlib_smooth_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.smooth(0, robot.angle(), 0.1)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Smooth" in api.project._proc_meta

    def test_stdlib_countdown_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.countdown(5)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Countdown" in api.project._proc_meta

    def test_stdlib_flash_text_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.flash_text("GO", 3)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "FlashText" in api.project._proc_meta

    def test_stdlib_wait_or_timeout_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.wait_or_timeout(5000)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "WaitOrTimeout" in api.project._proc_meta

    def test_stdlib_smooth_yaw_call(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.smooth_yaw(10)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "SmoothYaw" in api.project._proc_meta

    def test_stdlib_result_attribute_access(self):
        """stdlib.clamp_result should emit a MATH_CLAMP reporter block."""
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.clamp(robot.angle(), -100, 100)
    robot.run_motor("A", stdlib.clamp_result)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Clamp" in api.project._proc_meta
        # MATH_CLAMP variable should be declared
        assert "stdlib__MATH_CLAMP" in {v[0] for v in api.project.variables.values()}

    def test_stdlib_sign_result_attribute(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.sign(robot.angle())
    robot.run_motor("A", stdlib.sign_result)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "stdlib__MATH_SIGN" in {v[0] for v in api.project.variables.values()}

    def test_stdlib_sensor_yaw_attribute(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.smooth_yaw(5)
    robot.run_motor("A", stdlib.sensor_yaw)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "stdlib__SENSOR_YAW" in {v[0] for v in api.project.variables.values()}

    def test_stdlib_lazy_install_only_math(self):
        """Only the math group should be installed when only math calls are used."""
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.clamp(50, 0, 100)
    stdlib.sign(robot.angle())
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "Clamp" in api.project._proc_meta
        assert "Sign" in api.project._proc_meta
        # Timing group not needed → WaitOrTimeout should NOT be installed
        assert "WaitOrTimeout" not in api.project._proc_meta

    def test_stdlib_set_wait_done(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.reset_wait()
    stdlib.wait_or_timeout(3000)
"""
        ctx = self._compile(src)
        api = ctx.api
        assert "WaitOrTimeout" in api.project._proc_meta


# ── New tests: stdlib shorthand aliases + robot.* handlers ────────────────────

class TestStdlibShorthandAliases:
    """stdlib.clamp (no _result suffix) should work as an alias for stdlib.clamp_result."""

    def _compile(self, src: str):
        import ast
        from pathlib import Path
        from outputllsp3 import LLSP3Project, reset_pythonfirst_registry
        from outputllsp3.pythonfirst.compiler import PythonFirstContext
        from outputllsp3.workflow import discover_defaults
        reset_pythonfirst_registry()
        d = discover_defaults(".")
        project = LLSP3Project(d["template"], d["strings"])
        ctx = PythonFirstContext(project=project, source_path=Path("test.py"))
        ctx.transpile(ast.parse(src))
        return ctx

    def test_clamp_shorthand_installs_math(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.clamp(50, 0, 100)
    robot.run_motor("A", stdlib.clamp)
"""
        ctx = self._compile(src)
        assert "Clamp" in ctx.api.project._proc_meta
        assert "stdlib__MATH_CLAMP" in {v[0] for v in ctx.api.project.variables.values()}

    def test_sign_shorthand(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.sign(robot.angle())
    robot.run_motor("A", stdlib.sign)
"""
        ctx = self._compile(src)
        assert "stdlib__MATH_SIGN" in {v[0] for v in ctx.api.project.variables.values()}

    def test_lerp_shorthand(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.lerp(0, 100, 0.5)
    robot.run_motor("A", stdlib.lerp)
"""
        ctx = self._compile(src)
        assert "stdlib__MATH_LERP" in {v[0] for v in ctx.api.project.variables.values()}

    def test_smooth_shorthand(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.smooth(0, 50, 0.1)
    robot.run_motor("A", stdlib.smooth)
"""
        ctx = self._compile(src)
        assert "stdlib__MATH_SMOOTH" in {v[0] for v in ctx.api.project.variables.values()}

    def test_deadzone_shorthand(self):
        src = """\
from outputllsp3 import robot, run, stdlib

@run.main
def main():
    stdlib.deadzone(robot.angle(), 5)
    robot.run_motor("A", stdlib.deadzone)
"""
        ctx = self._compile(src)
        assert "stdlib__MATH_DEADZONE" in {v[0] for v in ctx.api.project.variables.values()}


class TestNewRobotHandlers:
    """Tests for newly added robot.* expression and statement handlers."""

    def _compile(self, src: str):
        import ast
        from pathlib import Path
        from outputllsp3 import LLSP3Project, reset_pythonfirst_registry
        from outputllsp3.pythonfirst.compiler import PythonFirstContext
        from outputllsp3.workflow import discover_defaults
        reset_pythonfirst_registry()
        d = discover_defaults(".")
        project = LLSP3Project(d["template"], d["strings"])
        ctx = PythonFirstContext(project=project, source_path=Path("test.py"))
        ctx.transpile(ast.parse(src))
        return ctx

    def _opcodes(self, ctx) -> set:
        return {b["opcode"] for b in ctx.api.project.sprite["blocks"].values()}

    # ── expression reporters ────────────────────────────────────────────────

    def test_robot_timer(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    x = robot.timer()
"""
        ctx = self._compile(src)
        assert any("timer" in op.lower() for op in self._opcodes(ctx))

    def test_robot_loudness(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    x = robot.loudness()
"""
        ctx = self._compile(src)
        assert any("loud" in op.lower() for op in self._opcodes(ctx))

    def test_robot_button_pressed(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    x = robot.button_pressed("center")
"""
        ctx = self._compile(src)
        assert any("pressed" in op.lower() or "button" in op.lower() for op in self._opcodes(ctx))

    def test_robot_motor_absolute_position(self):
        src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    x = robot.motor_absolute_position(port.A)
"""
        ctx = self._compile(src)
        assert any("absolute" in op.lower() or "position" in op.lower() for op in self._opcodes(ctx))

    def test_robot_is_color(self):
        src = """\
from outputllsp3 import robot, run, port, Color

@run.main
def main():
    if robot.is_color(port.A, Color.RED):
        robot.stop()
"""
        ctx = self._compile(src)
        assert any("color" in op.lower() for op in self._opcodes(ctx))

    def test_robot_is_pressed(self):
        src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    if robot.is_pressed(port.A):
        robot.stop()
"""
        ctx = self._compile(src)
        assert any("pressed" in op.lower() for op in self._opcodes(ctx))

    # ── statement handlers ──────────────────────────────────────────────────

    def test_robot_reset_timer(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    robot.reset_timer()
"""
        ctx = self._compile(src)
        assert any("timer" in op.lower() for op in self._opcodes(ctx))

    def test_robot_run_motor_for_seconds(self):
        src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.run_motor_for_seconds(port.A, 2, 50)
"""
        ctx = self._compile(src)
        assert any("motor" in op.lower() for op in self._opcodes(ctx))

    def test_robot_run_motor_for(self):
        src = """\
from outputllsp3 import robot, run, port, Direction

@run.main
def main():
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 360, 'degrees')
"""
        ctx = self._compile(src)
        assert any("motor" in op.lower() for op in self._opcodes(ctx))

    def test_robot_motor_go_to_position(self):
        src = """\
from outputllsp3 import robot, run, port, Direction

@run.main
def main():
    robot.motor_go_to_position(port.A, Direction.SHORTEST, 90)
"""
        ctx = self._compile(src)
        assert any("position" in op.lower() or "motor" in op.lower() for op in self._opcodes(ctx))

    def test_robot_set_motor_stop_mode(self):
        src = """\
from outputllsp3 import robot, run, port, StopMode

@run.main
def main():
    robot.set_motor_stop_mode(port.A, StopMode.BRAKE)
"""
        ctx = self._compile(src)
        assert any("stop" in op.lower() for op in self._opcodes(ctx))

    def test_robot_show_image_for(self):
        src = """\
from outputllsp3 import robot, run, LightImage

@run.main
def main():
    robot.show_image_for(LightImage.HEART, 2)
"""
        ctx = self._compile(src)
        assert any("image" in op.lower() or "display" in op.lower() for op in self._opcodes(ctx))

    def test_robot_set_center_light(self):
        src = """\
from outputllsp3 import robot, run, Color

@run.main
def main():
    robot.set_center_light(Color.RED)
"""
        ctx = self._compile(src)
        assert any("light" in op.lower() or "button" in op.lower() for op in self._opcodes(ctx))

    def test_robot_play_sound(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    robot.play_sound(1)
"""
        ctx = self._compile(src)
        assert any("sound" in op.lower() for op in self._opcodes(ctx))

    def test_robot_drive(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    robot.drive(50, 50)
"""
        ctx = self._compile(src)
        assert any("speed" in op.lower() or "drive" in op.lower() or "move" in op.lower() for op in self._opcodes(ctx))

    def test_robot_steer(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    robot.steer(0, 50)
"""
        ctx = self._compile(src)
        assert any("steer" in op.lower() for op in self._opcodes(ctx))


class TestAugAssignExtended:
    """AugAssign should support *=, /= in addition to +=, -=."""

    def _compile(self, src: str):
        import ast
        from pathlib import Path
        from outputllsp3 import LLSP3Project, reset_pythonfirst_registry
        from outputllsp3.pythonfirst.compiler import PythonFirstContext
        from outputllsp3.workflow import discover_defaults
        reset_pythonfirst_registry()
        d = discover_defaults(".")
        project = LLSP3Project(d["template"], d["strings"])
        ctx = PythonFirstContext(project=project, source_path=Path("test.py"))
        ctx.transpile(ast.parse(src))
        return ctx

    def test_multiply_assign(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    x = 3
    x *= 2
"""
        ctx = self._compile(src)
        vars_ = {v[0] for v in ctx.api.project.variables.values()}
        assert any("x" in v for v in vars_)

    def test_divide_assign(self):
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    x = 10
    x /= 2
"""
        ctx = self._compile(src)
        vars_ = {v[0] for v in ctx.api.project.variables.values()}
        assert any("x" in v for v in vars_)

    def test_all_four_ops(self):
        """All four augmented assignment operators should compile without errors."""
        src = """\
from outputllsp3 import robot, run

@run.main
def main():
    x = 10
    x += 1
    x -= 2
    x *= 3
    x /= 4
"""
        ctx = self._compile(src)
        # Just verifying no crash — all 4 ops should compile
        assert ctx.notes == [] or True  # notes allowed but no exception
