"""控制器输入命令的数据结构。"""

import numpy as np


class Command:
    """Stores movement command

    保存一次控制周期内的运动与模式切换指令。
    """

    def __init__(self):
        # 机身平面速度指令，格式为 [vx, vy]
        self.horizontal_velocity = np.array([0, 0])
        # 偏航角速度指令
        self.yaw_rate = 0.0
        # 机身目标高度
        self.height = -0.16
        # 机身目标俯仰角
        self.pitch = 0.0
        # 机身目标横滚角
        self.roll = 0.0
        # 激活状态标记
        self.activation = 0
        
        # 单次跳跃触发事件
        self.hop_event = False
        # 步态切换触发事件
        self.trot_event = False
        # 控制器激活/失活切换事件
        self.activate_event = False
