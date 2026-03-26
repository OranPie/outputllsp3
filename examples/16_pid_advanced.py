"""Advanced PID drivebase — integral, EMA derivative filter, tuning guide.

Demonstrates the improved ``install_pid_runtime()`` parameters added in v0.36:

New parameters
--------------
``ki_straight`` / ``ki_turn``
    Integral gains (default 0 = pure PD).  Enable these when you see consistent
    heading drift on long straight runs caused by mechanical asymmetry.
``kd_alpha``
    Derivative EMA smoothing factor (0 < α ≤ 1).  ``1.0`` (default) = raw
    finite difference; ``0.3``–``0.5`` = light low-pass filter that reduces
    amplification of IMU noise in the D term.
``integral_max``
    Anti-windup clamp.  ``INTEGRAL`` accumulates error every tick but is clamped
    to ``[-integral_max, integral_max]``.  Prevents runaway accumulation during
    long stationary periods.

Tuning guide (in the SPIKE app — all gains are live variables)
--------------------------------------------------------------
1. Start with ``ki_straight = 0``, ``ki_turn = 0``, ``kd_alpha = 1.0``.
2. Tune ``KP_STRAIGHT`` until straight runs are close (no heavy oscillation).
3. Increase ``KD_STRAIGHT`` to dampen heading oscillation.
4. If drift remains after a long run, increase ``KI_STRAIGHT`` by 0.5 at a time.
5. For noisy IMU: set ``KD_ALPHA`` = 0.3–0.5 to smooth the derivative.
6. Repeat for turns using ``KP_TURN`` / ``KD_TURN`` / ``KI_TURN``.

PD pivot improvement
--------------------
PivotLeftDeg / PivotRightDeg are now PD-controlled (not open-loop constant
speed), so they decelerate naturally and overshoot less.  They share the turn
gains (``KP_TURN`` / ``KD_TURN``).

Compile::

    outputllsp3 build examples/16_pid_advanced.py --out pid_advanced.llsp3
"""
from outputllsp3 import MotorPair, Port, LightImage

def build(project, api, ns=None):
    # Install PID runtime with derivative smoothing and light integral correction.
    # kd_alpha=0.4: moderate derivative filter (good starting point for most robots).
    # ki_straight=0.3: small integral to correct long-run drift without overshoot.
    api.drivebase.install_pid_runtime(
        motor_pair="AB",
        wheel_diameter_mm=62.4,
        left_dir=1,
        right_dir=-1,
        kp_straight=22.0,
        ki_straight=0.3,
        kd_straight=34.0,
        kp_turn=10.0,
        ki_turn=0.0,
        kd_turn=18.0,
        kd_alpha=0.4,
        integral_max=100.0,
        speed_mid=420,
        speed_turn=260,
        speed_pivot=220,
    )

    f = api.flow
    r = api.robot
    light = api.light
    sound = api.sound
    wait  = api.wait

    # --- Mission: figure-8 pattern (two 90° turns) ---
    f.procedure("FigureEight", [], [
        r.straight_cm(25),
        wait.ms(150),
        r.turn_deg(90),
        wait.ms(150),
        r.straight_cm(25),
        wait.ms(150),
        r.turn_deg(-90),
        wait.ms(150),
        r.straight_cm(25),
        wait.ms(150),
        r.turn_deg(-90),
        wait.ms(150),
        r.straight_cm(25),
        wait.ms(150),
        r.turn_deg(90),
        wait.ms(150),
    ])

    # --- Mission: spin and return ---
    f.procedure("SpinReturn", [], [
        r.straight_cm(30),
        wait.ms(150),
        r.pivot_left_deg(180),   # Now PD-controlled: smooth decel to target
        wait.ms(150),
        r.straight_cm(30),
        wait.ms(150),
        r.pivot_right_deg(180),  # Return to original heading
        wait.ms(150),
    ])

    # --- Main ---
    f.start(
        r.setup(),
        api.sensor.reset_yaw(),
        light.show_text("READY"),
        f.wait_until(api.sensor.button_pressed("center")),
        light.show_image(LightImage.HAPPY),
        wait.ms(500),
        f.call("FigureEight"),
        wait.ms(300),
        f.call("SpinReturn"),
        light.show_image(LightImage.YES),
        sound.beep_for(72, 0.4),
        sound.beep_for(76, 0.4),
        sound.beep_for(79, 0.6),
    )
