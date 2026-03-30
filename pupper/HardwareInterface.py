"""Hardware GPIO and servo output interface.

硬件 GPIO 与舵机输出接口。
"""

import pigpio
from pupper.Config import ServoParams, PWMParams


class HardwareInterface:
    """Thin wrapper around pigpio for servo control.

    基于 `pigpio` 的舵机控制封装。
    """

    def __init__(self):
        # 建立与本机 pigpio 守护进程的连接
        self.pi = pigpio.pi()
        self.pwm_params = PWMParams()
        self.servo_params = ServoParams()
        # 初始化所有舵机对应引脚的 PWM 参数
        initialize_pwm(self.pi, self.pwm_params)

    def set_actuator_postions(self, joint_angles):
        """设置全部 12 个关节的目标角度。"""
        send_servo_commands(self.pi, self.pwm_params, self.servo_params, joint_angles)
    
    def set_actuator_position(self, joint_angle, axis, leg):
        """设置单个关节的目标角度。"""
        send_servo_command(self.pi, self.pwm_params, self.servo_params, joint_angle, axis, leg)


def pwm_to_duty_cycle(pulsewidth_micros, pwm_params):
    """Converts a pwm signal (measured in microseconds) to a corresponding duty cycle on the gpio pwm pin

    Parameters
    ----------
    pulsewidth_micros : float
        Width of the pwm signal in microseconds
    pwm_params : PWMParams
        PWMParams object

    Returns
    -------
    float
        PWM duty cycle corresponding to the pulse width

    将以微秒表示的 PWM 脉宽转换为 GPIO 输出所需的 duty cycle。
    """
    return int(pulsewidth_micros / 1e6 * pwm_params.freq * pwm_params.range)


def angle_to_pwm(angle, servo_params, axis_index, leg_index):
    """Converts a desired servo angle into the corresponding PWM command

    Parameters
    ----------
    angle : float
        Desired servo angle, relative to the vertical (z) axis
    servo_params : ServoParams
        ServoParams object
    axis_index : int
        Specifies which joint of leg to control. 0 is abduction servo, 1 is inner hip servo, 2 is outer hip servo.
    leg_index : int
        Specifies which leg to control. 0 is front-right, 1 is front-left, 2 is back-right, 3 is back-left.

    Returns
    -------
    float
        PWM width in microseconds

    将期望关节角转换为对应的 PWM 脉宽（微秒）。
    """
    angle_deviation = (
        angle - servo_params.neutral_angles[axis_index, leg_index]
    ) * servo_params.servo_multipliers[axis_index, leg_index]
    pulse_width_micros = (
        servo_params.neutral_position_pwm
        + servo_params.micros_per_rad * angle_deviation
    )
    return pulse_width_micros


def angle_to_duty_cycle(angle, pwm_params, servo_params, axis_index, leg_index):
    """将关节角直接转换为 PWM duty cycle。"""
    return pwm_to_duty_cycle(
        angle_to_pwm(angle, servo_params, axis_index, leg_index), pwm_params
    )


def initialize_pwm(pi, pwm_params):
    """初始化所有关节引脚的 PWM 频率和范围。"""
    for leg_index in range(4):
        for axis_index in range(3):
            pi.set_PWM_frequency(
                pwm_params.pins[axis_index, leg_index], pwm_params.freq
            )
            pi.set_PWM_range(pwm_params.pins[axis_index, leg_index], pwm_params.range)


def send_servo_commands(pi, pwm_params, servo_params, joint_angles):
    """批量向四条腿的所有关节发送舵机命令。"""
    for leg_index in range(4):
        for axis_index in range(3):
            duty_cycle = angle_to_duty_cycle(
                joint_angles[axis_index, leg_index],
                pwm_params,
                servo_params,
                axis_index,
                leg_index,
            )
            pi.set_PWM_dutycycle(pwm_params.pins[axis_index, leg_index], duty_cycle)


def send_servo_command(pi, pwm_params, servo_params, joint_angle, axis, leg):
    """向单个关节发送舵机命令。"""
    duty_cycle = angle_to_duty_cycle(joint_angle, pwm_params, servo_params, axis, leg)
    pi.set_PWM_dutycycle(pwm_params.pins[axis, leg], duty_cycle)


def deactivate_servos(pi, pwm_params):
    """关闭所有舵机输出。"""
    for leg_index in range(4):
        for axis_index in range(3):
            pi.set_PWM_dutycycle(pwm_params.pins[axis_index, leg_index], 0)
