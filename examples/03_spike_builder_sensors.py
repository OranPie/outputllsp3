"""Sensor-reactive program using SpikeBuilder.

Demonstrates:
- b.sensor.color(), b.sensor.distance(), b.sensor.force_is_pressed()
- b.flow.if_() and b.flow.if_else() with sensor expressions
- b.flow.wait_until() to block on a condition
- Color and Comparator enums for readable threshold checks
- b.light and b.sound reacting to sensor state

Compile::

    outputllsp3 build examples/03_spike_builder_sensors.py --out sensors.llsp3
"""
from outputllsp3 import MotorPair, Port, Color, Comparator

def build(project, api, ns=None):
    from outputllsp3 import SpikeBuilder
    b = SpikeBuilder(project)

    # Wait until force sensor is pressed, then react to color.
    b.flow.start(
        *b.setup(motor_pair=MotorPair.AB),

        # Show "READY" and wait for the force button press
        b.light.show_text("READY"),
        b.flow.wait_until(b.sensor.force_is_pressed(Port.C)),

        # React: show color reading on display, drive based on it
        b.light.show_text("GO"),
        b.flow.forever(
            b.flow.if_else(
                b.sensor.color_is(Port.D, Color.RED),
                [
                    # Red → stop and beep
                    b.move.stop(),
                    b.sound.beep(48),
                    b.light.show_image("NO"),
                ],
                [
                    # Not red → drive forward
                    b.move.dual_speed(30, 30),
                    b.light.show_image("HAPPY"),
                ],
            ),
            # Also stop if obstacle is close
            b.flow.if_(
                b.sensor.distance_is(Port.E, Comparator.LESS_THAN, 15),
                b.move.stop(),
                b.sound.beep(60),
            ),
            b.wait.ms(50),
        ),
    )
