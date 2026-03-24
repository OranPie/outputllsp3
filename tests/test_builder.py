"""Tests for the SpikeBuilder fluent API."""
import pytest
from outputllsp3 import SpikeBuilder
from outputllsp3.enums import Port, MotorPair, Color, StopMode, LightImage, Button


class TestSpikeBuilderConstruction:
    def test_creates_from_project(self, project):
        b = SpikeBuilder(project)
        assert b.project is project

    def test_has_all_subnamespaces(self, project):
        b = SpikeBuilder(project)
        for attr in ("motor", "move", "sensor", "light", "sound", "flow", "vars", "lists", "ops", "wait"):
            assert hasattr(b, attr), f"Missing sub-namespace: {attr}"

    def test_api_property(self, project):
        b = SpikeBuilder(project)
        from outputllsp3.api import API
        assert isinstance(b.api, API)


class TestSpikeBuilderSetup:
    def test_setup_returns_list(self, project):
        b = SpikeBuilder(project)
        result = b.setup(motor_pair=MotorPair.AB)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_setup_with_ports(self, project):
        b = SpikeBuilder(project)
        result = b.setup(motor_pair=MotorPair.AB, left_port=Port.A, right_port=Port.B)
        assert isinstance(result, list)
        assert len(result) == 3  # set_pair + 2 set_position

    def test_setup_enum_pair(self, project):
        b = SpikeBuilder(project)
        result = b.setup(motor_pair=MotorPair.CD)
        assert len(result) >= 1

    def test_setup_invalid_pair_raises(self, project):
        b = SpikeBuilder(project)
        with pytest.raises(ValueError, match="Invalid motor pair"):
            b.setup(motor_pair="ZZ")

    def test_setup_invalid_port_raises(self, project):
        b = SpikeBuilder(project)
        with pytest.raises(ValueError, match="Invalid port"):
            b.setup(motor_pair=MotorPair.AB, left_port="Z")

    def test_setup_only_left_port(self, project):
        b = SpikeBuilder(project)
        result = b.setup(motor_pair=MotorPair.AB, left_port=Port.A)
        assert len(result) == 2  # set_pair + 1 set_position

    def test_setup_only_right_port(self, project):
        b = SpikeBuilder(project)
        result = b.setup(motor_pair=MotorPair.AB, right_port=Port.B)
        assert len(result) == 2  # set_pair + 1 set_position

    def test_setup_all_block_ids_are_strings(self, project):
        b = SpikeBuilder(project)
        result = b.setup(motor_pair=MotorPair.AB, left_port=Port.A, right_port=Port.B)
        for block_id in result:
            assert isinstance(block_id, str)


class TestMotorBuilder:
    def test_run_returns_block_id(self, project):
        b = SpikeBuilder(project)
        result = b.motor.run(Port.A, 50)
        assert isinstance(result, str)

    def test_run_with_enum(self, project):
        b = SpikeBuilder(project)
        result = b.motor.run(Port.B, 75)
        assert isinstance(result, str)

    def test_invalid_port_raises(self, project):
        b = SpikeBuilder(project)
        with pytest.raises(ValueError, match="Invalid port"):
            b.motor.run("Z", 50)

    def test_stop_returns_block_id(self, project):
        b = SpikeBuilder(project)
        result = b.motor.stop(Port.A)
        assert isinstance(result, str)

    def test_stop_invalid_port_raises(self, project):
        b = SpikeBuilder(project)
        with pytest.raises(ValueError, match="Invalid port"):
            b.motor.stop("Q")

    def test_run_for_degrees(self, project):
        b = SpikeBuilder(project)
        result = b.motor.run_for_degrees(Port.C, 360, 50)
        assert isinstance(result, str)

    def test_run_for_seconds(self, project):
        b = SpikeBuilder(project)
        result = b.motor.run_for_seconds(Port.A, 2, 50)
        assert isinstance(result, str)

    def test_set_stop_mode_enum(self, project):
        b = SpikeBuilder(project)
        result = b.motor.set_stop_mode(Port.A, StopMode.BRAKE)
        assert isinstance(result, str)

    def test_set_stop_mode_coast(self, project):
        b = SpikeBuilder(project)
        result = b.motor.set_stop_mode(Port.B, StopMode.COAST)
        assert isinstance(result, str)

    def test_set_stop_mode_hold(self, project):
        b = SpikeBuilder(project)
        result = b.motor.set_stop_mode(Port.C, StopMode.HOLD)
        assert isinstance(result, str)

    def test_position(self, project):
        b = SpikeBuilder(project)
        result = b.motor.position(Port.A)
        assert isinstance(result, str)

    def test_absolute_position(self, project):
        b = SpikeBuilder(project)
        result = b.motor.absolute_position(Port.A)
        assert isinstance(result, str)

    def test_speed(self, project):
        b = SpikeBuilder(project)
        result = b.motor.speed(Port.A)
        assert isinstance(result, str)

    def test_set_position(self, project):
        b = SpikeBuilder(project)
        result = b.motor.set_position(Port.A, 0)
        assert isinstance(result, str)

    def test_run_with_power(self, project):
        b = SpikeBuilder(project)
        result = b.motor.run_with_power(Port.A, 80)
        assert isinstance(result, str)

    def test_run_for_degrees_negative_speed(self, project):
        b = SpikeBuilder(project)
        result = b.motor.run_for_degrees(Port.D, 180, -50)
        assert isinstance(result, str)


