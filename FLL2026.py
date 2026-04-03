"""
Source:    ok.llsp3
Exported by outputllsp3 0.35.0  (python-first style)
Note:      readable approximation — not an exact round-trip

Blocks: 1059  |  Variables: 44  |  Procedures: 21
"""

from outputllsp3 import robot, run, port, Direction, StopMode, Axis, Unit, stdlib

# ── Variables ───────────────────────────────────────────────────────────────
任务次数 = 0
上一次偏差 = 0
偏差 = 0
p = 0
i = 0
d = 0
pid = 0
Vmax = '-70'
Vmin = '-30'
distance = '200'
P = '0'
I = '0'
D = '0'
积分 = '0'
微分 = '2'
上一次误差 = '19'
误差 = '19'
PID = '0'
V = '-70'
匀加速 = '1'
匀减速 = '1'
制动 = '0'
初始化 = 0
基数 = '12'
任务 = '13'
角度 = '0'
抬放 = '1'
复位电机_上一次相对位置 = '2112'
切换中 = '0'
yaw = '-2'

# ── Monitors ────────────────────────────────────────────────────────────────
robot.show_monitor('P')
robot.show_monitor('I')
robot.show_monitor('D')
robot.show_monitor('PID')
robot.show_monitor('任务次数')
robot.show_monitor('任务')
robot.show_monitor('角度')
robot.show_monitor('抬放')
robot.show_monitor('yaw')

# ── Procedures ──────────────────────────────────────────────────────────────

@robot.proc
def reset_all():
    robot.motor_go_to_position(port.A, Direction.SHORTEST, 0)
    robot.motor_go_to_position(port.E, Direction.SHORTEST, 0)
    robot.reset_yaw()
    PID = 0
    P = 0
    I = 0
    D = 0

@robot.proc
def 匀加速陀螺仪直线_是否匀加速(_1_0, vmax, 加速距离, 角度, KP):
    robot.reset_yaw()
    run.sleep(0.03)
    robot.set_motor_position(port.BC, 0)
    robot.set_stop_mode(port.BC, StopMode.COAST)
    V = 0
    Vmax = vmax
    Vmin = 30
    distance = 加速距离
    匀加速 = _1_0
    积分 = 0
    上一次误差 = 0
    while not ((abs(robot.motor_relative_position(port.B)) > 角度)):
        误差 = (0 - robot.angle(Axis.YAW))
        P = (误差 * KP)
        if (abs(误差) > 5):
            积分 = 0
            I = 0
        else:
            积分 = (误差 + 积分)
            I = (积分 * 0.1)
        微分 = (误差 - 上一次误差)
        D = (微分 * 5)
        PID = (P + (I + D))
        if (匀加速 == 1):
            if (V < Vmax):
                V = ((((Vmax - Vmin) / distance) * robot.motor_relative_position(port.C)) + Vmin)
            else:
                V = Vmax
        robot.run_motor_power(port.B, ((V + PID) * -1))
        robot.run_motor_power(port.C, (V - PID))
        上一次误差 = 误差
    robot.stop_motor(port.BC)

@robot.proc
def 匀减速陀螺仪直线_是否匀减速(_0_1, vmax, 距离, kp, _0_1_2):
    robot.set_motor_position(port.BC, 0)
    robot.set_stop_mode(port.BC, StopMode.HOLD)
    if (_0_1 == 1):
        robot.reset_yaw()
        run.sleep(0.03)
    V = 0
    Vmax = vmax
    Vmin = 20
    distance = 距离
    匀减速 = _0_1
    积分 = 0
    上一次误差 = 0
    while not ((abs(robot.motor_relative_position(port.B)) > (distance - 10))):
        误差 = (0 - robot.angle(Axis.YAW))
        P = (误差 * kp)
        if (abs(误差) > 5):
            积分 = 0
            I = 0
        else:
            积分 = (误差 + 积分)
            I = (积分 * 0.1)
        微分 = (误差 - 上一次误差)
        D = (微分 * 5)
        PID = (P + (I + D))
        if (匀减速 == 1):
            if (V > Vmin):
                V = ((((Vmin - Vmax) / distance) * robot.motor_relative_position(port.C)) + Vmax)
            else:
                V = Vmax
        robot.run_motor_power(port.B, ((V + PID) * -1))
        robot.run_motor_power(port.C, (V - PID))
        上一次误差 = 误差
    robot.stop_motor(port.BC)

