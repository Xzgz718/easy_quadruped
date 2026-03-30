"""手柄输入解析与命令生成逻辑。"""

import UDPComms
import numpy as np
import time
from src.State import BehaviorState, State
from src.Command import Command
from src.Utilities import deadband, clipped_first_order_filter


class JoystickInterface:
    """将 UDP 手柄消息转换为控制器可用的 `Command`。"""

    def __init__(
        self, config, udp_port=8830, udp_publisher_port = 8840, timeout=0.3,
    ):
        self.config = config
        # 保存上一帧按键状态，用于检测“边沿触发”事件
        self.previous_gait_toggle = 0
        self.previous_state = BehaviorState.REST
        self.previous_hop_toggle = 0
        self.previous_activate_toggle = 0

        self.message_rate = 50
        # 订阅手柄消息，并向手柄回发灯光颜色
        self.udp_handle = UDPComms.Subscriber(udp_port, timeout=timeout)
        self.udp_publisher = UDPComms.Publisher(udp_publisher_port)


    def get_command(self, state, do_print=False):
        """读取一帧手柄输入并转换为控制命令。"""
        try:
            msg = self.udp_handle.get()
            command = Command()
            
            ####### Handle discrete commands ########
            # 处理离散事件：步态切换、跳跃、激活/失活
            # Check if requesting a state transition to trotting, or from trotting to resting
            gait_toggle = msg["R1"]
            command.trot_event = (gait_toggle == 1 and self.previous_gait_toggle == 0)

            # Check if requesting a state transition to hopping, from trotting or resting
            hop_toggle = msg["x"]
            command.hop_event = (hop_toggle == 1 and self.previous_hop_toggle == 0)            
            
            activate_toggle = msg["L1"]
            command.activate_event = (activate_toggle == 1 and self.previous_activate_toggle == 0)

            # Update previous values for toggles and state
            # 更新上一帧按键状态
            self.previous_gait_toggle = gait_toggle
            self.previous_hop_toggle = hop_toggle
            self.previous_activate_toggle = activate_toggle

            ####### Handle continuous commands ########
            # 处理连续量：平移速度、偏航、俯仰、高度、横滚
            x_vel = msg["ly"] * self.config.max_x_velocity
            y_vel = msg["lx"] * -self.config.max_y_velocity
            command.horizontal_velocity = np.array([x_vel, y_vel])
            command.yaw_rate = msg["rx"] * -self.config.max_yaw_rate

            message_rate = msg["message_rate"]
            message_dt = 1.0 / message_rate

            pitch = msg["ry"] * self.config.max_pitch
            deadbanded_pitch = deadband(
                pitch, self.config.pitch_deadband
            )
            # 俯仰命令先经过死区和一阶限速滤波，避免突变
            pitch_rate = clipped_first_order_filter(
                state.pitch,
                deadbanded_pitch,
                self.config.max_pitch_rate,
                self.config.pitch_time_constant,
            )
            command.pitch = state.pitch + message_dt * pitch_rate

            height_movement = msg["dpady"]
            command.height = state.height - message_dt * self.config.z_speed * height_movement
            
            roll_movement = - msg["dpadx"]
            command.roll = state.roll + message_dt * self.config.roll_speed * roll_movement

            return command

        except UDPComms.timeout:
            if do_print:
                print("UDP Timed out")
            # 超时则返回零指令，保证控制器安全退回默认输入
            return Command()


    def set_color(self, color):
        """设置手柄灯光颜色。"""
        joystick_msg = {"ps4_color": color}
        self.udp_publisher.send(joystick_msg)
