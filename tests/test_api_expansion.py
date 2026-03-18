"""Tests for expanded coding API: OpsAPI, SensorAPI, MotorAPI, LightAPI, SoundAPI, MoveAPI, FlowBuilder, and python-first robot helpers."""
import ast
import os
import tempfile
from pathlib import Path


def _make_project():
    from outputllsp3 import LLSP3Project, API
    from outputllsp3.workflow import discover_defaults
    d = discover_defaults('.')
    project = LLSP3Project(d['template'], d['strings'])
    api = API(project)
    return project, api


# ---------------------------------------------------------------------------
# OpsAPI expanded
# ---------------------------------------------------------------------------

def test_ops_mod():
    project, api = _make_project()
    blk = api.ops.mod(10, 3)
    assert project.blocks[blk]['opcode'] == 'operator_mod'
    project.cleanup()


def test_ops_round():
    project, api = _make_project()
    blk = api.ops.round(3.7)
    assert project.blocks[blk]['opcode'] == 'operator_round'
    project.cleanup()


def test_ops_join():
    project, api = _make_project()
    blk = api.ops.join('hello', ' world')
    assert project.blocks[blk]['opcode'] == 'operator_join'
    project.cleanup()


def test_ops_length_of():
    project, api = _make_project()
    blk = api.ops.length_of('hello')
    assert project.blocks[blk]['opcode'] == 'operator_length'
    project.cleanup()


def test_ops_letter_of():
    project, api = _make_project()
    blk = api.ops.letter_of(1, 'hello')
    assert project.blocks[blk]['opcode'] == 'operator_letter_of'
    project.cleanup()


def test_ops_str_contains():
    project, api = _make_project()
    blk = api.ops.str_contains('hello world', 'world')
    assert project.blocks[blk]['opcode'] == 'operator_contains'
    project.cleanup()


def test_ops_random():
    project, api = _make_project()
    blk = api.ops.random(1, 10)
    assert project.blocks[blk]['opcode'] == 'operator_random'
    project.cleanup()


def test_ops_mathop():
    project, api = _make_project()
    blk = api.ops.mathop('sqrt', 16)
    assert project.blocks[blk]['opcode'] == 'operator_mathop'
    project.cleanup()


# ---------------------------------------------------------------------------
# SensorAPI expanded
# ---------------------------------------------------------------------------

def test_sensor_pitch():
    project, api = _make_project()
    blk = api.sensor.pitch()
    assert project.blocks[blk]['opcode'] == 'flippersensors_orientationAxis'
    assert project.blocks[blk]['fields']['AXIS'] == ['pitch', None]
    project.cleanup()


def test_sensor_roll():
    project, api = _make_project()
    blk = api.sensor.roll()
    assert project.blocks[blk]['opcode'] == 'flippersensors_orientationAxis'
    assert project.blocks[blk]['fields']['AXIS'] == ['roll', None]
    project.cleanup()


def test_sensor_timer():
    project, api = _make_project()
    blk = api.sensor.timer()
    assert blk in project.blocks
    project.cleanup()


def test_sensor_loudness():
    project, api = _make_project()
    blk = api.sensor.loudness()
    assert blk in project.blocks
    project.cleanup()


def test_sensor_button_pressed():
    project, api = _make_project()
    blk = api.sensor.button_pressed('left')
    assert blk in project.blocks
    project.cleanup()


def test_sensor_color():
    project, api = _make_project()
    blk = api.sensor.color('A')
    assert blk in project.blocks
    project.cleanup()


def test_sensor_distance():
    project, api = _make_project()
    blk = api.sensor.distance('A')
    assert blk in project.blocks
    project.cleanup()


def test_sensor_force():
    project, api = _make_project()
    blk = api.sensor.force('A')
    assert blk in project.blocks
    project.cleanup()


def test_sensor_reflectivity():
    project, api = _make_project()
    blk = api.sensor.reflectivity('A')
    assert blk in project.blocks
    project.cleanup()


# ---------------------------------------------------------------------------
# MotorAPI expanded
# ---------------------------------------------------------------------------

def test_motor_run():
    project, api = _make_project()
    blk = api.motor.run('A', 500)
    assert blk in project.blocks
    project.cleanup()


def test_motor_run_power():
    project, api = _make_project()
    blk = api.motor.run_power('A', 50)
    assert blk in project.blocks
    project.cleanup()


def test_motor_stop():
    project, api = _make_project()
    blk = api.motor.stop('A')
    assert blk in project.blocks
    project.cleanup()


def test_motor_run_for_degrees():
    project, api = _make_project()
    blk = api.motor.run_for_degrees('A', 360, 500)
    assert blk in project.blocks
    project.cleanup()


def test_motor_run_for_seconds():
    project, api = _make_project()
    blk = api.motor.run_for_seconds('A', 2, 500)
    assert blk in project.blocks
    project.cleanup()


def test_motor_absolute_position():
    project, api = _make_project()
    blk = api.motor.absolute_position('A')
    assert blk in project.blocks
    project.cleanup()


def test_motor_speed():
    project, api = _make_project()
    blk = api.motor.speed('A')
    assert blk in project.blocks
    project.cleanup()


# ---------------------------------------------------------------------------
# LightAPI
# ---------------------------------------------------------------------------

def test_light_show_text():
    project, api = _make_project()
    blk = api.light.show_text('hi')
    assert blk in project.blocks
    project.cleanup()