@robot.proc
def B_C转向_方向(角度, 功率, kp, 精度, ki=0.0002, kd=2.0):
    robot.set_stop_mode(port.BC, StopMode.HOLD)
    robot.reset_yaw()
    run.sleep(0.03)
    for _ in range(2):
        上一次误差 = 0
        积分 = 0
        稳定计数 = 0
        max_iters = 400
        iters = 0
        run.reset_timer()
        上次检查角 = robot.angle(Axis.YAW)
        while 稳定计数 < 3 and iters < max_iters:
            iters += 1
            # Single gyro read per tick — consistent across error/watchdog/stable checks
            当前角 = robot.angle(Axis.YAW)
            误差 = 角度 - 当前角
            if 误差 > 180:
                误差 = 误差 - 360
            if 误差 < -180:
                误差 = 误差 + 360
            if abs(误差) < 精度:
                run.reset_timer()
                上次检查角 = 当前角
                稳定计数 += 1
                robot.stop_motor(port.BC)
                run.sleep(0.005)
                上一次误差 = 误差
                continue
            稳定计数 = 0
            if run.timer() > 0.2:
                if abs(当前角 - 上次检查角) < 0.2:
                    break
                run.reset_timer()
                上次检查角 = 当前角
            P = 误差 * kp
            if P > abs(功率):
                P = abs(功率)
            if P < (-1 * abs(功率)):
                P = (-1 * abs(功率))
            if abs(误差) < 20:
                积分 = 积分 + 误差
                if 积分 > 300:
                    积分 = 300
                if 积分 < -300:
                    积分 = -300
            else:
                积分 = 0
            I = 积分 * ki
            微分 = 误差 - 上一次误差
            if 微分 > 30:
                微分 = 30
            if 微分 < -30:
                微分 = -30
            D = 微分 * kd
            PID = P + I + D
            基数_raw = abs(误差) * 4
            if 基数_raw < 12:
                基数_raw = 12
            if 基数_raw > 15:
                基数_raw = 15
            if PID > 0:
                基数 = 基数_raw
            elif PID < 0:
                基数 = -基数_raw
            else:
                基数 = 0
            robot.run_motor_power(port.B, (-1 * (PID + 基数)))
            robot.run_motor_power(port.C, (-1 * (PID + 基数)))
            上一次误差 = 误差
        robot.stop_motor(port.BC)
        run.sleep(0.02)

@robot.proc
def 单电机转向_方向(角度, B_C, kp, 功率, 精度, ki=0.0001, kd=0.45):
    robot.set_stop_mode(port.BC, StopMode.HOLD)
    robot.reset_yaw()
    run.sleep(0.03)
    for _ in range(2):
        上一次误差 = 0
        积分 = 0
        稳定计数 = 0
        max_iters = 400
        iters = 0
        run.reset_timer()
        上次检查角 = robot.angle(Axis.YAW)
        while 稳定计数 < 3 and iters < max_iters:
            iters += 1
            # Single gyro read per tick — consistent across error/watchdog/stable checks
            当前角 = robot.angle(Axis.YAW)
            误差 = 角度 - 当前角
            if 误差 > 180:
                误差 = 误差 - 360
            if 误差 < -180:
                误差 = 误差 + 360
            if abs(误差) < 精度:
                run.reset_timer()
                上次检查角 = 当前角
                稳定计数 += 1
                robot.stop_motor(port.BC)
                run.sleep(0.005)
                上一次误差 = 误差
                continue
            稳定计数 = 0
            if run.timer() > 0.2:
                if abs(当前角 - 上次检查角) < 0.2:
                    break
                run.reset_timer()
                上次检查角 = 当前角
            P = 误差 * kp
            if P > abs(功率):
                P = abs(功率)
            if P < (-1 * abs(功率)):
                P = (-1 * abs(功率))
            if abs(误差) < 20:
                积分 = 积分 + 误差
                if 积分 > 300:
                    积分 = 300
                if 积分 < -300:
                    积分 = -300
            else:
                积分 = 0
            I = 积分 * ki
            微分 = 误差 - 上一次误差
            if 微分 > 30:
                微分 = 30
            if 微分 < -30:
                微分 = -30
            D = 微分 * kd
            PID = P + I + D
            基数_raw = abs(误差) * 4
            if 基数_raw < 12:
                基数_raw = 12
            if 基数_raw > 15:
                基数_raw = 15
            if PID > 0:
                基数 = 基数_raw
            elif PID < 0:
                基数 = -基数_raw
            else:
                基数 = 0
            robot.run_motor_power(B_C, (-1 * (PID + 基数)))
            上一次误差 = 误差
        robot.stop_motor(port.BC)
        run.sleep(0.02)

