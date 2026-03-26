"""FlowBuilder helpers: for_loop, while_loop, cond.

Demonstrates:
- api.flow.for_loop(var, start, end, *body) — counted loop with auto counter
- api.flow.while_loop(condition, *body)     — repeat while condition is true
- api.flow.cond(condition, a, b)            — conditional statement (if-else block)
  NOTE: cond() is a STATEMENT, not an inline expression.  Both branches must be
  block IDs (e.g. v.set(...)).  For value selection use a variable + cond().
- Composing these with sensor and variable blocks

Compile::

    outputllsp3 build examples/05_flow_helpers.py --out flow_helpers.llsp3
"""
from outputllsp3 import MotorPair, Port

def build(project, api, ns=None):
    f = api.flow
    v = api.vars
    o = api.ops
    sensor = api.sensor
    move = api.move
    light = api.light
    wait = api.wait

    # --- Procedure: flash display N times using for_loop ---
    f.procedure("FlashN", ["n_times"], [
        *f.for_loop("flash_i", 0, project.arg("n_times"),
            light.show_image("HEART"),
            wait.ms(200),
            light.clear(),
            wait.ms(200),
        ),
    ])

    # --- Procedure: drive until obstacle or N seconds elapsed ---
    v.add("elapsed_ms", 0)
    v.add("DRIVE_SPEED_L", 30)
    v.add("DRIVE_SPEED_R", 30)
    f.procedure("DriveUntilBlocked", ["max_ms"], [
        v.set("elapsed_ms", 0),
        *f.for_loop("drive_i", 0, o.div(project.arg("max_ms"), 50),
            # Adjust speed per side using cond (statement-style: sets variable in if/else)
            f.cond(o.gt(sensor.yaw(), 5),
                   v.set("DRIVE_SPEED_L", 20), v.set("DRIVE_SPEED_L", 30)),
            f.cond(o.lt(sensor.yaw(), -5),
                   v.set("DRIVE_SPEED_R", 20), v.set("DRIVE_SPEED_R", 30)),
            move.dual_speed(v.get("DRIVE_SPEED_L"), v.get("DRIVE_SPEED_R")),
            v.change("elapsed_ms", 50),
            wait.ms(50),
        ),
        move.stop(),
    ])

    # --- Procedure: spin until yaw reaches target ---
    f.procedure("SpinToYaw", ["target_deg"], [
        sensor.reset_yaw(),
        f.while_loop(
            o.lt(o.abs(sensor.yaw()), project.arg("target_deg")),
            move.dual_speed(20, -20),
            wait.ms(20),
        ),
        move.stop(),
    ])

    # --- Main program ---
    f.start(
        move.set_pair(MotorPair.AB),
        sensor.reset_yaw(),
        f.call("FlashN", 3),
        f.call("DriveUntilBlocked", 2000),
        wait.ms(200),
        f.call("SpinToYaw", 90),
        f.call("FlashN", 1),
    )
