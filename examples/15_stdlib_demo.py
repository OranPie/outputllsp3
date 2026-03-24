"""Example 15 — Standard Library (stdlib) procedures.

This example shows how to use the outputllsp3 standard library to install and
call reusable SPIKE procedure templates.  Three groups are available:

  math    — Clamp, MapRange, Sign
  timing  — WaitOrTimeout  (guarded wait with semaphore)
  display — Countdown, FlashText

Run::

    python3 examples/15_stdlib_demo.py
"""
from pathlib import Path

from outputllsp3 import LLSP3Project, API, Port
from outputllsp3.workflow import discover_defaults
from outputllsp3.stdlib import install_all

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
d = discover_defaults(ROOT)
project = LLSP3Project(d["template"], d["strings"])
api = API(project)

f  = api.flow   # FlowBuilder
v  = api.vars   # VarsAPI
o  = api.ops    # OpsAPI
sl = api.stdlib  # StdLib (fluent)

# Install all stdlib groups in one call via the fluent StdLib facade.
# This also tracks installed groups for introspection.
api.stdlib.all()

# ---------------------------------------------------------------------------
# Helper: add a result-variable declare
# ---------------------------------------------------------------------------
# (stdlib already declared MATH_CLAMP, MATH_MAP, MATH_SIGN, WAIT_DONE, …)

# ---------------------------------------------------------------------------
# Demo 1 — Clamp a raw yaw sensor value to motor speed range [-100, 100]
# ---------------------------------------------------------------------------
f.start(
    f.call("Clamp", api.sensor.yaw(), -100, 100),
    api.motor.run(Port.A, sl.clamp),         # sl.clamp → MATH_CLAMP reporter
    api.wait.seconds(2),
    api.motor.stop(Port.A),
)

# ---------------------------------------------------------------------------
# Demo 2 — MapRange: map yaw [-90, 90] → motor bias [-50, 50]
# ---------------------------------------------------------------------------
f.start(
    f.call("MapRange", api.sensor.yaw(), -90, 90, -50, 50),
    # MATH_MAP now holds the bias value
    api.motor.run(Port.A, o.add(50, sl.map_result)),
    api.motor.run(Port.B, o.sub(50, sl.map_result)),
    api.wait.seconds(1),
    api.motor.stop(Port.A),
    api.motor.stop(Port.B),
)

# ---------------------------------------------------------------------------
# Demo 3 — Sign: determine direction of tilt and spin accordingly
# ---------------------------------------------------------------------------
f.start(
    f.call("Sign", api.sensor.pitch()),       # −1, 0, or +1 in MATH_SIGN
    api.motor.run(Port.A, o.mul(sl.sign, 50)),  # forward or backward
    api.wait.seconds(1),
    api.motor.stop(Port.A),
)

# ---------------------------------------------------------------------------
# Demo 4 — WaitOrTimeout: wait for a button press with 5-second safety net
# ---------------------------------------------------------------------------
# Event hat: when left button pressed → signal WAIT_DONE = 1
f.when("button",
       sl.set_wait_done(1),   # sets WAIT_DONE = 1
       button="left")

# Main hat: reset semaphore → wait (up to 5 s) → drive
f.start(
    sl.reset_wait(),                         # sets WAIT_DONE = 0
    f.call("WaitOrTimeout", 5000),           # waits up to 5 000 ms
    api.motor.run(Port.A, 60),
    api.wait.seconds(2),
    api.motor.stop(Port.A),
)

# ---------------------------------------------------------------------------
# Demo 5 — Countdown then FlashText
# ---------------------------------------------------------------------------
f.start(
    f.call("Countdown", 3),           # shows 3 → 2 → 1 → 0 (1 s each)
    api.motor.run(Port.A, 80),
    api.wait.seconds(2),
    api.motor.stop(Port.A),
    f.call("FlashText", "DONE", 3),   # flashes "DONE" 3 times
)

# ---------------------------------------------------------------------------
# Demo 6 — Chaining multiple stdlib calls: clamp → sign → display result
# ---------------------------------------------------------------------------
f.start(
    # Read gyro pitch, clamp to [-45, 45], then get its sign
    f.call("Clamp", api.sensor.pitch(), -45, 45),
    f.call("Sign", sl.clamp),
    # Show the sign on the display (−1, 0, or +1)
    api.light.show_text(sl.sign),
    api.wait.seconds(2),
    api.light.clear(),
)

# ---------------------------------------------------------------------------
# Save the project
# ---------------------------------------------------------------------------
out = Path("/tmp/15_stdlib_demo.llsp3")
api.relayout()
project.save(out)
print(f"Saved → {out}")
print(f"Stdlib groups installed: {sl.installed_groups()}")
print(f"Stdlib procedures: {list(sl.proc_ids())}")
