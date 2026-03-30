"""支撑相足端位置更新逻辑。"""

import numpy as np
from transforms3d.euler import euler2mat

class StanceController:
    """在支撑相内推进足端位置。"""

    def __init__(self, config):
        self.config = config


    def position_delta(self, leg_index, state, command):
        """Calculate the difference between the next desired body location and the current body location

        Parameters
        ----------
        z_measured : float
            Z coordinate of the feet relative to the body.
        stance_params : StanceParams
            Stance parameters object.
        movement_reference : MovementReference
            Movement reference object.
        gait_params : GaitParams
            Gait parameters object.

        Returns
        -------
        (Numpy array (3), Numpy array (3, 3))
            (Position increment, rotation matrix increment)

        计算当前控制周期内足端的平移增量和旋转增量。
        """
        z = state.foot_locations[2, leg_index]
        # 水平速度取负号，相当于在机身前进时让足端相对机身向后“划地”
        v_xy = np.array(
            [
                -command.horizontal_velocity[0],
                -command.horizontal_velocity[1],
                1.0
                / self.config.z_time_constant
                * (state.height - z),
            ]
        )
        # 由线速度和偏航角速度得到足端在机身坐标系中的增量
        delta_p = v_xy * self.config.dt
        delta_R = euler2mat(0, 0, -command.yaw_rate * self.config.dt)
        return (delta_p, delta_R)

    # TODO: put current foot location into state
    # TODO: 将当前足端位置显式作为状态量维护
    def next_foot_location(self, leg_index, state, command):
        """根据支撑相运动学更新单条腿的足端位置。"""
        foot_location = state.foot_locations[:, leg_index]
        (delta_p, delta_R) = self.position_delta(leg_index, state, command)
        incremented_location = delta_R @ foot_location + delta_p

        return incremented_location
