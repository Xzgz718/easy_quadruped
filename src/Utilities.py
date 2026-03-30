"""常用数值处理工具函数。"""

import numpy as np


def deadband(value, band_radius):
    """对输入施加死区，过滤掉接近零的小幅抖动。"""
    return max(value - band_radius, 0) + min(value + band_radius, 0)


def clipped_first_order_filter(input, target, max_rate, tau):
    """计算一阶滤波后的变化率，并限制最大变化速度。"""
    rate = (target - input) / tau
    return np.clip(rate, -max_rate, max_rate)