class TestMoveBuilder:
    def test_set_pair_enum(self, project):
        b = SpikeBuilder(project)
        result = b.move.set_pair(MotorPair.AB)
        assert isinstance(result, str)

    def test_set_pair_cd(self, project):
        b = SpikeBuilder(project)
        result = b.move.set_pair(MotorPair.CD)
        assert isinstance(result, str)

    def test_invalid_pair_raises(self, project):
        b = SpikeBuilder(project)
        with pytest.raises(ValueError, match="Invalid motor pair"):
            b.move.set_pair("XY")

    def test_dual_speed(self, project):
        b = SpikeBuilder(project)
        result = b.move.dual_speed(50, -50)
        assert isinstance(result, str)

    def test_dual_speed_both_positive(self, project):
        b = SpikeBuilder(project)
        result = b.move.dual_speed(30, 30)
        assert isinstance(result, str)

    def test_stop(self, project):
        b = SpikeBuilder(project)
        result = b.move.stop()
        assert isinstance(result, str)

    def test_dual_power(self, project):
        b = SpikeBuilder(project)
        result = b.move.dual_power(60, 60)
        assert isinstance(result, str)

    def test_steer(self, project):
        b = SpikeBuilder(project)
        result = b.move.steer(0, 50)
        assert isinstance(result, str)


