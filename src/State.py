"""控制器长期状态数据结构。"""

import numpy as np
from enum import Enum


class State:
    """保存控制器跨周期持续维护的内部状态。"""

    def __init__(self):
        # 控制器期望的机身水平速度指令，格式为 [vx, vy]
        self.horizontal_velocity = np.array([0.0, 0.0])
        # 控制器期望的偏航角速度指令
        self.yaw_rate = 0.0
        # 机身目标高度（机身坐标系下的 z 方向）
        self.height = -0.16
        # 机身目标俯仰角
        self.pitch = 0.0
        # 机身目标横滚角
        self.roll = 0.0
        # 控制器激活状态标记，通常由遥控器或上层逻辑切换
        self.activation = 0
        # 当前行为状态，如静止、对角小跑、跳跃等
        self.behavior_state = BehaviorState.REST

        # 控制循环已经运行的 tick 计数
        self.ticks = 0
        # 期望足端位置，形状为 (3, 4)，分别对应 xyz 和四条腿
        self.foot_locations = np.zeros((3, 4))
        # 期望关节角，形状为 (3, 4)
        self.joint_angles = np.zeros((3, 4))
        # 期望关节角速度，形状为 (3, 4)
        self.joint_velocities = np.zeros((3, 4))
        # 实际测得的足端位置，形状为 (3, 4)
        self.measured_foot_locations = np.zeros((3, 4))
        # 实际测得的关节角，形状为 (3, 4)
        self.measured_joint_angles = np.zeros((3, 4))
        # 实际测得的关节角速度，形状为 (3, 4)
        self.measured_joint_velocities = np.zeros((3, 4))
        # 机身姿态四元数，格式为 [w, x, y, z]
        self.quat_orientation = np.array([1.0, 0.0, 0.0, 0.0])
        # 机身在世界坐标系中的位置，格式为 [x, y, z]
        self.body_position = np.zeros(3)
        # 机身在世界坐标系中的线速度，格式为 [vx, vy, vz]
        self.body_velocity = np.zeros(3)
        # 机身角速度，格式为 [wx, wy, wz]
        self.angular_velocity = np.zeros(3)
        # 四足足端接触力估计，长度为 4
        self.foot_forces = np.zeros(4)
        # 四足接触状态估计，True 表示该腿当前认为处于接触
        self.contact_estimate = np.zeros(4, dtype=bool)

        # 初始化为静止模式
        self.behavior_state = BehaviorState.REST


class BehaviorState(Enum):
    """控制器支持的行为状态枚举。"""

    DEACTIVATED = -1
    REST = 0
    TROT = 1
    HOP = 2
    FINISHHOP = 3
