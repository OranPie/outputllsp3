"""Minimal SpikeBuilder example — the simplest robot program.

Demonstrates:
- Creating a SpikeBuilder from an LLSP3Project
- b.setup() one-liner robot init
- b.flow.start() to wire a program-start hat
- b.move, b.wait, b.sensor sub-namespaces
- Typed Port and MotorPair enums

Compile::

    outputllsp3 build examples/01_spike_builder_hello.py --out hello.llsp3
"""
from outputllsp3 import MotorPair, Port

def build(project, api, ns=None):
    from outputllsp3 import SpikeBuilder
    b = SpikeBuilder(project)

    b.flow.start(
        *b.setup(motor_pair=MotorPair.AB),   # set pair + reset positions
        b.sensor.reset_yaw(),
        b.move.dual_speed(30, 30),
        b.wait.seconds(0.5),
        b.move.stop(),
    )
