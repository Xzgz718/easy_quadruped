"""Pupper robot configuration parameters.

Pupper 机器人的各类配置参数。
"""

import numpy as np
from pupper.ServoCalibration import MICROS_PER_RAD, NEUTRAL_ANGLE_DEGREES
from pupper.HardwareConfig import PS4_COLOR, PS4_DEACTIVATED_COLOR
from enum import Enum

# TODO: put these somewhere else
# TODO: 这些参数最好迁移到更合适的模块中
class PWMParams:
    """PWM output parameters.

    PWM 输出相关参数。
    """

    def __init__(self):
        # 3 个关节轴 × 4 条腿对应的 GPIO 引脚编号
        self.pins = np.array([[2, 14, 18, 23], [3, 15, 27, 24], [4, 17, 22, 25]])
        # pigpio 的 PWM 计数范围
        self.range = 4000
        # PWM 频率
        self.freq = 250


class ServoParams:
    """Servo calibration and neutral pose parameters.

    舵机标定与中立位姿参数。
    """

    def __init__(self):
        self.neutral_position_pwm = 1500  # Middle position
        # 中位 PWM 脉宽
        self.micros_per_rad = MICROS_PER_RAD  # Must be calibrated
        # 每弧度对应的 PWM 微秒数，需要标定得到

        # The neutral angle of the joint relative to the modeled zero-angle in degrees, for each joint
        # 各关节相对模型零位的中立角度，单位为度
        self.neutral_angle_degrees = NEUTRAL_ANGLE_DEGREES

        # 不同腿和关节的转向符号，用于将数学角度映射到真实舵机方向
        self.servo_multipliers = np.array(
            [[1, 1, 1, 1], [-1, 1, -1, 1], [1, -1, 1, -1]]
        )

    @property
    def neutral_angles(self):
        return self.neutral_angle_degrees * np.pi / 180.0  # Convert to radians
        # 将中立角从度转换为弧度


