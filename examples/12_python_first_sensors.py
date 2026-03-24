"""Python-first style: sensors, lists, and control flow.

Demonstrates:
- @robot.proc with sensor expression arguments
- ls.list() for data logging
- run.sleep_ms() for timing
- robot.angle(), robot.motor_relative_position() (expression stubs)
- Multi-proc composition

Compile::

    outputllsp3 build-python examples/12_python_first_sensors.py --out pf_sensors.llsp3
"""
from outputllsp3 import robot, run, port, ls

LEFT  = port.A
RIGHT = port.B
log   = ls.list("sensor_log")
imu   = ls.list("imu_samples")


@robot.proc
def sample_imu(n_samples):
    """Record n_samples IMU readings into imu list."""
    imu.clear()
    for _ in range(n_samples):
        imu.append(robot.angle("yaw"))
        run.sleep_ms(50)


@robot.proc
def drive_straight_corrected(dist_cm, speed):
    """Drive forward with simple yaw correction."""
    robot.reset_yaw()
    run.sleep_ms(80)
    robot.forward_cm(dist_cm, speed)


@robot.proc
def scan_color(port_id):
    """Log a color reading from the given port."""
    log.append("color")
    # robot.color(port_id) would be an expression; log the port as label
    log.append(port_id)


@robot.proc
def find_line(max_tries):
    """Inch forward until a dark color is detected (simulated with counter)."""
    tries = 0
    while tries < max_tries:
        robot.forward_cm(2, 200)
        tries = tries + 1
        if tries > max_tries:
            return


@run.main
def main():
    robot.use_pair(RIGHT, LEFT)
    robot.set_direction(left=1, right=-1)

    log.clear()
    log.append("start")

    # Sample IMU before moving
    sample_imu(5)

    # Drive with correction
    drive_straight_corrected(30, 420)
    run.sleep_ms(200)

    # Scan color on port D
    scan_color("D")

    # Find line
    find_line(10)
    run.sleep_ms(200)

    # Turn and return
    robot.turn_deg(180, 260)
    drive_straight_corrected(30, 420)

    log.append("done")
    robot.show_text("OK")
    robot.stop()
