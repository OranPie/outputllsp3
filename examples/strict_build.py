from outputllsp3 import ENUMS

def build(project, api, ns=None):
    api.flow.start(
        api.move.set_pair(ENUMS.MotorPair.AB),
        api.sensor.reset_yaw(),
        api.move.dual_speed(20, 20),
        api.wait.ms(200),
        api.move.stop(),
    )
