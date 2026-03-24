"""Event handler hat blocks via ``api.flow.when()``.

``FlowBuilder.when()`` creates any SPIKE event hat block with a single,
unified call — no need to know opcode names or field layouts.

All handlers are placed in the **event column** (x ≈ 250) by the
LayoutManager, keeping them visually separate from the main entry points.
Call ``api.relayout()`` afterwards to tighten vertical spacing.

Supported event types
---------------------
  button      – hub button (left / right / center / any) + action
  gesture     – tapped / doubletapped / shake / freefall
  orientation – hub orientation (front / back / up / upside-down / …)
  tilted      – tilt direction (any / front / back / leftside / rightside)
  timer       – fires once when timer exceeds threshold
  color       – color sensor on a given port detects a color
  force       – force sensor pressed / released / hardpressed
  near        – distance sensor closer than a value
  far         – distance sensor farther than a value
  distance    – generic comparator (less_than / greater_than)
  broadcast   – receives a named broadcast message
  condition   – fires whenever a boolean expression becomes true

Compile::

    outputllsp3 build examples/14_event_handlers.py --out event_demo.llsp3
"""
from outputllsp3 import Port


def build(project, api, ns=None):
    f = api.flow

    # ── Main program ──────────────────────────────────────────────────────────
    f.start(
        api.light.show_text("READY"),
        api.wait.seconds(1),
        api.light.clear(),
    )

    # ── Button events ─────────────────────────────────────────────────────────
    f.when('button',
        api.motor.run(Port.A, 60),
        api.wait.seconds(2),
        api.motor.stop(Port.A),
        button='left', action='pressed',
    )

    f.when('button',
        api.motor.stop(Port.A),
        button='right', action='pressed',
    )

    # ── Gesture events ────────────────────────────────────────────────────────
    f.when('gesture',
        api.light.show_image("SURPRISED"),
        api.wait.seconds(0.5),
        api.light.clear(),
        gesture='tapped',
    )

    f.when('gesture',
        api.sound.beep_for(60, 0.2),
        api.sound.beep_for(64, 0.2),
        gesture='doubletapped',
    )

    f.when('gesture',
        api.motor.stop(Port.A),
        gesture='shake',
    )

    # ── Orientation event ─────────────────────────────────────────────────────
    f.when('orientation',
        api.light.show_image("SKULL"),
        value='upside-down',
    )

    # ── Timer event (fires once after 30 s) ───────────────────────────────────
    f.when('timer',
        api.motor.stop(Port.A),
        api.light.show_text("TIME"),
        threshold=30.0,
    )

    # ── Color sensor event ────────────────────────────────────────────────────
    f.when('color',
        api.motor.run(Port.A, 80),
        port=Port.C, color='red',
    )

    f.when('color',
        api.motor.stop(Port.A),
        port=Port.C, color='black',
    )

    # ── Force sensor event ────────────────────────────────────────────────────
    f.when('force',
        api.light.show_image("HEART"),
        port=Port.D, option='pressed',
    )

    # ── Distance events ───────────────────────────────────────────────────────
    f.when('near',
        api.motor.stop(Port.A),
        api.light.show_image("ANGRY"),
        port=Port.E, value=10,
    )

    f.when('far',
        api.motor.run(Port.A, 50),
        port=Port.E, value=30,
    )

    # ── Broadcast event ───────────────────────────────────────────────────────
    f.when('broadcast',
        api.light.show_text("GO"),
        api.motor.run(Port.A, 100),
        message='start',
    )

    # ── Condition event (fires when yaw exceeds 45°) ──────────────────────────
    f.when('condition',
        api.motor.stop(Port.A),
        condition=api.ops.gt(api.sensor.yaw(), 45),
    )

    # Re-compute positions so stacks don't overlap
    api.relayout()
