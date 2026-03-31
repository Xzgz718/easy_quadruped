from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING

import mujoco
import numpy as np
from transforms3d.quaternions import quat2mat

from sim.model_constants import FOOT_SITE_NAMES, JOINT_NAMES, LEG_SPECS
from sim.task_scheduler import TaskScheduler
from src.Command import Command
from src.State import BehaviorState, State

if TYPE_CHECKING:
    from argparse import Namespace

    from pupper.Config import Configuration


FOOT_POS_SENSOR_NAMES = tuple(f"{prefix}_foot_pos" for prefix, _, _ in LEG_SPECS)
FOOT_TOUCH_SENSOR_NAMES = tuple(f"{prefix}_touch" for prefix, _, _ in LEG_SPECS)
JOINT_POS_SENSOR_NAMES = tuple(f"{joint_name}_pos" for joint_name in JOINT_NAMES)
JOINT_VEL_SENSOR_NAMES = tuple(f"{joint_name}_vel" for joint_name in JOINT_NAMES)


def joint_name_targets(joint_angles: np.ndarray) -> dict[str, float]:
    targets: dict[str, float] = {}
    for prefix, leg_index, _ in LEG_SPECS:
        targets[f"{prefix}_abad"] = float(joint_angles[0, leg_index])
        targets[f"{prefix}_hip"] = float(joint_angles[1, leg_index])
        targets[f"{prefix}_knee"] = float(joint_angles[2, leg_index] - joint_angles[1, leg_index])
    return targets


def joint_target_array(joint_angles: np.ndarray) -> np.ndarray:
    targets = joint_name_targets(joint_angles)
    return np.array([targets[name] for name in JOINT_NAMES], dtype=float)