@robot.proc
def 转向移动_方向(左右, 转向角度, 移动角度, 功率=45, kp=1.1):
    robot.set_stop_mode(port.BC, StopMode.HOLD)
    robot.reset_yaw()
    run.sleep(0.03)
    robot.set_motor_position(port.BC, 0)
    目标角 = abs(转向角度)
    目标距离 = abs(移动角度)
    积分 = 0
    上一次误差 = 0
    while not ((abs(robot.motor_relative_position(port.B)) > 目标距离) or (abs(robot.motor_relative_position(port.C)) > 目标距离)):
        当前角 = robot.angle(Axis.YAW)
        if (左右 == 'left'):
            误差 = (-1 * 目标角) - 当前角
        else:
            误差 = 目标角 - 当前角
        P = (误差 * kp)
        if P > abs(功率):
            P = abs(功率)
        if P < (-1 * abs(功率)):
            P = (-1 * abs(功率))
        if (abs(误差) < 15):
            积分 = (积分 + 误差)
            if 积分 > 200:
                积分 = 200
            if 积分 < -200:
                积分 = -200
        else:
            积分 = 0
        I = (积分 * 0.0002)
        微分 = (误差 - 上一次误差)
        if 微分 > 25:
            微分 = 25
        if 微分 < -25:
            微分 = -25
        D = (微分 * 1.2)
        PID = (P + (I + D))
        基础速度 = abs(功率)
        if (左右 == 'left'):
            robot.run_motor_power(port.B, ((基础速度 + PID) * -1))
            stdlib.max(8, (基础速度 - PID))
            robot.run_motor_power(port.C, stdlib.max)
        else:
            stdlib.max(8, (基础速度 + PID))
            robot.run_motor_power(port.B, (stdlib.max * -1))
            robot.run_motor_power(port.C, (基础速度 - PID))
        上一次误差 = 误差
    robot.stop_motor(port.BC)
    run.sleep(0.01)

@robot.proc
def 直行时间_时间(时间, kp, 速度, _0_1):
    run.reset_timer()
    积分 = 0
    上一次偏差 = 0
    while not ((run.timer() > 时间)):
        偏差 = (0 - robot.angle(Axis.YAW))
        p = (kp * 偏差)
        if (abs(偏差) < 5):
            积分 = (积分 + 偏差)
            i = (0.1 * 积分)
        else:
            积分 = 0
            i = 0
        微分 = (偏差 - 上一次偏差)
        d = (5 * 微分)
        上一次偏差 = 偏差
        pid = ((p + i) + d)
        robot.run_motor_power(port.B, ((速度 + pid) * -1))
        robot.run_motor_power(port.C, (速度 - pid))
    if (_0_1 == 1):
        robot.set_stop_mode(port.BC, StopMode.HOLD)
        robot.stop_motor(port.BC)
    if (_0_1 == 0):
        robot.set_stop_mode(port.BC, StopMode.COAST)
        robot.stop_motor(port.BC)
    run.sleep(0.01)

@robot.proc
def 匀加速陀螺仪后退_方向(方向, Vmax, 加速距离, 角度, KP):
    robot.reset_yaw()
    run.sleep(0.03)
    robot.set_motor_position(port.BC, 0)
    robot.set_stop_mode(port.BC, StopMode.COAST)
    V = 0
    Vmax = Vmax
    Vmin = -30
    distance = 加速距离
    匀加速 = 1
    积分 = 0
    上一次误差 = 0
    while not ((abs(robot.motor_relative_position(port.C)) > 角度)):
        误差 = (方向 - robot.angle(Axis.YAW))
        P = (误差 * KP)
        if (abs(误差) > 5):
            积分 = 0
            I = 0
        else:
            积分 = (误差 + 积分)
            I = (积分 * 0.1)
        微分 = (误差 - 上一次误差)
        D = (微分 * 0.9)
        PID = (P + (I + D))
        if (匀加速 == 1):
            if (abs(V) < abs(Vmax)):
                V = (((((abs(Vmax) - abs(Vmin)) / distance) * robot.motor_relative_position(port.B)) + abs(Vmin)) * -1)
            else:
                V = Vmax
        robot.run_motor_power(port.B, ((V + PID) * -1))
        robot.run_motor_power(port.C, (V - PID))
        上一次误差 = 误差
    robot.stop_motor(port.BC)
    run.sleep(0.01)

