"""Leg inverse kinematics utilities.

腿部逆运动学工具函数。
"""

import numpy as np
from transforms3d.euler import euler2mat


def leg_explicit_inverse_kinematics(r_body_foot, leg_index, config):
    """Find the joint angles corresponding to the given body-relative foot position for a given leg and configuration
    
    Parameters
    ----------
    r_body_foot : [type]
        [description]
    leg_index : [type]
        [description]
    config : [type]
        [description]
    
    Returns
    -------
    numpy array (3)
        Array of corresponding joint angles.

    根据给定腿编号和足端相对机身的位置，求解对应的三个关节角。
    """
    (x, y, z) = r_body_foot

    # Distance from the leg origin to the foot, projected into the y-z plane
    # 腿原点到足端的距离，投影到 y-z 平面后得到的长度
    R_body_foot_yz = (y ** 2 + z ** 2) ** 0.5

    # Distance from the leg's forward/back point of rotation to the foot
    # 从髋关节前后转轴到足端的 y-z 平面距离
    R_hip_foot_yz = (R_body_foot_yz ** 2 - config.ABDUCTION_OFFSET ** 2) ** 0.5

    # Interior angle of the right triangle formed in the y-z plane by the leg that is coincident to the ab/adduction axis
    # For feet 2 (front left) and 4 (back left), the abduction offset is positive, for the right feet, the abduction offset is negative.
    # 腿与外展/内收轴在 y-z 平面构成的直角三角形内角
    # 左侧腿外展偏移为正，右侧腿外展偏移为负
    arccos_argument = config.ABDUCTION_OFFSETS[leg_index] / R_body_foot_yz
    arccos_argument = np.clip(arccos_argument, -0.99, 0.99)
    phi = np.arccos(arccos_argument)

    # Angle of the y-z projection of the hip-to-foot vector, relative to the positive y-axis
    # 髋到足端向量在 y-z 平面投影相对正 y 轴的夹角
    hip_foot_angle = np.arctan2(z, y)

    # Ab/adduction angle, relative to the positive y-axis
    # 外展/内收关节角，相对正 y 轴定义
    abduction_angle = phi + hip_foot_angle

    # theta: Angle between the tilted negative z-axis and the hip-to-foot vector
    # theta：倾斜后的负 z 轴与髋到足端向量之间的夹角
    theta = np.arctan2(-x, R_hip_foot_yz)

    # Distance between the hip and foot
    # 髋关节到足端的空间距离
    R_hip_foot = (R_hip_foot_yz ** 2 + x ** 2) ** 0.5

    # Angle between the line going from hip to foot and the link L1
    # 髋到足端连线与第一段连杆 L1 之间的夹角
    arccos_argument = (config.LEG_L1 ** 2 + R_hip_foot ** 2 - config.LEG_L2 ** 2) / (
        2 * config.LEG_L1 * R_hip_foot
    )
    arccos_argument = np.clip(arccos_argument, -0.99, 0.99)
    trident = np.arccos(arccos_argument)

    # Angle of the first link relative to the tilted negative z axis
    # 第一段连杆相对倾斜负 z 轴的夹角
    hip_angle = theta + trident

    # Angle between the leg links L1 and L2
    # 连杆 L1 与 L2 之间的夹角
    arccos_argument = (config.LEG_L1 ** 2 + config.LEG_L2 ** 2 - R_hip_foot ** 2) / (
        2 * config.LEG_L1 * config.LEG_L2
    )
    arccos_argument = np.clip(arccos_argument, -0.99, 0.99)
    beta = np.arccos(arccos_argument)

    # Angle of the second link relative to the tilted negative z axis
    # 第二段连杆相对倾斜负 z 轴的夹角
    knee_angle = hip_angle - (np.pi - beta)

    return np.array([abduction_angle, hip_angle, knee_angle])


def four_legs_inverse_kinematics(r_body_foot, config):
    """Find the joint angles for all twelve DOF correspoinding to the given matrix of body-relative foot positions.
    
    Parameters
    ----------
    r_body_foot : numpy array (3,4)
        Matrix of the body-frame foot positions. Each column corresponds to a separate foot.
    config : Config object
        Object of robot configuration parameters.
    
    Returns
    -------
    numpy array (3,4)
        Matrix of corresponding joint angles.

    对四条腿分别求逆运动学，返回 3×4 的关节角矩阵。
    """
    alpha = np.zeros((3, 4))
    for i in range(4):
        # 先扣除每条腿在机身坐标系下的安装原点偏移，再求单腿逆解
        body_offset = config.LEG_ORIGINS[:, i]
        alpha[:, i] = leg_explicit_inverse_kinematics(
            r_body_foot[:, i] - body_offset, i, config
        )
    return alpha