class Configuration:
    """Main robot controller configuration.

    机器人控制器的主配置。
    """

    def __init__(self):
        ################# CONTROLLER BASE COLOR ##############
        # 手柄默认灯光颜色
        self.ps4_color = PS4_COLOR    
        # 控制器失活时的灯光颜色
        self.ps4_deactivated_color = PS4_DEACTIVATED_COLOR    

        #################### COMMANDS ####################
        # 手柄输入允许的最大前向速度
        self.max_x_velocity = 0.4
        # 手柄输入允许的最大横向速度
        self.max_y_velocity = 0.3
        # 手柄输入允许的最大偏航角速度
        self.max_yaw_rate = 2.0
        # 最大俯仰角命令
        self.max_pitch = 30.0 * np.pi / 180.0
        
        #################### MOVEMENT PARAMS ####################
        # 高度控制一阶收敛时间常数
        self.z_time_constant = 0.02
        self.z_speed = 0.03  # maximum speed [m/s]
        # 机身高度变化最大速度 [m/s]
        self.pitch_deadband = 0.02
        # 俯仰输入死区
        self.pitch_time_constant = 0.25
        # 俯仰指令滤波时间常数
        self.max_pitch_rate = 0.15
        # 俯仰变化率上限
        self.roll_speed = 0.16  # maximum roll rate [rad/s]
        # 横滚变化最大角速度 [rad/s]
        self.yaw_time_constant = 0.3
        # 静止模式下偏航滤波时间常数
        self.max_stance_yaw = 1.2
        # 静止站姿允许的最大偏航角
        self.max_stance_yaw_rate = 2.0
        # 静止站姿允许的最大偏航变化率

        #################### STANCE ####################
        # 默认站姿下足端前后方向展开量
        self.delta_x = 0.1
        # 默认站姿下足端左右方向展开量
        self.delta_y = 0.09
        # 整个站姿在 x 方向的整体平移
        self.x_shift = 0.0
        # 默认机身参考高度
        self.default_z_ref = -0.16

        #################### SWING ######################
        # 摆腿高度轨迹多项式系数，当前未使用
        self.z_coeffs = None
        # 摆腿时足端离地高度
        self.z_clearance = 0.07
        self.alpha = (
            0.5  # Ratio between touchdown distance and total horizontal stance movement
        )
        # 落脚点与支撑期水平位移之间的比例系数
        self.beta = (
            0.5  # Ratio between touchdown distance and total horizontal stance movement
        )
        # 偏航运动下落脚点旋转补偿比例

        #################### GAIT #######################
        # 控制器离散时间步长
        self.dt = 0.01
        # 一个步态周期中包含的相位数
        self.num_phases = 4
        # 四条腿在各相位中的接触表，1 为支撑，0 为摆动
        self.contact_phases = np.array(
            [[1, 1, 1, 0], [1, 0, 1, 1], [1, 0, 1, 1], [1, 1, 1, 0]]
        )
        self.overlap_time = (
            0.10  # duration of the phase where all four feet are on the ground
        )
        # 四足都着地的相位持续时间
        self.swing_time = (
            0.15  # duration of the phase when only two feet are on the ground
        )
        # 两足着地、两足摆动的相位持续时间

        ######################## GEOMETRY ######################
        self.LEG_FB = 0.10  # front-back distance from center line to leg axis
        # 机身中心线到腿前后安装轴的距离
        self.LEG_LR = 0.04  # left-right distance from center line to leg plane
        # 机身中心线到腿平面的左右距离
        # 两段腿长参数
        self.LEG_L2 = 0.115
        self.LEG_L1 = 0.1235
        self.ABDUCTION_OFFSET = 0.03  # distance from abduction axis to leg
        # 外展轴到腿平面的偏移距离
        self.FOOT_RADIUS = 0.01
        # 足端半径

        # 机身髋部几何尺寸
        self.HIP_L = 0.0394
        self.HIP_W = 0.0744
        self.HIP_T = 0.0214
        self.HIP_OFFSET = 0.0132

        # 机身长宽厚
        self.L = 0.276
        self.W = 0.100
        self.T = 0.050

        # 四条腿在机身坐标系中的安装原点
        self.LEG_ORIGINS = np.array(
            [
                [self.LEG_FB, self.LEG_FB, -self.LEG_FB, -self.LEG_FB],
                [-self.LEG_LR, self.LEG_LR, -self.LEG_LR, self.LEG_LR],
                [0, 0, 0, 0],
            ]
        )

        # 四条腿的外展偏移方向，左腿为正，右腿为负
        self.ABDUCTION_OFFSETS = np.array(
            [
                -self.ABDUCTION_OFFSET,
                self.ABDUCTION_OFFSET,
                -self.ABDUCTION_OFFSET,
                self.ABDUCTION_OFFSET,
            ]
        )

        ################### INERTIAL ####################
        self.FRAME_MASS = 0.560  # kg
        # 机身框架质量 [kg]
        self.MODULE_MASS = 0.080  # kg
        # 单个髋部模块质量 [kg]
        self.LEG_MASS = 0.030  # kg
        # 单条腿连杆质量 [kg]
        self.MASS = self.FRAME_MASS + (self.MODULE_MASS + self.LEG_MASS) * 4

        # Compensation factor of 3 because the inertia measurement was just
        # of the carbon fiber and plastic parts of the frame and did not
        # include the hip servos and electronics
        # 惯量乘以 3 的补偿系数，因为原始测量未包含髋关节舵机与电子元件
        self.FRAME_INERTIA = tuple(
            map(lambda x: 3.0 * x, (1.844e-4, 1.254e-3, 1.337e-3))
        )
        # 单个髋部模块惯量
        self.MODULE_INERTIA = (3.698e-5, 7.127e-6, 4.075e-5)

        leg_z = 1e-6
        leg_mass = 0.010
        leg_x = 1 / 12 * self.LEG_L1 ** 2 * leg_mass
        leg_y = leg_x
        # 单条腿近似为细杆后的转动惯量
        self.LEG_INERTIA = (leg_x, leg_y, leg_z)

    @property
    def default_stance(self):
        """Default foot positions in the body frame.

        机身坐标系下的默认四足站姿。
        """
        return np.array(
            [
                [
                    self.delta_x + self.x_shift,
                    self.delta_x + self.x_shift,
                    -self.delta_x + self.x_shift,
                    -self.delta_x + self.x_shift,
                ],
                [-self.delta_y, self.delta_y, -self.delta_y, self.delta_y],
                [0, 0, 0, 0],
            ]
        )

    ################## SWING ###########################
    @property
    def z_clearance(self):
        """Swing foot clearance height.

        摆腿离地高度。
        """
        return self.__z_clearance

    @z_clearance.setter
    def z_clearance(self, z):
        # 更新摆腿离地高度，并为后续轨迹参数预留接口
        self.__z_clearance = z
        # b_z = np.array([0, 0, 0, 0, self.__z_clearance])
        # A_z = np.array(
        #     [
        #         [0, 0, 0, 0, 1],
        #         [1, 1, 1, 1, 1],
        #         [0, 0, 0, 1, 0],
        #         [4, 3, 2, 1, 0],
        #         [0.5 ** 4, 0.5 ** 3, 0.5 ** 2, 0.5 ** 1, 0.5 ** 0],
        #     ]
        # )
        # self.z_coeffs = solve(A_z, b_z)

    ########################### GAIT ####################
    @property
    def overlap_ticks(self):
        """Number of control ticks in overlap phase.

        四足同时支撑相对应的控制 tick 数。
        """
        return int(self.overlap_time / self.dt)

    @property
    def swing_ticks(self):
        """Number of control ticks in swing phase.

        摆动相对应的控制 tick 数。
        """
        return int(self.swing_time / self.dt)

    @property
    def stance_ticks(self):
        """Number of ticks for one stance interval.

        单次支撑区间的总 tick 数。
        """
        return 2 * self.overlap_ticks + self.swing_ticks

    @property
    def phase_ticks(self):
        """Ticks for each gait phase.

        各步态相位对应的 tick 数组。
        """
        return np.array(
            [self.overlap_ticks, self.swing_ticks, self.overlap_ticks, self.swing_ticks]
        )

    @property
    def phase_length(self):
        """Total ticks in one gait cycle.

        一个完整步态周期的总 tick 数。
        """
        return 2 * self.overlap_ticks + 2 * self.swing_ticks

        