class SimObservationInterface:
    """MuJoCo sensor bridge that populates `State` like a robot-side observer."""

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData):
        self.model = model
        self.data = data
        self._sensor_slices = {
            sensor_name: self._sensor_slice(sensor_name)
            for sensor_name in (
                "torso_pos",
                "imu_quat",
                "imu_gyro",
                "imu_acc",
                "imu_vel",
                *FOOT_POS_SENSOR_NAMES,
                *FOOT_TOUCH_SENSOR_NAMES,
                *JOINT_POS_SENSOR_NAMES,
                *JOINT_VEL_SENSOR_NAMES,
            )
        }

    def _sensor_slice(self, sensor_name: str) -> slice:
        sensor_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SENSOR, sensor_name)
        sensor_adr = self.model.sensor_adr[sensor_id]
        sensor_dim = self.model.sensor_dim[sensor_id]
        return slice(sensor_adr, sensor_adr + sensor_dim)

    def read_sensor(self, sensor_name: str) -> np.ndarray:
        return np.array(self.data.sensordata[self._sensor_slices[sensor_name]], copy=True)

    def torso_pose(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        torso_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "torso")
        position = self.data.xpos[torso_id].copy()
        rotation = self.data.xmat[torso_id].reshape(3, 3).copy()
        quat = self.data.xquat[torso_id].copy()
        return position, rotation, quat

    def body_frame_feet(self) -> np.ndarray:
        torso_position, torso_rotation, _ = self.torso_pose()
        feet = np.zeros((3, 4))
        for site_index, site_name in enumerate(FOOT_SITE_NAMES):
            site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, site_name)
            offset_world = self.data.site_xpos[site_id] - torso_position
            feet[:, site_index] = torso_rotation.T @ offset_world
        return feet

    def measured_body_frame_feet(self, torso_position: np.ndarray, torso_quat: np.ndarray) -> np.ndarray:
        torso_rotation = quat2mat(torso_quat)
        feet = np.zeros((3, 4))
        for site_index, sensor_name in enumerate(FOOT_POS_SENSOR_NAMES):
            foot_world = self.read_sensor(sensor_name)
            feet[:, site_index] = torso_rotation.T @ (foot_world - torso_position)
        return feet

    def measured_joint_angles(self) -> np.ndarray:
        joint_values = np.array([self.read_sensor(sensor_name)[0] for sensor_name in JOINT_POS_SENSOR_NAMES], dtype=float)
        joint_values = joint_values.reshape(4, 3).T
        joint_values[2, :] += joint_values[1, :]
        return joint_values

    def measured_joint_velocities(self) -> np.ndarray:
        joint_values = np.array([self.read_sensor(sensor_name)[0] for sensor_name in JOINT_VEL_SENSOR_NAMES], dtype=float)
        joint_values = joint_values.reshape(4, 3).T
        joint_values[2, :] += joint_values[1, :]
        return joint_values

    def contact_forces(self) -> np.ndarray:
        return np.array([self.read_sensor(sensor_name)[0] for sensor_name in FOOT_TOUCH_SENSOR_NAMES], dtype=float)

    def sync_state(
        self,
        state: State,
        stance_state_blend: float,
        swing_state_blend: float,
        contact_threshold: float,
    ) -> None:
        torso_position = self.read_sensor("torso_pos")
        torso_quat = self.read_sensor("imu_quat")
        measured_feet = self.measured_body_frame_feet(torso_position, torso_quat)
        state.measured_foot_locations = measured_feet
        state.measured_joint_angles = self.measured_joint_angles()
        state.measured_joint_velocities = self.measured_joint_velocities()
        state.joint_angles = state.measured_joint_angles.copy()
        state.joint_velocities = state.measured_joint_velocities.copy()
        state.body_position = torso_position
        state.body_velocity = self.read_sensor("imu_vel")
        state.angular_velocity = self.read_sensor("imu_gyro")
        state.foot_forces = self.contact_forces()
        state.contact_estimate = state.foot_forces > contact_threshold

        for leg_index in range(4):
            blend = stance_state_blend if state.contact_estimate[leg_index] else swing_state_blend
            state.foot_locations[:, leg_index] = (
                (1.0 - blend) * state.foot_locations[:, leg_index]
                + blend * measured_feet[:, leg_index]
            )

    def telemetry_line(self) -> str:
        torso_position = self.read_sensor("torso_pos")
        torso_quat = self.read_sensor("imu_quat")
        body_velocity = self.read_sensor("imu_vel")
        touches = self.contact_forces()
        contacts = "".join("1" if touch > 1e-3 else "0" for touch in touches)
        from transforms3d.euler import mat2euler

        roll, pitch, yaw = mat2euler(quat2mat(torso_quat))
        return (
            f"xyz={np.round(torso_position, 3)} "
            f"vxyz={np.round(body_velocity, 3)} "
            f"rpy={np.round([roll, pitch, yaw], 3)} "
            f"touch={contacts}"
        )

    def pose_error(self, state: State) -> float:
        return float(np.max(np.abs(self.body_frame_feet() - state.foot_locations)))


class SimIMU:
    """MuJoCo-backed IMU adapter with the same public shape as the robot IMU."""

    def __init__(self, observation_interface: SimObservationInterface):
        self.observation_interface = observation_interface

    def flush_buffer(self) -> None:
        return None

    def read_orientation(self) -> np.ndarray:
        return self.observation_interface.read_sensor("imu_quat")


