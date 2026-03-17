from outputllsp3 import robot, run, port, ls

# Demonstrates custom procedure return values.
# Each @robot.proc that uses `return` gets a unique __retval_<name> variable
# so the caller can read the result right after calling the procedure.

LEFT = port.B
RIGHT = port.A

log = ls.list("log")


@robot.proc
def clamp(val, lo, hi):
    """Return val clamped to [lo, hi]."""
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val


@robot.proc
def abs_val(x):
    """Return the absolute value of x."""
    if x < 0:
        return x * -1
    return x


@run.main
def main():
    robot.use_pair(RIGHT, LEFT)
    robot.set_direction(left=1, right=-1)

    # Call procs and capture their return values.
    speed = clamp(500, 0, 420)
    dist = abs_val(-20)

    log.append("speed")
    log.append(speed)
    log.append("dist")
    log.append(dist)

    robot.forward_cm(dist, speed)
    run.sleep_ms(200)
    robot.stop()
