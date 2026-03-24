"""PID drivebase using SpikeBuilder + DrivebaseAPI.

Demonstrates:
- api.drivebase.install_pid_runtime() for a full PID-controlled robot
- api.robot helpers: straight_cm, turn_deg, pivot_left_deg
- SpikeBuilder for clean per-step blocks
- Composing a multi-step competition run sequence

Compile::

    outputllsp3 build examples/11_pid_robot.py --out pid_robot.llsp3
"""
from outputllsp3 import MotorPair

def build(project, api, ns=None):
    # Install PID runtime (creates ~6 procedures and ~20 variables)
    api.drivebase.install_pid_runtime(
        motor_pair="AB",
        wheel_diameter_mm=62.4,
        left_dir=1,
        right_dir=-1,
        speed_mid=420,
        speed_turn=260,
        speed_pivot=220,
    )

    f = api.flow
    r = api.robot

    # --- Competition run: navigate to target, pick up object, return ---
    f.procedure("CompRun", [], [
        # Leg 1: straight ahead 30 cm
        r.straight_cm(30),
        api.wait.ms(200),

        # Turn right 90°
        r.turn_deg(90),
        api.wait.ms(200),

        # Leg 2: approach target
        r.straight_cm(15),
        api.wait.ms(200),

        # Spin in place 180°
        r.pivot_left_deg(180),
        api.wait.ms(200),

        # Return home
        r.straight_cm(45),
        api.wait.ms(200),

        api.light.show_image("YES"),
        api.sound.beep_for(72, 0.5),
    ])

    # --- Main program ---
    f.start(
        r.setup(),                      # set motor pair
        api.sensor.reset_yaw(),
        api.light.show_text("READY"),
        api.flow.wait_until(
            api.sensor.button_pressed("center")
        ),
        api.light.show_image("HAPPY"),
        api.wait.ms(500),
        f.call("CompRun"),
        api.light.clear(),
    )
