from outputllsp3 import robot, run, port, ls

LEFT = port.A
RIGHT = port.B
log = ls.list("log")

@robot.proc
def square(side, speed):
    for _ in range(4):
        robot.forward_cm(side, speed)
        robot.turn_deg(90, 260)

@run.main
def main():
    robot.use_pair(RIGHT, LEFT)
    robot.set_direction(left=1, right=-1)
    log.append("start")
    square(20, 420)
    run.sleep_ms(200)
    log.append("done")