@robot.proc
def 复位电机_端口(端口, 方向, 功率):
    robot.note('运行直到卡住')
    robot.set_motor_position(端口, 0)
    复位电机_上一次相对位置 = robot.motor_relative_position(端口)
    robot.run_motor_power(端口, (方向 * 功率))
    run.sleep(0.08)
    while not ((robot.button_pressed('right') or (abs((复位电机_上一次相对位置 - robot.motor_relative_position(端口))) < 5))):
        if (abs((复位电机_上一次相对位置 - robot.motor_relative_position(端口))) < 20):
            robot.run_motor_power(端口, ((方向 * 功率) * 0.3))
        else:
            robot.run_motor_power(端口, (方向 * 功率))
        复位电机_上一次相对位置 = robot.motor_relative_position(端口)
        run.sleep(0.05)
    robot.stop_motor(端口)

@robot.proc
def _11():
    robot.set_motor_acceleration(port.BC, 3000)
    匀加速陀螺仪直线_是否匀加速(1, 50, 100, 200, 1.1)
    单电机转向_方向(-90, 'C', 1.1, 60, 1)
    匀加速陀螺仪直线_是否匀加速(1, 100, 300, 1000, 1.1)
    B_C转向_方向(-90, 60, 1.1,1)
    匀加速陀螺仪直线_是否匀加速(1, 40, 100, 230, 1.1)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 5, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -50, 100, 230, 1.1)
    B_C转向_方向(90, 60, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -100, 200, 980, 1.1)
    单电机转向_方向(90, 'C', 1.1, 60, 1)
    匀加速陀螺仪后退_方向(0, -50, 100, 200, 1.1)

@robot.proc
def _12():
    robot.set_motor_acceleration(port.BC, 3000)
    复位电机_端口('A', 1, 50)
    robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 1, Unit.ROTATIONS)
    robot.show_text('R')
    run.wait_until(lambda: robot.button_pressed('right'))
    robot.show_text('G')
    匀加速陀螺仪直线_是否匀加速(1, 80, 200, ((60 / 19.6) * 360), 1.1)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 0.3, Unit.ROTATIONS)
    run.sleep(0.2)
    robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 0.3, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -80, 200, ((60 / 19.6) * 360), 1)

@robot.proc
def _10():
    robot.set_motor_acceleration(port.BC, 3000)
    匀加速陀螺仪直线_是否匀加速(1, 50, 100, 200, 1.1)
    单电机转向_方向(-90, 'C', 1.1, 60, 1)
    匀加速陀螺仪直线_是否匀加速(1, 100, 200, 800, 1.1)
    单电机转向_方向(90, 'C', 1.1, 60, 1)
    匀加速陀螺仪直线_是否匀加速(1, 100, 200, 450, 1.1)
    匀加速陀螺仪后退_方向(0, -50, 200, 200, 1.1)
    单电机转向_方向(-90, 'C', 1.1, 60, 1)
    匀加速陀螺仪后退_方向(0, -70, 200, 900, 1.1)

@robot.proc
def _09_01():
    robot.note("""不能合起来，程序bug
Todo速度提升""")
    robot.set_motor_acceleration(port.BC, 3000)
    匀加速陀螺仪后退_方向(0, -50, 100, 555, 1.1)
    B_C转向_方向(90, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 40, 50, 100, 1.1)
    B_C转向_方向(90, 65, 1.1, 1)
    单电机转向_方向(-160, 'C', 1.1, 60, 3)
    单电机转向_方向(-80, 'C', 1.1, 60, 3)
    单电机转向_方向(-120, 'C', 1.1, 60, 3)
    B_C转向_方向(180, 50, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -70, 200, 1200, 1.1)
    单电机转向_方向(-90, 'B', 1.1, 65, 1)
    匀加速陀螺仪后退_方向(0, -70, 200, 700, 1.1)
    B_C转向_方向(-60, 65, 1.1, 1)
    B_C转向_方向(-75, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -65, 200, 600, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 70, 200, 400, 1.1)
    B_C转向_方向(50, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -70, 200, 1000, 1.1)
    B_C转向_方向(90, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 80, 200, 1200, 1.1)

@robot.proc
def _09_02():
    robot.note("""Bug 不能合起来
Bug 不能合起来""")
    pass

