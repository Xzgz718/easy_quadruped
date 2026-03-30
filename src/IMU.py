"""IMU 串口读取接口。"""

import serial
import numpy as np
import time


class IMU:
    """负责从串口读取四元数姿态数据。"""

    def __init__(self, port, baudrate=500000):
        # 打开 Teensy/IMU 对应的串口
        self.serial_handle = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0,
        )
        # 保存最近一次有效姿态，避免串口暂时无数据时返回空值
        self.last_quat = np.array([1, 0, 0, 0])
        self.start_time = time.time()

    def flush_buffer(self):
        """清空串口输入缓冲区。"""
        self.serial_handle.reset_input_buffer()

    def read_orientation(self):
        """Reads quaternion measurements from the Teensy until none are left. Returns the last read quaternion.

        Parameters
        ----------
        serial_handle : Serial object
            Handle to the pyserial Serial object

        Returns
        -------
        np array (4,)
            If there was quaternion data to read on the serial port returns the quaternion as a numpy array, otherwise returns the last read quaternion.

        持续读取串口中的四元数数据，并返回最近一次有效值。
        """

        while True:
            x = self.serial_handle.readline().decode("utf").strip()
            if x is "" or x is None:
                return self.last_quat
            else:
                parsed = x.split(",")
                if len(parsed) == 4:
                    # 串口数据格式约定为逗号分隔的四元数 [w, x, y, z]
                    self.last_quat = np.array(parsed, dtype=np.float64)
                else:
                    print("Did not receive 4-vector from imu")
