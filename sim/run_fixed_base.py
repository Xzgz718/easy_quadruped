from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import mujoco
from mujoco import viewer as mujoco_viewer
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pupper.Config import Configuration
from pupper.Kinematics import four_legs_inverse_kinematics
from src.Command import Command
from src.Controller import Controller
from src.State import State
from sim.build_fixed_base_mjcf import FOOT_SITE_NAMES, LEG_SPECS, build_mjcf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fixed-base MuJoCo visualizer for StanfordQuadruped.")
    parser.add_argument("--mode", choices=("rest", "trot"), default="trot")
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--x-vel", type=float, default=0.20)
    parser.add_argument("--y-vel", type=float, default=0.0)
    parser.add_argument("--yaw-rate", type=float, default=0.0)
    parser.add_argument("--height", type=float, default=-0.16)
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--roll", type=float, default=0.0)
    return parser.parse_args()


def joint_name_targets(joint_angles: np.ndarray) -> dict[str, float]:
    targets: dict[str, float] = {}
    for prefix, leg_index, _ in LEG_SPECS:
        targets[f"{prefix}_abad"] = float(joint_angles[0, leg_index])
        targets[f"{prefix}_hip"] = float(joint_angles[1, leg_index])
        targets[f"{prefix}_knee"] = float(joint_angles[2, leg_index] - joint_angles[1, leg_index])
    return targets


def apply_joint_targets(model: mujoco.MjModel, data: mujoco.MjData, joint_angles: np.ndarray) -> None:
    for joint_name, target in joint_name_targets(joint_angles).items():
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        qpos_address = model.jnt_qposadr[joint_id]
        data.qpos[qpos_address] = target
    mujoco.mj_forward(model, data)


def body_frame_feet(model: mujoco.MjModel, data: mujoco.MjData) -> np.ndarray:
    torso_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso")
    torso_position = data.xpos[torso_id].copy()
    feet = np.zeros((3, 4))
    for site_index, site_name in enumerate(FOOT_SITE_NAMES):
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
        feet[:, site_index] = data.site_xpos[site_id] - torso_position
    return feet


def pose_error(model: mujoco.MjModel, data: mujoco.MjData, state: State) -> float:
    return float(np.max(np.abs(body_frame_feet(model, data) - state.foot_locations)))


def make_command(args: argparse.Namespace, first_trot_step: bool) -> Command:
    command = Command()
    command.height = args.height
    command.pitch = args.pitch
    command.roll = args.roll
    command.horizontal_velocity = np.array([args.x_vel, args.y_vel], dtype=float)
    command.yaw_rate = args.yaw_rate
    if first_trot_step:
        command.trot_event = True
    if args.mode == "rest":
        command.horizontal_velocity[:] = 0.0
        command.yaw_rate = 0.0
    return command


def initialize_controller(args: argparse.Namespace) -> tuple[Configuration, Controller, State]:
    config = Configuration()
    controller = Controller(config, four_legs_inverse_kinematics)
    state = State()
    state.quat_orientation = np.array([1.0, 0.0, 0.0, 0.0])

    initial_command = Command()
    initial_command.height = args.height
    initial_command.pitch = args.pitch
    initial_command.roll = args.roll
    controller.run(state, initial_command)
    return config, controller, state


def step_controller(controller: Controller, state: State, command: Command) -> None:
    state.quat_orientation = np.array([1.0, 0.0, 0.0, 0.0])
    controller.run(state, command)


def run_loop(args: argparse.Namespace, model: mujoco.MjModel, data: mujoco.MjData, viewer=None) -> None:
    config, controller, state = initialize_controller(args)
    apply_joint_targets(model, data, state.joint_angles)
    print(f"rest pose max foot error: {pose_error(model, data, state):.4f} m")

    total_steps = max(1, int(args.duration / config.dt))
    next_wall_time = time.perf_counter()

    for step_index in range(total_steps):
        command = make_command(args, first_trot_step=args.mode == "trot" and step_index == 0)
        step_controller(controller, state, command)
        apply_joint_targets(model, data, state.joint_angles)

        if viewer is not None:
            viewer.sync()
            next_wall_time += config.dt
            sleep_time = next_wall_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)

    print(f"final max foot error: {pose_error(model, data, state):.4f} m")


def main() -> None:
    args = parse_args()
    xml_path = Path(__file__).with_name("pupper_fixed.xml")
    builder_path = Path(__file__).with_name("build_fixed_base_mjcf.py")
    if args.rebuild or not xml_path.exists() or xml_path.stat().st_mtime < builder_path.stat().st_mtime:
        build_mjcf(xml_path)

    model = mujoco.MjModel.from_xml_path(str(xml_path))
    data = mujoco.MjData(model)

    if args.headless:
        run_loop(args, model, data)
        return

    with mujoco_viewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False) as viewer:
        run_loop(args, model, data, viewer=viewer)


if __name__ == "__main__":
    main()