#TODO EDIT
@robot.proc
def _03_04():
    匀加速陀螺仪直线_是否匀加速(1, 60, 200, 400, 1.1)
    B_C转向_方向(180, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -60, 300, 1030, 1.1)
    B_C转向_方向(-95, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 20, 50, 130, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 20, 100, 150, 1.1)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 1.6, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -20, 150, 250, 1.1)
    B_C转向_方向(90, 65, 1.1, 3)
    匀加速陀螺仪直线_是否匀加速(1, 80, 200, 1200, 1.1)

@robot.proc
def _13():
    匀加速陀螺仪直线_是否匀加速(1, 50, 100, 400, 1.1)
    B_C转向_方向(-90, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 100, 200, 1235, 1.1)
    B_C转向_方向(45, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 30, 200, 200, 1.1)
    robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 0.8, Unit.ROTATIONS)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 0.8, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -30, 100, 200, 1.1)
    B_C转向_方向(-45, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -100, 100, 1300, 1.1)

@robot.proc
def _07():
    匀加速陀螺仪直线_是否匀加速(1, 60, 200, 300, 1.1)
    B_C转向_方向(90, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 60, 200, 300, 1.1)
    B_C转向_方向(-90, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 60, 200, 1200, 1.1)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 1, Unit.ROTATIONS)
    单电机转向_方向(-20, 'C', 1.1, 65, 1)
    robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 1, Unit.ROTATIONS)
    单电机转向_方向(20, 'C', 1.1, 65, 1)
    匀加速陀螺仪后退_方向(0, 65, 200, 1200, 1.1)

@robot.proc
def _08():
    匀加速陀螺仪直线_是否匀加速(1, 80, 200, (((20 - 0.5) / 27) * 500), 1.1)
    for _ in range(1, 5):
        robot.run_motor_for(port.A, Direction.CLOCKWISE, 0.8, Unit.SECONDS)
        robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 0.8, Unit.SECONDS)
    匀加速陀螺仪后退_方向(0, -90, 200, (((30 - 0.5) / 27) * 500), 1.1)

@robot.proc
def _05_06_07():
    匀加速陀螺仪后退_方向(0, -70, 200, 995, 1.1)
    B_C转向_方向(28, 65, 1.1, 1)
    robot.run_motor_for(port.E, Direction.CLOCKWISE, 1, Unit.ROTATIONS)
    run.sleep(0.5)
    匀加速陀螺仪后退_方向(0, -40, 50, 160, 1.1)
    robot.run_motor_for(port.E, Direction.COUNTERCLOCKWISE, 1, Unit.ROTATIONS)
    匀加速陀螺仪直线_是否匀加速(1, 20, 50, 150, 1.1)
    B_C转向_方向(-28, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -40, 50, 200, 1.1)
    单电机转向_方向(-85, 'B', 1.1, 65, 1)
    单电机转向_方向(50, 'B', 1.1, 65, 1)
    匀加速陀螺仪直线_是否匀加速(1, 40, 100, 150, 1.1)
    B_C转向_方向(84, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 50, 200, 100, 1.1)
    B_C转向_方向(90, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -70, 200, 500, 1.1)

@robot.proc
def _14():
    robot.set_motor_acceleration(port.BC, 3000)
    匀加速陀螺仪直线_是否匀加速(1, 65, 200, (2.9 * 360), 1.1)
    匀加速陀螺仪后退_方向(0, -45, 80, (0.8 * 360), 1.1)
    转向移动_方向('left', 50, 80, 40, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 45, 80, (1 * 360), 1.1)
    转向移动_方向('right', 10, 330, 40, 1.1)
    转向移动_方向('right', 60, 320, 40, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 45, 80, (1 * 360), 1.1)
    转向移动_方向('right', 30, 80, 40, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 45, 80, (1 * 360), 1.1)
    转向移动_方向('left', 25, (0.5 * 360), 40, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 50, 100, (1.5 * 360), 1.1)
    转向移动_方向('left', 30, (0.3 * 360), 35, 1.1)
    转向移动_方向('left', 70, 120, 35, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 30, 50, (0.3 * 360), 1.1)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 0.5, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -50, 100, (1 * 360), 1.1)
    转向移动_方向('right', 20, (2 * 360), 45, 1.1)
    转向移动_方向('right', 25, (1 * 360), 45, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 70, 200, (3 * 360), 1.1)

# ── Entry point(s) ──────────────────────────────────────────────────────────

@run.main
def main():
    reset_all()
    任务 = 0
    robot.hub_display_orientation('1')
    robot.hub_display_rotate(Direction.CLOCKWISE)
    robot.hub_show_image(90009990009000097218560)
    run.broadcast('启动控制程序')

