"""Full robot movement sequence using SpikeBuilder.

Demonstrates:
- b.flow.proc() to define reusable procedures
- b.flow.call() to invoke them
- b.sensor.yaw() expression used as input
- b.ops arithmetic
- b.vars for named constants
- Port and MotorPair typed enums throughout

Compile::

    outputllsp3 build examples/02_spike_builder_robot.py --out robot.llsp3
"""
from outputllsp3 import MotorPair, Port

def build(project, api, ns=None):
    from outputllsp3 import SpikeBuilder
    b = SpikeBuilder(project)

    # --- Procedures ---
    b.flow.proc("DriveForward", ["dist_cm", "spd"], [
        b.move.dual_speed(b.project.arg("spd"), b.project.arg("spd")),
        b.wait.seconds(b.ops.div(b.project.arg("dist_cm"), 20)),
        b.move.stop(),
    ])

    b.flow.proc("TurnRight90", [], [
        b.move.dual_speed(30, -30),
        b.wait.seconds(0.5),
        b.move.stop(),
        b.sensor.reset_yaw(),
    ])

    b.flow.proc("DriveSquare", ["side"], [
        b.flow.repeat(4, [
            b.flow.call("DriveForward", b.project.arg("side"), 40),
            b.wait.ms(100),
            b.flow.call("TurnRight90"),
            b.wait.ms(100),
        ]),
    ])

    # --- Main program ---
    b.flow.start(
        *b.setup(motor_pair=MotorPair.AB),
        b.sensor.reset_yaw(),
        b.light.show_text("GO"),
        b.wait.seconds(1),
        b.flow.call("DriveSquare", 20),
        b.light.show_image("HAPPY"),
        b.sound.beep(72),
    )