class SimHardwareInterface:
    """Servo-like actuator adapter that tracks joint targets through MuJoCo motors."""

    def __init__(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        kp: float,
        kd: float,
        torque_limit: float,
    ):
        self.model = model
        self.data = data
        self.kp = kp
        self.kd = kd
        self.torque_limit = torque_limit
        self.target_qpos = np.zeros(len(JOINT_NAMES))

    def set_initial_pose(self, joint_angles: np.ndarray, base_z: float) -> None:
        self.target_qpos = joint_target_array(joint_angles)
        self.data.qpos[:3] = np.array([0.0, 0.0, base_z])
        self.data.qpos[3:7] = np.array([1.0, 0.0, 0.0, 0.0])
        for index, joint_name in enumerate(JOINT_NAMES):
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            self.data.qpos[self.model.jnt_qposadr[joint_id]] = self.target_qpos[index]
        self.data.qvel[:] = 0.0
        self.data.ctrl[:] = 0.0
        mujoco.mj_forward(self.model, self.data)

    def set_actuator_postions(self, joint_angles: np.ndarray) -> None:
        self.target_qpos = joint_target_array(joint_angles)

    def set_actuator_position(self, joint_angle: float, axis: int, leg: int) -> None:
        joint_name = JOINT_NAMES[leg * 3 + axis]
        targets = dict(zip(JOINT_NAMES, self.target_qpos.tolist()))
        if axis == 2:
            hip_joint_name = JOINT_NAMES[leg * 3 + 1]
            targets[joint_name] = float(joint_angle - targets[hip_joint_name])
        else:
            targets[joint_name] = float(joint_angle)
        self.target_qpos = np.array([targets[name] for name in JOINT_NAMES], dtype=float)

    def _compute_pd_torques(self) -> np.ndarray:
        torques = np.zeros(len(JOINT_NAMES))
        for index, joint_name in enumerate(JOINT_NAMES):
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            qpos_addr = self.model.jnt_qposadr[joint_id]
            qvel_addr = self.model.jnt_dofadr[joint_id]
            position_error = self.target_qpos[index] - self.data.qpos[qpos_addr]
            velocity_error = -self.data.qvel[qvel_addr]
            torques[index] = np.clip(
                self.kp * position_error + self.kd * velocity_error,
                -self.torque_limit,
                self.torque_limit,
            )
        return torques

    def step(self, substeps: int) -> None:
        for _ in range(substeps):
            self.data.ctrl[:] = self._compute_pd_torques()
            mujoco.mj_step(self.model, self.data)


class SimControlClock:
    """Control-rate clock that advances MuJoCo substeps like a robot-side loop."""

    def __init__(self, sim_dt: float, control_dt: float, viewer=None):
        self.sim_dt = sim_dt
        self.control_dt = control_dt
        self.control_interval = max(1, int(round(control_dt / sim_dt)))
        self.viewer = viewer
        self.next_wall_time = time.perf_counter()

    def total_ticks(self, duration: float) -> int:
        return max(1, int(duration / self.control_dt))

    def viewer_lock(self):
        return self.viewer.lock() if self.viewer is not None else contextlib.nullcontext()

    def finish_tick(self) -> None:
        if self.viewer is None:
            return
        self.viewer.sync()
        self.next_wall_time += self.control_dt
        sleep_time = self.next_wall_time - time.perf_counter()
        if sleep_time > 0:
            time.sleep(sleep_time)


