"""New enum types in action: StopMode, Direction, Comparator, Color, Axis.

Demonstrates every new enum type introduced in the interface expansion:
- StopMode.BRAKE / COAST / HOLD with motor.set_stop_mode()
- Color.RED / GREEN / etc. with sensor.color_is() and light.set_center_button()
- Comparator.LESS_THAN / GREATER_THAN with sensor.distance_is()
- Axis.PITCH / ROLL / YAW with sensor.angle()
- LightImage enum for strongly-typed image names

Compile::

    outputllsp3 build examples/10_new_enums.py --out enums_demo.llsp3
"""
from outputllsp3 import (
    MotorPair, Port,
    Color, StopMode, Comparator, Axis, LightImage,
)

def build(project, api, ns=None):
    from outputllsp3 import SpikeBuilder
    b = SpikeBuilder(project)
    f = b.flow

    # --- StopMode ---
    f.procedure("BrakeHard", ["port_str"], [
        b.motor.set_stop_mode(Port.A, StopMode.BRAKE),
        b.motor.stop(Port.A),
    ])

    f.procedure("CoastStop", ["port_str"], [
        b.motor.set_stop_mode(Port.A, StopMode.COAST),
        b.motor.stop(Port.A),
    ])

    # --- Color reactions ---
    f.procedure("ColorReact", [], [
        f.if_else(
            b.sensor.color_is(Port.D, Color.RED),
            [b.light.set_center_button(Color.RED),   b.sound.beep(48)],
            [f.if_else(
                b.sensor.color_is(Port.D, Color.GREEN),
                [b.light.set_center_button(Color.GREEN), b.sound.beep(60)],
                [b.light.set_center_button(Color.WHITE)],
            )],
        ),
    ])

    # --- Axis-based orientation display ---
    f.procedure("ShowOrientation", [], [
        f.if_(
            b.ops.gt(b.sensor.angle(Axis.PITCH), 20),
            b.light.show_image(LightImage.ARROW_UP),
        ),
        f.if_(
            b.ops.lt(b.sensor.angle(Axis.PITCH), -20),
            b.light.show_image(LightImage.ARROW_DOWN),
        ),
        f.if_(
            b.ops.gt(b.sensor.angle(Axis.ROLL), 20),
            b.light.show_image(LightImage.ARROW_RIGHT),
        ),
        f.if_(
            b.ops.lt(b.sensor.angle(Axis.ROLL), -20),
            b.light.show_image(LightImage.ARROW_LEFT),
        ),
    ])

    # --- Comparator-based distance check ---
    f.procedure("DistanceGuard", [], [
        f.if_(
            b.sensor.distance_is(Port.E, Comparator.LESS_THAN, 10),
            b.move.stop(),
            b.light.show_image(LightImage.NO),
            b.sound.beep(36),
        ),
    ])

    # --- Main ---
    b.flow.start(
        *b.setup(motor_pair=MotorPair.AB),
        b.sensor.reset_yaw(),
        f.forever(
            f.call("ColorReact"),
            f.call("ShowOrientation"),
            f.call("DistanceGuard"),
            b.wait.ms(100),
        ),
    )