class TestSensorBuilder:
    def test_reset_yaw(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.reset_yaw()
        assert isinstance(result, str)

    def test_yaw(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.yaw()
        assert isinstance(result, str)

    def test_pitch(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.pitch()
        assert isinstance(result, str)

    def test_roll(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.roll()
        assert isinstance(result, str)

    def test_color_with_port_enum(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.color(Port.C)
        assert isinstance(result, str)

    def test_invalid_port_raises(self, project):
        b = SpikeBuilder(project)
        with pytest.raises(ValueError, match="Invalid port"):
            b.sensor.color("X")

    def test_button_pressed_with_enum(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.button_pressed(Button.CENTER)
        assert isinstance(result, str)

    def test_button_pressed_left(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.button_pressed(Button.LEFT)
        assert isinstance(result, str)

    def test_button_pressed_right(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.button_pressed(Button.RIGHT)
        assert isinstance(result, str)

    def test_timer(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.timer()
        assert isinstance(result, str)

    def test_reset_timer(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.reset_timer()
        assert isinstance(result, str)

    def test_loudness(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.loudness()
        assert isinstance(result, str)

    def test_distance(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.distance(Port.D)
        assert isinstance(result, str)

    def test_force(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.force(Port.C)
        assert isinstance(result, str)

    def test_force_is_pressed(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.force_is_pressed(Port.C)
        assert isinstance(result, str)

    def test_reflectivity(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.reflectivity(Port.C)
        assert isinstance(result, str)

    def test_color_is(self, project):
        b = SpikeBuilder(project)
        result = b.sensor.color_is(Port.C, Color.RED)
        assert isinstance(result, str)


class TestLightBuilder:
    def test_show_text(self, project):
        b = SpikeBuilder(project)
        result = b.light.show_text("Hi")
        assert isinstance(result, str)

    def test_show_image_with_enum(self, project):
        b = SpikeBuilder(project)
        result = b.light.show_image(LightImage.HEART)
        assert isinstance(result, str)

    def test_show_image_sad(self, project):
        b = SpikeBuilder(project)
        result = b.light.show_image(LightImage.SAD)
        assert isinstance(result, str)

    def test_clear(self, project):
        b = SpikeBuilder(project)
        result = b.light.clear()
        assert isinstance(result, str)

    def test_set_center_button_color(self, project):
        b = SpikeBuilder(project)
        result = b.light.set_center_button(Color.RED)
        assert isinstance(result, str)

    def test_set_center_button_blue(self, project):
        b = SpikeBuilder(project)
        result = b.light.set_center_button(Color.BLUE)
        assert isinstance(result, str)

    def test_set_pixel(self, project):
        b = SpikeBuilder(project)
        result = b.light.set_pixel(2, 2, 100)
        assert isinstance(result, str)

    def test_set_brightness(self, project):
        b = SpikeBuilder(project)
        result = b.light.set_brightness(80)
        assert isinstance(result, str)

    def test_show_image_for(self, project):
        b = SpikeBuilder(project)
        result = b.light.show_image_for(LightImage.HAPPY, 2)
        assert isinstance(result, str)


class TestSoundBuilder:
    def test_beep(self, project):
        b = SpikeBuilder(project)
        result = b.sound.beep(60)
        assert isinstance(result, str)

    def test_beep_default_note(self, project):
        b = SpikeBuilder(project)
        result = b.sound.beep()
        assert isinstance(result, str)

    def test_beep_for(self, project):
        b = SpikeBuilder(project)
        result = b.sound.beep_for(72, 0.5)
        assert isinstance(result, str)

    def test_sound_stop(self, project):
        b = SpikeBuilder(project)
        result = b.sound.stop()
        assert isinstance(result, str)

    def test_play(self, project):
        b = SpikeBuilder(project)
        result = b.sound.play("Cat Meow 1")
        assert isinstance(result, str)


class TestWaitBuilder:
    def test_wait_seconds(self, project):
        b = SpikeBuilder(project)
        result = b.wait.seconds(1.5)
        assert isinstance(result, str)

    def test_wait_ms(self, project):
        b = SpikeBuilder(project)
        result = b.wait.ms(500)
        assert isinstance(result, str)

    def test_wait_callable(self, project):
        b = SpikeBuilder(project)
        result = b.wait(2)
        assert isinstance(result, str)


class TestOpsBuilder:
    def test_add(self, project):
        b = SpikeBuilder(project)
        result = b.ops.add(1, 2)
        assert isinstance(result, str)

    def test_sub(self, project):
        b = SpikeBuilder(project)
        result = b.ops.sub(10, 3)
        assert isinstance(result, str)

    def test_mul(self, project):
        b = SpikeBuilder(project)
        result = b.ops.mul(4, 5)
        assert isinstance(result, str)

    def test_div(self, project):
        b = SpikeBuilder(project)
        result = b.ops.div(10, 2)
        assert isinstance(result, str)

    def test_lt(self, project):
        b = SpikeBuilder(project)
        result = b.ops.lt(1, 2)
        assert isinstance(result, str)

    def test_gt(self, project):
        b = SpikeBuilder(project)
        result = b.ops.gt(5, 3)
        assert isinstance(result, str)

    def test_eq(self, project):
        b = SpikeBuilder(project)
        result = b.ops.eq(2, 2)
        assert isinstance(result, str)

    def test_and(self, project):
        b = SpikeBuilder(project)
        a = b.ops.gt(5, 3)
        c = b.ops.lt(1, 2)
        result = b.ops.and_(a, c)
        assert isinstance(result, str)

    def test_or(self, project):
        b = SpikeBuilder(project)
        a = b.ops.gt(5, 3)
        c = b.ops.lt(1, 2)
        result = b.ops.or_(a, c)
        assert isinstance(result, str)

    def test_not(self, project):
        b = SpikeBuilder(project)
        cond = b.ops.gt(1, 0)
        result = b.ops.not_(cond)
        assert isinstance(result, str)

    def test_random(self, project):
        b = SpikeBuilder(project)
        result = b.ops.random(1, 10)
        assert isinstance(result, str)

    def test_join(self, project):
        b = SpikeBuilder(project)
        result = b.ops.join("hello ", "world")
        assert isinstance(result, str)


class TestVarsBuilder:
    def test_add_returns_string(self, project):
        b = SpikeBuilder(project)
        result = b.vars.add("myVar", 0)
        assert isinstance(result, str)

    def test_get_returns_string(self, project):
        b = SpikeBuilder(project)
        b.vars.add("speed", 50)
        result = b.vars.get("speed")
        assert isinstance(result, str)

    def test_set_returns_string(self, project):
        b = SpikeBuilder(project)
        b.vars.add("counter", 0)
        result = b.vars.set("counter", 10)
        assert isinstance(result, str)

    def test_change_returns_string(self, project):
        b = SpikeBuilder(project)
        b.vars.add("score", 0)
        result = b.vars.change("score", 1)
        assert isinstance(result, str)

    def test_ensure_idempotent(self, project):
        b = SpikeBuilder(project)
        id1 = b.vars.ensure("myVar", 0)
        id2 = b.vars.ensure("myVar", 0)
        assert isinstance(id1, str)
        assert isinstance(id2, str)


class TestListsBuilder:
    def test_add_list(self, project):
        b = SpikeBuilder(project)
        result = b.lists.add("myList")
        assert isinstance(result, str)

    def test_append_item(self, project):
        b = SpikeBuilder(project)
        b.lists.add("myList")
        result = b.lists.append("myList", 42)
        assert isinstance(result, str)

    def test_clear_list(self, project):
        b = SpikeBuilder(project)
        b.lists.add("myList")
        result = b.lists.clear("myList")
        assert isinstance(result, str)

    def test_length(self, project):
        b = SpikeBuilder(project)
        b.lists.add("myList")
        result = b.lists.length("myList")
        assert isinstance(result, str)


class TestFlowIntegration:
    def test_full_start_block(self, project):
        b = SpikeBuilder(project)
        start_id = b.flow.start(
            b.move.set_pair(MotorPair.AB),
            b.sensor.reset_yaw(),
            b.wait.seconds(1),
            b.move.stop(),
        )
        assert isinstance(start_id, str)
        assert start_id in project.blocks

    def test_proc_definition(self, project):
        b = SpikeBuilder(project)
        proc_id = b.flow.proc("MyMove", ["dist"], [
            b.move.dual_speed(50, 50),
            b.wait.seconds(1),
            b.move.stop(),
        ])
        assert isinstance(proc_id, str)

    def test_vars_ops_integration(self, project):
        b = SpikeBuilder(project)
        b.vars.add("speed", 50)
        speed_ref = b.vars.get("speed")
        doubled = b.ops.mul(speed_ref, 2)
        assert isinstance(doubled, str)

    def test_if_block(self, project):
        b = SpikeBuilder(project)
        cond = b.ops.gt(b.sensor.yaw(), 45)
        block_id = b.flow.if_(cond, b.move.stop())
        assert isinstance(block_id, str)

    def test_forever_block(self, project):
        b = SpikeBuilder(project)
        block_id = b.flow.forever(
            b.move.dual_speed(50, 50),
        )
        assert isinstance(block_id, str)

    def test_repeat_block(self, project):
        b = SpikeBuilder(project)
        block_id = b.flow.repeat(10, b.move.stop())
        assert isinstance(block_id, str)

    def test_call_proc(self, project):
        b = SpikeBuilder(project)
        b.flow.proc("TurnLeft", [], [b.move.steer(-50, 30)])
        call_id = b.flow.call("TurnLeft")
        assert isinstance(call_id, str)

    def test_start_empty(self, project):
        b = SpikeBuilder(project)
        start_id = b.flow.start()
        assert isinstance(start_id, str)
        assert start_id in project.blocks

    def test_complete_program(self, project):
        b = SpikeBuilder(project)
        setup_blocks = b.setup(motor_pair=MotorPair.AB, left_port=Port.A, right_port=Port.B)
        b.vars.add("dist", 100)
        dist_ref = b.vars.get("dist")
        b.flow.proc("Drive", ["d"], [
            b.move.dual_speed(50, 50),
            b.wait.seconds(1),
            b.move.stop(),
        ])
        start_id = b.flow.start(
            *setup_blocks,
            b.sensor.reset_yaw(),
            b.flow.call("Drive", dist_ref),
            b.light.show_image(LightImage.HAPPY),
        )
        assert isinstance(start_id, str)
        assert start_id in project.blocks
