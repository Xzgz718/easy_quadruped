"""步态时序相关逻辑。"""

class GaitController:
    """根据 tick 计算当前步态相位和接触模式。"""

    def __init__(self, config):
        self.config = config


    def phase_index(self, ticks):
        """Calculates which part of the gait cycle the robot should be in given the time in ticks.

        Parameters
        ----------
        ticks : int
            Number of timesteps since the program started
        gaitparams : GaitParams
            GaitParams object

        Returns
        -------
        Int
            The index of the gait phase that the robot should be in.

        根据 tick 计算机器人当前处于步态周期中的哪一相。
        """
        phase_time = ticks % self.config.phase_length
        phase_sum = 0
        for i in range(self.config.num_phases):
            phase_sum += self.config.phase_ticks[i]
            if phase_time < phase_sum:
                return i
        assert False


    def subphase_ticks(self, ticks):
        """Calculates the number of ticks (timesteps) since the start of the current phase.

        Parameters
        ----------
        ticks : Int
            Number of timesteps since the program started
        gaitparams : GaitParams
            GaitParams object

        Returns
        -------
        Int
            Number of ticks since the start of the current phase.

        计算当前步态子相已经持续了多少个 tick。
        """
        phase_time = ticks % self.config.phase_length
        phase_sum = 0
        subphase_ticks = 0
        for i in range(self.config.num_phases):
            phase_sum += self.config.phase_ticks[i]
            if phase_time < phase_sum:
                subphase_ticks = phase_time - phase_sum + self.config.phase_ticks[i]
                return subphase_ticks
        assert False


    def contacts(self, ticks):
        """Calculates which feet should be in contact at the given number of ticks

        Parameters
        ----------
        ticks : Int
            Number of timesteps since the program started.
        gaitparams : GaitParams
            GaitParams object

        Returns
        -------
        numpy array (4,)
            Numpy vector with 0 indicating flight and 1 indicating stance.

        返回四条腿的接触状态，0 表示摆动相，1 表示支撑相。
        """
        return self.config.contact_phases[:, self.phase_index(ticks)]
