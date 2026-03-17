from outputllsp3 import robot, run, port, ls

# Demonstrates default parameter values for @robot.proc procedures.
# Any param with a default can be omitted at the call site; the default is
# automatically substituted.  Keyword arguments are also supported.

LEFT = port.B
RIGHT = port.A


@robot.proc
def move_square(side=20, speed=420):
    """Drive a square with optional side length and speed."""
    for _ in range(4):
        robot.forward_cm(side, speed)
        robot.turn_deg(90, 260)


@robot.proc
def clamp(val, lo=0, hi=100):
    """Return val clamped to [lo, hi] (defaults: lo=0, hi=100)."""
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val


@robot.proc
def pivot_both(angle=90, speed=220):
    """Pivot the robot by angle degrees (default 90°) at given speed."""
    robot.pivot_left(angle, speed)


@run.main
def main():
    robot.use_pair(RIGHT, LEFT)
    robot.set_direction(left=1, right=-1)

    # All defaults: side=20, speed=420
    move_square()

    # Override side only; speed uses default
    move_square(30)

    # Override both
    move_square(15, 300)

    # Keyword arg: use default side, override speed
    move_square(speed=350)

    # Clamp with default lo/hi
    a = clamp(50)       # → 50
    b = clamp(-5)       # → 0  (uses lo=0)
    c = clamp(150)      # → 100 (uses hi=100)

    # Clamp with explicit bounds
    d = clamp(50, 10, 90)  # → 50

    # Keyword arg on clamp
    e = clamp(200, hi=80)  # → 80

    robot.stop()
