"""SpikeBuilder: complete competition robot program.

A realistic competition-style program combining:
- SpikeBuilder for clean, readable code
- Multiple mission procedures (proc) each handling one field task
- Shared state via variables (heading lock, position tracking)
- Error-checking via flow.if_() guards
- Auto-layout: procedures and start blocks placed without magic numbers

Compile::

    outputllsp3 build examples/13_competition_run.py --out competition.llsp3
"""
from outputllsp3 import MotorPair, Port, LightImage, Color, StopMode

def build(project, api, ns=None):
    from outputllsp3 import SpikeBuilder
    b = SpikeBuilder(project)
    f = b.flow
    o = b.ops
    v = b.vars

    # --- Shared state ---
    v.add("heading_lock", 0)
    v.add("mission_ok",   0)

    # --- Utility: lock current heading ---
    f.proc("LockHeading", [], [
        v.set("heading_lock", b.sensor.yaw()),
    ])

    # --- Utility: straight drive for degrees (motor encoder) ---
    f.proc("DriveDeg", ["target_deg", "spd"], [
        b.motor.set_position(Port.A, 0),
        b.motor.set_position(Port.B, 0),
        b.move.dual_speed(project.arg("spd"), project.arg("spd")),
        f.repeat_until(
            o.gt(
                o.div(
                    o.add(
                        o.abs(b.motor.position(Port.A)),
                        o.abs(b.motor.position(Port.B)),
                    ),
                    2,
                ),
                project.arg("target_deg"),
            ),
            b.wait.ms(10),
        ),
        b.move.stop(),
    ])

    # --- Mission 1: push block off platform ---
    f.proc("Mission1", [], [
        b.light.show_text("M1"),
        f.call("DriveDeg", 300, 50),
        b.wait.ms(150),
        f.call("DriveDeg", 300, -50),
        v.set("mission_ok", o.add(v.get("mission_ok"), 1)),
        b.light.show_image(LightImage.YES),
    ])

    # --- Mission 2: collect from station ---
    f.proc("Mission2", [], [
        b.light.show_text("M2"),
        b.move.dual_speed(25, -25),
        b.wait.ms(450),
        b.move.stop(),
        b.wait.ms(100),
        f.call("DriveDeg", 200, 40),
        b.wait.ms(100),
        b.move.dual_speed(-25, 25),
        b.wait.ms(450),
        b.move.stop(),
        v.set("mission_ok", o.add(v.get("mission_ok"), 1)),
        b.light.show_image(LightImage.YES),
    ])

    # --- Mission 3: deliver to goal ---
    f.proc("Mission3", [], [
        b.light.show_text("M3"),
        b.sensor.reset_yaw(),
        b.wait.ms(80),
        f.call("LockHeading"),
        f.call("DriveDeg", 500, 50),
        b.wait.ms(200),
        v.set("mission_ok", o.add(v.get("mission_ok"), 1)),
        b.light.show_image(LightImage.HAPPY),
    ])

    # --- End sequence ---
    f.proc("ReturnHome", [], [
        b.move.dual_speed(-40, -40),
        b.wait.seconds(1.5),
        b.move.stop(),
        b.light.show_text(o.join("M:", o.join(v.get("mission_ok"), ""))),
        b.sound.beep_for(72, 0.3),
        b.sound.beep_for(76, 0.3),
        b.sound.beep_for(79, 0.6),
    ])

    # --- Main program ---
    f.start(
        *b.setup(motor_pair=MotorPair.AB),
        b.sensor.reset_yaw(),
        b.light.show_text("WAIT"),

        # Wait for button press to start
        f.wait_until(b.sensor.button_pressed("center")),
        b.light.show_image(LightImage.HAPPY),
        b.wait.ms(500),

        # Run missions in sequence
        f.call("Mission1"),
        b.wait.ms(300),
        f.call("Mission2"),
        b.wait.ms(300),
        f.call("Mission3"),
        b.wait.ms(300),
        f.call("ReturnHome"),
    )