class TaskCommandSource:
    """Task-level source that emits run_robot-like toggle events and continuous commands."""

    def __init__(self, args: "Namespace"):
        self.args = args
        self.scheduler = TaskScheduler.from_args(args)
        self._printed_waiting = False
        self._printed_activation = False
        self._current_step_index: int | None = None

    def set_color(self, color) -> None:
        return None

    def target_mode(self, sim_time: float) -> str:
        return self.scheduler.mode_at(sim_time)

    def _base_gait_params(self) -> dict[str, float]:
        return {
            "z_clearance": self.args.z_clearance,
            "overlap_time": self.args.overlap_time,
            "swing_time": self.args.swing_time,
        }

    def base_feedback_params(self) -> dict[str, float]:
        return {
            "attitude_kp": self.args.attitude_kp,
            "attitude_kd": self.args.attitude_kd,
            "velocity_kp": self.args.velocity_kp,
        }

    @staticmethod
    def _blend_dict(
        previous_values: dict[str, float],
        current_values: dict[str, float],
        alpha: float,
    ) -> dict[str, float]:
        keys = set(previous_values) | set(current_values)
        return {
            key: (1.0 - alpha) * previous_values[key] + alpha * current_values[key]
            for key in keys
        }

    @staticmethod
    def _step_values(base_values: dict[str, float], step: object | None, allowed_keys: set[str]) -> dict[str, float]:
        values = dict(base_values)
        if step is None:
            return values
        params = getattr(step, "params", {}) or {}
        values.update({key: value for key, value in params.items() if key in allowed_keys})
        return values

    def _blended_step_values(self, sim_time: float, base_values: dict[str, float]) -> tuple[dict[str, float], str]:
        step_index, previous_step, step, alpha = self.scheduler.transition_info_at(sim_time)
        del step_index
        allowed_keys = set(base_values)
        previous_values = self._step_values(base_values, previous_step, allowed_keys)
        current_values = self._step_values(base_values, step, allowed_keys)
        blended_values = self._blend_dict(previous_values, current_values, alpha)
        return blended_values, step.mode

    def apply_step_config(self, config, state: State, sim_time: float) -> tuple[bool, str] | None:
        if self.scheduler.is_waiting(sim_time):
            return None

        step_index, previous_step, step, _ = self.scheduler.transition_info_at(sim_time)
        gait_params, _ = self._blended_step_values(sim_time, self._base_gait_params())

        config.z_clearance = gait_params["z_clearance"]
        config.overlap_time = gait_params["overlap_time"]
        config.swing_time = gait_params["swing_time"]

        changed = step_index != self._current_step_index
        if changed:
            if previous_step is None or previous_step.mode != step.mode:
                state.ticks = 0
            self._current_step_index = step_index
        return changed, self.scheduler.render_step(step)

    def feedback_params(self, sim_time: float) -> dict[str, float]:
        params, _ = self._blended_step_values(sim_time, self.base_feedback_params())
        return params

    def _base_command(self) -> Command:
        command = Command()
        command.height = self.args.height
        command.pitch = self.args.pitch
        command.roll = self.args.roll
        command.horizontal_velocity = np.array([self.args.x_vel, self.args.y_vel], dtype=float)
        command.yaw_rate = self.args.yaw_rate
        return command

    def _apply_step_params(self, command: Command, sim_time: float) -> str:
        base_command_values = {
            "vx": float(command.horizontal_velocity[0]),
            "vy": float(command.horizontal_velocity[1]),
            "yaw_rate": float(command.yaw_rate),
            "height": float(command.height),
            "pitch": float(command.pitch),
            "roll": float(command.roll),
        }
        params, mode = self._blended_step_values(sim_time, base_command_values)
        command.horizontal_velocity[0] = params["vx"]
        command.horizontal_velocity[1] = params["vy"]
        command.yaw_rate = params["yaw_rate"]
        command.height = params["height"]
        command.pitch = params["pitch"]
        command.roll = params["roll"]
        return mode

    def get_command(self, state: State, sim_time: float) -> Command | None:
        if state.behavior_state == BehaviorState.DEACTIVATED and self.scheduler.is_waiting(sim_time):
            if not self._printed_waiting:
                print("Waiting for task-layer activation.")
                self._printed_waiting = True
            return None

        command = self._base_command()
        mode = self._apply_step_params(command, sim_time)

        if state.behavior_state == BehaviorState.DEACTIVATED:
            if not self._printed_activation:
                print("Task layer activated.")
                self._printed_activation = True
            command.activate_event = True
            command.horizontal_velocity[:] = 0.0
            command.yaw_rate = 0.0
            return command

        if mode == "rest":
            command.horizontal_velocity[:] = 0.0
            command.yaw_rate = 0.0

        if mode == "trot" and state.behavior_state != BehaviorState.TROT:
            command.trot_event = True
        elif mode == "rest" and state.behavior_state == BehaviorState.TROT:
            command.trot_event = True
        return command


def create_command_source(args: "Namespace", config: "Configuration"):
    del config
    return TaskCommandSource(args)
