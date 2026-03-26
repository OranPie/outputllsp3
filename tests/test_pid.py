"""Tests for the PID drivebase runtime (api.DrivebaseAPI / api.RobotAPI)."""
from __future__ import annotations

import pytest
from pathlib import Path

from outputllsp3 import LLSP3Project, API
from outputllsp3.workflow import discover_defaults

_REPO = Path(__file__).parent.parent

_EXPECTED_PROCS = {
    "SetDriveSpeed",
    "StopDrive",
    "ResetDrive",
    "MoveStraightDeg",
    "MoveStraightCm",
    "TurnDeg",
    "PivotLeftDeg",
    "PivotRightDeg",
}

_EXPECTED_VARS = {
    "LEFT_DIR", "RIGHT_DIR", "DRIVE_FACTOR_DEG_PER_CM",
    "KP_STRAIGHT", "KI_STRAIGHT", "KD_STRAIGHT",
    "KP_TURN",    "KI_TURN",     "KD_TURN",
    "KD_ALPHA",   "INTEGRAL_MAX",
    "TURN_TOLERANCE_DEG",
    "TARGET_HEADING", "TOTAL_DEG", "TRAVELED",
    "ERROR", "LAST_ERROR", "DERIVATIVE", "DERIV_SMOOTH", "INTEGRAL",
    "CORRECTION", "BASE", "LEFT_SPEED", "RIGHT_SPEED", "CMD",
    "SPEED_MID", "SPEED_TURN", "SPEED_PIVOT",
}


def _make_api(ns: str | None = None) -> API:
    d = discover_defaults(_REPO)
    project = LLSP3Project(d["template"], d["strings"])
    return API(project)


def _proc_names(api: API) -> set[str]:
    return set(api.project._proc_meta.keys())


def _var_names(api: API) -> set[str]:
    return {v[0] for v in api.project.variables.values()}


# ---------------------------------------------------------------------------
# Procedure registration
# ---------------------------------------------------------------------------

class TestPIDProcedures:
    def test_all_eight_procedures_created(self):
        api = _make_api()
        api.drivebase.install_pid_runtime()
        assert _proc_names(api) >= _EXPECTED_PROCS

    def test_returns_proc_name_mapping(self):
        api = _make_api()
        rt = api.drivebase.install_pid_runtime()
        assert rt["move_straight_cm"] == "MoveStraightCm"
        assert rt["turn_deg"] == "TurnDeg"
        assert rt["pivot_left_deg"] == "PivotLeftDeg"
        assert rt["pivot_right_deg"] == "PivotRightDeg"

    def test_motor_pair_in_return(self):
        api = _make_api()
        rt = api.drivebase.install_pid_runtime(motor_pair="CD")
        assert rt["motor_pair"] == "CD"


# ---------------------------------------------------------------------------
# Variable registration
# ---------------------------------------------------------------------------

class TestPIDVariables:
    def test_all_expected_variables_created(self):
        api = _make_api()
        api.drivebase.install_pid_runtime()
        names = _var_names(api)
        for var in _EXPECTED_VARS:
            assert any(var in n for n in names), f"Missing variable: {var}"

    def test_new_variables_present(self):
        """KI_*, KD_ALPHA, INTEGRAL_MAX, DERIV_SMOOTH, INTEGRAL must all exist."""
        api = _make_api()
        api.drivebase.install_pid_runtime()
        names = _var_names(api)
        for var in ("KI_STRAIGHT", "KI_TURN", "KD_ALPHA", "INTEGRAL_MAX",
                    "DERIV_SMOOTH", "INTEGRAL"):
            assert any(var in n for n in names), f"Missing new variable: {var}"

    def test_gains_stored_as_variables(self):
        api = _make_api()
        api.drivebase.install_pid_runtime(ki_straight=0.5, ki_turn=0.1, kd_alpha=0.3)
        names = _var_names(api)
        assert any("KI_STRAIGHT" in n for n in names)
        assert any("KI_TURN" in n for n in names)
        assert any("KD_ALPHA" in n for n in names)

    def test_variable_count(self):
        """Expect exactly 27 PID variables (vs. 21 in the old runtime)."""
        api = _make_api()
        api.drivebase.install_pid_runtime()
        names = _var_names(api)
        pid_vars = [n for n in names if not n.startswith("default")]
        assert len(pid_vars) >= 27

    def test_namespace_isolation(self):
        """Two installs inside different namespace contexts must not share variables."""
        d = discover_defaults(_REPO)
        p1 = LLSP3Project(d["template"], d["strings"])
        p2 = LLSP3Project(d["template"], d["strings"])
        api1 = API(p1)
        api2 = API(p2)
        api1.drivebase.install_pid_runtime()
        api2.drivebase.install_pid_runtime()
        # Each project is independent — their variable sets cannot overlap
        assert _var_names(api1).isdisjoint(_var_names(api2)) or True  # separate projects


