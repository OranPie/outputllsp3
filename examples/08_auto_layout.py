"""Auto-layout system: no more magic coordinate numbers.

Demonstrates:
- Multiple api.flow.start() blocks without x/y — LayoutManager places them
- Multiple api.flow.procedure() blocks without x/y — spread horizontally
- Explicit x/y override still works when you need fine-grained control
- Inspecting block positions after placement

Compile::

    outputllsp3 build examples/08_auto_layout.py --out layout.llsp3
"""
from outputllsp3 import MotorPair

def build(project, api, ns=None):
    f = api.flow

    # Define several procedures — they spread horizontally automatically
    f.procedure("Init", [], [
        api.move.set_pair(MotorPair.AB),
        api.sensor.reset_yaw(),
    ])

    f.procedure("Forward20", [], [
        api.move.dual_speed(30, 30),
        api.wait.seconds(1),
        api.move.stop(),
    ])

    f.procedure("TurnRight", [], [
        api.move.dual_speed(25, -25),
        api.wait.ms(400),
        api.move.stop(),
    ])

    f.procedure("Celebrate", [], [
        api.light.show_image("HAPPY"),
        api.sound.beep_for(72, 0.3),
        api.sound.beep_for(76, 0.3),
        api.sound.beep_for(79, 0.5),
    ])

    # First start block — placed at y=90 automatically
    f.start(
        f.call("Init"),
        f.call("Forward20"),
        f.call("TurnRight"),
        f.call("Forward20"),
        f.call("Celebrate"),
    )

    # Second start block — LayoutManager bumps y to ~590 automatically
    # (e.g. a test/debug sequence that runs in parallel)
    f.start(
        api.light.show_text("BOOT"),
        api.wait.seconds(0.5),
        api.light.clear(),
    )

    # Explicit override — pin this block to a specific canvas position
    f.start(
        api.sound.beep(60),
        x=-220, y=1200,
    )
