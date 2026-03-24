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
        assert set(result.keys()) == {"Clamp", "MapRange", "Sign"}

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
        expected = {"Clamp", "MapRange", "Sign", "WaitOrTimeout", "Countdown", "FlashText"}
        assert set(result.keys()) == expected

    def test_all_procedures_registered(self):
        api = _make_api()
        install_all(api)
        procs = _proc_names(api)
        for name in ("Clamp", "MapRange", "Sign", "WaitOrTimeout", "Countdown", "FlashText"):
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
        assert api.stdlib.installed_groups() == ["math", "timing", "display"]

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