class SimulationConfig:
    """Simulation-specific configuration.

    仿真环境使用的配置参数。
    """

    def __init__(self):
        # 输入/输出的 MuJoCo XML 文件名
        self.XML_IN = "pupper.xml"
        self.XML_OUT = "pupper_out.xml"

        # 初始机身高度
        self.START_HEIGHT = 0.3
        self.MU = 1.5  # coeff friction
        # 地面摩擦系数
        self.DT = 0.001  # seconds between simulation steps
        # 仿真步长
        self.JOINT_SOLREF = "0.001 1"  # time constant and damping ratio for joints
        # 关节约束求解器参数
        self.JOINT_SOLIMP = "0.9 0.95 0.001"  # joint constraint parameters
        # 关节约束软化参数
        self.GEOM_SOLREF = "0.01 1"  # time constant and damping ratio for geom contacts
        # 几何接触求解器参数
        self.GEOM_SOLIMP = "0.9 0.95 0.001"  # geometry contact parameters
        # 几何接触软化参数
        
        # Joint params
        # 关节与舵机参数
        G = 220  # Servo gear ratio
        # 舵机减速比
        m_rotor = 0.016  # Servo rotor mass
        # 转子质量
        r_rotor = 0.005  # Rotor radius
        # 转子半径
        self.ARMATURE = G ** 2 * m_rotor * r_rotor ** 2  # Inertia of rotational joints
        # 旋转关节等效电机转动惯量
        # print("Servo armature", self.ARMATURE)

        NATURAL_DAMPING = 1.0  # Damping resulting from friction
        # 摩擦等自然阻尼
        ELECTRICAL_DAMPING = 0.049  # Damping resulting from back-EMF
        # 反电动势带来的等效阻尼

        self.REV_DAMPING = (
            NATURAL_DAMPING + ELECTRICAL_DAMPING
        )  # Damping torque on the revolute joints
        # 转动关节总阻尼

        # Servo params
        self.SERVO_REV_KP = 300  # Position gain [Nm/rad]
        # 仿真中舵机位置控制增益 [Nm/rad]

        # Force limits
        # 力矩和转角限制
        self.MAX_JOINT_TORQUE = 3.0
        self.REVOLUTE_RANGE = 1.57