def test_light_show_image():
    project, api = _make_project()
    blk = api.light.show_image('HEART')
    assert blk in project.blocks
    project.cleanup()


def test_light_clear():
    project, api = _make_project()
    blk = api.light.clear()
    assert blk in project.blocks
    project.cleanup()


def test_light_set_pixel():
    project, api = _make_project()
    blk = api.light.set_pixel(0, 0, 100)
    assert blk in project.blocks
    project.cleanup()


def test_light_set_brightness():
    project, api = _make_project()
    blk = api.light.set_brightness(100)
    assert blk in project.blocks
    project.cleanup()


# ---------------------------------------------------------------------------
# SoundAPI
# ---------------------------------------------------------------------------

def test_sound_beep():
    project, api = _make_project()
    blk = api.sound.beep(60)
    assert blk in project.blocks
    project.cleanup()


def test_sound_beep_for():
    project, api = _make_project()
    blk = api.sound.beep_for(60, 0.5)
    assert blk in project.blocks
    project.cleanup()


def test_sound_stop():
    project, api = _make_project()
    blk = api.sound.stop()
    assert blk in project.blocks
    project.cleanup()


# ---------------------------------------------------------------------------
# MoveAPI expanded
# ---------------------------------------------------------------------------

def test_move_steer():
    project, api = _make_project()
    blk = api.move.steer(50, 500)
    assert blk in project.blocks
    project.cleanup()


def test_move_steer_for_distance():
    project, api = _make_project()
    blk = api.move.steer_for_distance(50, 360, 500)
    assert blk in project.blocks
    project.cleanup()


# ---------------------------------------------------------------------------
# FlowBuilder expanded
# ---------------------------------------------------------------------------

def test_flow_wait_until():
    project, api = _make_project()
    cond = api.ops.gt(api.ops.add(1, 2), 0)
    blk = api.flow.wait_until(cond)
    assert project.blocks[blk]['opcode'] == 'control_wait_until'
    project.cleanup()


def test_flow_stop():
    project, api = _make_project()
    blk = api.flow.stop()
    assert project.blocks[blk]['opcode'] == 'flippercontrol_stop'
    project.cleanup()


# ---------------------------------------------------------------------------
# Public API exports
# ---------------------------------------------------------------------------

def test_light_api_exported():
    import outputllsp3
    assert 'LightAPI' in outputllsp3.__all__
    assert callable(getattr(outputllsp3, 'LightAPI', None))


def test_sound_api_exported():
    import outputllsp3
    assert 'SoundAPI' in outputllsp3.__all__
    assert callable(getattr(outputllsp3, 'SoundAPI', None))


# ---------------------------------------------------------------------------
# Integration: build and save a project using new APIs
# ---------------------------------------------------------------------------

def test_integration_new_api_save():
    """A project using all new API features should save and reload correctly."""
    from outputllsp3 import LLSP3Project, API, parse_llsp3
    from outputllsp3.workflow import discover_defaults

    d = discover_defaults('.')
    project = LLSP3Project(d['template'], d['strings'])
    api = API(project)

    api.flow.start(
        api.light.show_text('hi'),
        api.sound.beep(60),
        api.flow.wait_until(api.ops.gt(api.ops.random(1, 10), 5)),
        api.motor.run('A', 500),
        api.motor.stop('A'),
        api.move.steer(50, 500),
        api.light.clear(),
        api.sound.stop(),
    )

    with tempfile.NamedTemporaryFile(suffix='.llsp3', delete=False) as f:
        out = f.name
    try:
        project.save(out)
        doc = parse_llsp3(out)
        opcodes = [b.get('opcode') for b in doc.blocks.values()]
        assert 'control_wait_until' in opcodes
    finally:
        project.cleanup()
        if Path(out).exists():
            os.unlink(out)


# ---------------------------------------------------------------------------
# Python-first robot helpers
# ---------------------------------------------------------------------------

def _defaults():
    from outputllsp3.workflow import discover_defaults
    return discover_defaults('.')


def test_pythonfirst_robot_show_text():
    """robot.show_text should compile."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.show_text('hi')
    robot.show_image('HEART')
    robot.clear_display()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_pythonfirst_robot_beep():
    """robot.beep should compile."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.beep(60)
    robot.beep(72, 0.5)
    robot.stop_sound()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_pythonfirst_robot_motor():
    """robot.run_motor, robot.stop_motor should compile."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    robot.run_motor(port.A, 500)
    robot.stop_motor(port.A)
    robot.reset_yaw()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)


def test_pythonfirst_robot_sensor_expr():
    """robot.angle() and robot.distance() as expressions should compile."""
    from outputllsp3 import transpile_pythonfirst_file, reset_pythonfirst_registry
    reset_pythonfirst_registry()
    d = _defaults()
    src = """\
from outputllsp3 import robot, run, port

@run.main
def main():
    heading = robot.angle('yaw')
    dist = robot.distance(port.A)
    col = robot.color(port.B)
    robot.stop()
"""
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(src)
        py = f.name
    out = py.replace('.py', '.llsp3')
    try:
        transpile_pythonfirst_file(py, template=d['template'], strings=d['strings'], out=out)
        assert Path(out).exists()
    finally:
        os.unlink(py)
        if Path(out).exists():
            os.unlink(out)