# ── Event handlers ──────────────────────────────────────────────────────────

@run.when_broadcast('启动控制程序')
def on_broadcast():
    while True:
        if robot.button_pressed('left'):
            run.wait_until(lambda: robot.button_released('left'))
            任务 = (任务 + 1)
            if (任务 > 14):
                任务 = 1
            robot.show_text(任务)
        yaw = robot.angle(Axis.YAW)

@run.when_condition(lambda: (任务 == 2))
def on_condition():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(任务)
    robot.set_center_light('1')
    robot.set_motor_acceleration(port.BC, 3000)
    复位电机_端口('A', 1, 50)
    匀加速陀螺仪直线_是否匀加速(1, 85, 200, ((70 / 19.6) * 360), 1.1)
    B_C转向_方向(-45, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 60, 200, 400, 1.1)
    robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 2, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, 60, 100, 50, 1.1)
    匀加速陀螺仪直线_是否匀加速(1, 60, 100, 50, 1.1)
    robot.run_motor_for(port.A, Direction.CLOCKWISE, 2, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -60, 100, 200, 1.1)
    B_C转向_方向(45, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -90, 100, ((70 / 19.6) * 360), 1.1)

@run.when_condition(lambda: (任务 == 3))
def on_condition_2():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(12)
    robot.set_center_light('1')
    _12()

@run.when_condition(lambda: (任务 == 4))
def on_condition_3():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(11)
    robot.set_center_light('1')
    _11()

@run.when_condition(lambda: (任务 == 1))
def on_condition_4():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(任务)
    robot.set_center_light('1')
    robot.set_motor_acceleration(port.BC, 3000)
    复位电机_端口('A', 1, 65)
    匀加速陀螺仪直线_是否匀加速(1, 85, 200, 1040, 1.1)
    B_C转向_方向(-90, 90, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 65, 200, 230, 1.1)
    robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 7, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -60, 200, 200, 1.1)
    B_C转向_方向(90, 90, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -80, 200, 1060, 1.1)

@run.when_condition(lambda: (任务 == 5))
def on_condition_5():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(10)
    robot.set_center_light('1')
    _10()

@run.when_condition(lambda: (任务 == 6))
def on_condition_6():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text('9-1')
    robot.set_center_light('1')
    _09_01()

@run.when_condition(lambda: (任务 == 7))
def on_condition_7():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text('9-2')
    robot.set_center_light('1')
    _09_02()

@run.when_condition(lambda: (任务 == 8))
def on_condition_8():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text('03+04')
    robot.set_center_light('1')
    _03_04()

@run.when_condition(lambda: (任务 == 9))
def on_condition_9():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(13)
    robot.set_center_light('1')
    _13()

@run.when_condition(lambda: (任务 == 10))
def on_condition_10():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(7)
    robot.set_center_light('1')
    _07()

@run.when_condition(lambda: (任务 == 11))
def on_condition_11():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(8)
    robot.set_center_light('1')
    _07()

@run.when_condition(lambda: (任务 == 12))
def on_condition_12():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text('05+06')
    robot.set_center_light('1')
    _05_06_07()

@run.when_condition(lambda: (任务 == 13))
def on_condition_13():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(8)
    robot.set_center_light('1')
    robot.set_motor_speed(port.A, 75)
    匀加速陀螺仪直线_是否匀加速(1, 65, 200, (((35 - 0.5) / 27) * 500), 1.1)
    B_C转向_方向(45, 65, 1.1, 1)
    匀加速陀螺仪直线_是否匀加速(1, 35, 50, 50, 1.1)
    robot.set_stop_mode(port.A, StopMode.BRAKE)
    for _ in range(3):
        robot.run_motor_for(port.A, Direction.COUNTERCLOCKWISE, 1.5, Unit.ROTATIONS)
        run.sleep(0.4)
        robot.run_motor_for(port.A, Direction.CLOCKWISE, 1.5, Unit.ROTATIONS)
    匀加速陀螺仪后退_方向(0, -60, 200, 200, 1.1)
    B_C转向_方向(-45, 65, 1.1, 1)
    匀加速陀螺仪后退_方向(0, -60, 200, 500, 1.1)

@run.when_condition(lambda: (任务 == 14))
def on_condition_14():
    run.stop_other_stacks()
    run.broadcast('启动控制程序')
    robot.show_text(14)
    robot.set_center_light('1')
    _14()
