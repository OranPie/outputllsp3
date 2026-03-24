"""Namespaced multi-module robot program.

Demonstrates:
- api.namespace() context manager for variable scoping
- Multiple logical subsystems (drive, arm, sensors) with isolated variables
- Procedures defined per-subsystem, each with its own namespace
- api.vars.add_many() for bulk constant declaration
- Function-namespace mode separating each build() sub-call

Compile::

    outputllsp3 build examples/09_namespaced_modules.py --out namespaced.llsp3
"""
from outputllsp3 import MotorPair, Port

def build(project, api, ns=None):
    f = api.flow

    # --- Drive subsystem ---
    with api.namespace("drive") as drive_ns:
        api.vars.add_many({
            "SPEED_FWD":  420,
            "SPEED_TURN": 260,
            "PAIR":       "AB",
        })

        def V(name): return api.vars.get(name)

        f.procedure("Drive_Init", [], [
            api.move.set_pair(MotorPair.AB),
            api.sensor.reset_yaw(),
        ])

        f.procedure("Drive_Forward", ["cm"], [
            api.move.dual_speed(V("SPEED_FWD"), V("SPEED_FWD")),
            api.wait.seconds(api.ops.div(project.arg("cm"), 20)),
            api.move.stop(),
        ])

        f.procedure("Drive_TurnDeg", ["deg"], [
            api.move.dual_speed(V("SPEED_TURN"), api.ops.sub(0, V("SPEED_TURN"))),
            api.wait.ms(400),
            api.move.stop(),
            api.sensor.reset_yaw(),
        ])

    # --- Arm subsystem ---
    with api.namespace("arm") as arm_ns:
        api.vars.add_many({
            "OPEN_SPEED":  50,
            "CLOSE_SPEED": -50,
            "GRAB_MS":     600,
        })

        def A(name): return api.vars.get(name)

        f.procedure("Arm_Open", [], [
            api.motor.run(Port.C, A("OPEN_SPEED")),
            api.wait.ms(A("GRAB_MS")),
            api.motor.stop(Port.C),
        ])

        f.procedure("Arm_Close", [], [
            api.motor.run(Port.C, A("CLOSE_SPEED")),
            api.wait.ms(A("GRAB_MS")),
            api.motor.stop(Port.C),
        ])

    # --- Main sequence ---
    f.start(
        f.call("Drive_Init"),
        f.call("Arm_Open"),
        f.call("Drive_Forward", 15),
        f.call("Arm_Close"),
        f.call("Drive_Forward", 5),
        f.call("Drive_TurnDeg", 180),
        f.call("Drive_Forward", 20),
        f.call("Arm_Open"),
        api.light.show_image("HAPPY"),
    )
