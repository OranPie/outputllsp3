"""Unified transpile() entry-point demo — build-script version.

Demonstrates how all three transpile modes work through a single entry point.
This file uses the build-script pattern so it can be compiled directly.

The three modes:
  - ``build_script``  — ``def build(project, api, ns)`` entry point (this file)
  - ``python_first``  — decorator-based style (robot.proc / run.main)
  - ``auto``          — transpile() detects the mode automatically from source

Compile::

    outputllsp3 build examples/07_transpile_unified.py --out transpile_unified.llsp3
"""
from outputllsp3 import MotorPair, Port

def build(project, api, ns=None):
    """Three-phase demo showing basic move → sense → react patterns."""
    f = api.flow
    v = api.vars
    o = api.ops
    sensor = api.sensor
    move   = api.move
    light  = api.light
    wait   = api.wait

    # Shared counter variable
    v.add("phase", 0)

    # --- Phase 1: Move forward 1 second ---
    f.procedure("Phase1", [], [
        v.set("phase", 1),
        light.show_text("FWD"),
        move.dual_speed(40, 40),
        wait.seconds(1),
        move.stop(),
    ])

    # --- Phase 2: Spin 90° using yaw ---
    f.procedure("Phase2", [], [
        v.set("phase", 2),
        light.show_text("SPIN"),
        sensor.reset_yaw(),
        f.repeat_until(
            o.gt(o.abs(sensor.yaw()), 85),
            move.dual_speed(25, -25),
            wait.ms(20),
        ),
        move.stop(),
    ])

    # --- Phase 3: Flash result ---
    f.procedure("Phase3", [], [
        v.set("phase", 3),
        light.show_image("HAPPY"),
        wait.ms(500),
        light.clear(),
        wait.ms(250),
        light.show_image("HAPPY"),
        wait.ms(500),
        light.clear(),
    ])

    # --- Main ---
    f.start(
        move.set_pair(MotorPair.AB),
        sensor.reset_yaw(),
        light.show_text("GO"),
        wait.ms(500),
        f.call("Phase1"),
        wait.ms(200),
        f.call("Phase2"),
        wait.ms(200),
        f.call("Phase3"),
    )
