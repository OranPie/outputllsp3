from outputllsp3 import ENUMS

def build(project, api, ns, enums=ENUMS):
    start = api.flow.start(x=-220, y=80)
    api.flow.chain(start,
        api.move.set_pair(enums.MotorPair.AB),
        api.sensor.reset_yaw(),
        api.move.start_dual_speed(30, 30),
        api.wait.seconds(0.5),
        api.move.stop(),
    )