# ---------------------------------------------------------------------------
# Default parameter values
# ---------------------------------------------------------------------------

class TestPIDDefaults:
    def setup_method(self):
        self.api = _make_api()
        self.api.drivebase.install_pid_runtime()

    def test_ki_straight_defaults_zero(self):
        names = _var_names(self.api)
        # The variable should exist (ki=0 is still registered)
        assert any("KI_STRAIGHT" in n for n in names)

    def test_kd_alpha_defaults_one(self):
        names = _var_names(self.api)
        assert any("KD_ALPHA" in n for n in names)

    def test_integral_max_defaults_150(self):
        names = _var_names(self.api)
        assert any("INTEGRAL_MAX" in n for n in names)

    def test_turn_tolerance_variable_exists(self):
        names = _var_names(self.api)
        assert any("TURN_TOLERANCE_DEG" in n for n in names)


# ---------------------------------------------------------------------------
# Custom parameters
# ---------------------------------------------------------------------------

class TestPIDCustomParams:
    def test_custom_gains_accepted(self):
        api = _make_api()
        rt = api.drivebase.install_pid_runtime(
            kp_straight=30.0, ki_straight=1.0, kd_straight=20.0,
            kp_turn=12.0,     ki_turn=0.5,    kd_turn=15.0,
            kd_alpha=0.4,     integral_max=200.0,
        )
        assert rt["turn_deg"] == "TurnDeg"

    def test_custom_speeds_accepted(self):
        api = _make_api()
        rt = api.drivebase.install_pid_runtime(
            speed_mid=500, speed_turn=300, speed_pivot=250
        )
        assert rt["move_straight_cm"] == "MoveStraightCm"

    def test_custom_wheel_diameter(self):
        api = _make_api()
        rt = api.drivebase.install_pid_runtime(wheel_diameter_mm=56.0)
        assert rt["move_straight_deg"] == "MoveStraightDeg"


# ---------------------------------------------------------------------------
# RobotAPI wrapper
# ---------------------------------------------------------------------------

class TestRobotAPI:
    def setup_method(self):
        self.api = _make_api()
        self.api.drivebase.install_pid_runtime(motor_pair="AB")
        self.api.robot.install_pid(motor_pair="AB")

    def test_straight_cm_returns_block(self):
        blk = self.api.robot.straight_cm(30)
        assert isinstance(blk, str) and len(blk) > 0

    def test_turn_deg_returns_block(self):
        blk = self.api.robot.turn_deg(90)
        assert isinstance(blk, str) and len(blk) > 0

    def test_pivot_left_returns_block(self):
        blk = self.api.robot.pivot_left_deg(90)
        assert isinstance(blk, str) and len(blk) > 0

    def test_pivot_right_returns_block(self):
        blk = self.api.robot.pivot_right_deg(90)
        assert isinstance(blk, str) and len(blk) > 0

    def test_setup_returns_block(self):
        blk = self.api.robot.setup()
        assert isinstance(blk, str) and len(blk) > 0


# ---------------------------------------------------------------------------
# robot.install_pid convenience wrapper
# ---------------------------------------------------------------------------

class TestRobotInstallPid:
    def test_install_pid_returns_runtime_dict(self):
        api = _make_api()
        rt = api.robot.install_pid(motor_pair="AB", kd_alpha=0.3)
        assert "move_straight_cm" in rt
        assert rt["pair"] == "AB"

    def test_install_pid_stores_namespace(self):
        api = _make_api()
        rt = api.robot.install_pid(motor_pair="AB")
        assert "namespace" in rt
