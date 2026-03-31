from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import mujoco
from mujoco import viewer as mujoco_viewer
import numpy as np
from transforms3d.euler import mat2euler
from transforms3d.quaternions import quat2mat

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pupper.Config import Configuration
from pupper.Kinematics import four_legs_inverse_kinematics
from src.Command import Command
from src.Controller import Controller
from src.State import BehaviorState, State
from sim.build_floating_base_mjcf import build_mjcf
from sim.sim_robot import (
    SimControlClock,
    SimHardwareInterface,
    SimIMU,
    SimObservationInterface,
    create_command_source,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Floating-base MuJoCo visualizer for easy_quadruped.")
    parser.add_argument("--mode", choices=("rest", "trot"), default="trot")
    parser.add_argument("--task-sequence", type=str, default=None)
    parser.add_argument("--transition-time", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--x-vel", type=float, default=0.06)
    parser.add_argument("--y-vel", type=float, default=0.0)
    parser.add_argument("--yaw-rate", type=float, default=0.0)
    parser.add_argument("--height", type=float, default=-0.16)
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--roll", type=float, default=0.0)
    parser.add_argument("--kp", type=float, default=24.0)
    parser.add_argument("--kd", type=float, default=2.2)
    parser.add_argument("--torque-limit", type=float, default=3.0)
    parser.add_argument("--activation-delay", type=float, default=0.0)
    parser.add_argument("--settle", type=float, default=1.0)
    parser.add_argument("--base-z", type=float, default=None)
    parser.add_argument("--telemetry-interval", type=float, default=1.0)
    parser.add_argument("--z-clearance", type=float, default=0.03)
    parser.add_argument("--overlap-time", type=float, default=0.16)
    parser.add_argument("--swing-time", type=float, default=0.11)
    parser.add_argument("--stance-state-blend", type=float, default=0.5)
    parser.add_argument("--swing-state-blend", type=float, default=0.05)
    parser.add_argument("--contact-threshold", type=float, default=0.5)
    parser.add_argument("--attitude-kp", type=float, default=0.0)
    parser.add_argument("--attitude-kd", type=float, default=0.0)
    parser.add_argument("--velocity-kp", type=float, default=0.0)
    parser.add_argument("--max-attitude-feedback", type=float, default=0.10)
    parser.add_argument("--max-velocity-feedback", type=float, default=0.03)
    parser.add_argument("--plot-window", type=float, default=6.0)
    parser.add_argument("--plot-update-interval", type=float, default=0.15)
    parser.add_argument("--plot-start-delay", type=float, default=0.30)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def initialize_controller(args: argparse.Namespace) -> tuple[Configuration, Controller, State]:
    config = Configuration()
    config.z_clearance = args.z_clearance
    config.overlap_time = args.overlap_time
    config.swing_time = args.swing_time
    controller = Controller(config, four_legs_inverse_kinematics)
    state = State()
    state.quat_orientation = np.array([1.0, 0.0, 0.0, 0.0])

    initial_command = Command()
    initial_command.height = args.height
    initial_command.pitch = args.pitch
    initial_command.roll = args.roll
    controller.run(state, initial_command)
    state.behavior_state = BehaviorState.DEACTIVATED
    state.ticks = 0
    return config, controller, state


def apply_feedback(
    command: Command,
    state: State,
    args: argparse.Namespace,
    mode: str,
    feedback_params: dict[str, float],
) -> Command:
    if mode != "trot":
        return command

    roll, pitch, _ = mat2euler(quat2mat(state.quat_orientation))
    body_rates = state.angular_velocity
    attitude_feedback = np.array(
        [
            -feedback_params["attitude_kp"] * roll - feedback_params["attitude_kd"] * body_rates[0],
            -feedback_params["attitude_kp"] * pitch - feedback_params["attitude_kd"] * body_rates[1],
        ]
    )
    attitude_feedback = np.clip(
        attitude_feedback,
        -args.max_attitude_feedback,
        args.max_attitude_feedback,
    )
    command.roll += float(attitude_feedback[0])
    command.pitch += float(attitude_feedback[1])

    velocity_feedback = feedback_params["velocity_kp"] * (command.horizontal_velocity[0] - state.body_velocity[0])
    velocity_feedback = float(np.clip(velocity_feedback, -args.max_velocity_feedback, args.max_velocity_feedback))
    command.horizontal_velocity[0] += velocity_feedback
    return command


def initialize_plot_history(config: Configuration, window_seconds: float) -> dict[str, object]:
    max_samples = max(10, min(1000, int(window_seconds / config.dt) + 2))
    return {
        "time": deque(maxlen=max_samples),
        "pitch": deque(maxlen=max_samples),
        "vx": deque(maxlen=max_samples),
        "contacts": [deque(maxlen=max_samples) for _ in range(4)],
        "window": window_seconds,
    }


def plots_enabled(args: argparse.Namespace) -> bool:
    return (not args.no_plots) and args.plot_window > 0.0


def record_plot_sample(history: dict[str, object], sim_time: float, state: State) -> None:
    _, pitch, _ = mat2euler(quat2mat(state.quat_orientation))
    history["time"].append(sim_time)  # type: ignore[index]
    history["pitch"].append(float(pitch))  # type: ignore[index]
    history["vx"].append(float(state.body_velocity[0]))  # type: ignore[index]
    contacts = history["contacts"]  # type: ignore[assignment]
    for leg_index in range(4):
        contacts[leg_index].append(float(state.contact_estimate[leg_index]))


def _fill_line(
    fig: mujoco.MjvFigure,
    line_index: int,
    x_values: np.ndarray,
    y_values: np.ndarray,
    name: str,
    color: tuple[float, float, float],
) -> None:
    num_points = min(len(x_values), fig.linedata.shape[1] // 2)
    fig.linepnt[line_index] = num_points
    if num_points == 0:
        fig.linename[line_index] = b""
        return
    fig.linename[line_index] = name.encode()
    fig.linergb[line_index] = color
    for point_index in range(num_points):
        fig.linedata[line_index, 2 * point_index] = x_values[point_index]
        fig.linedata[line_index, 2 * point_index + 1] = y_values[point_index]


def _series_bounds(values: np.ndarray, lower_pad: float, upper_pad: float, fallback: tuple[float, float]) -> tuple[float, float]:
    if values.size == 0:
        return fallback
    y_min = float(np.min(values))
    y_max = float(np.max(values))
    if abs(y_max - y_min) < 1e-6:
        center = 0.5 * (y_max + y_min)
        half = max(lower_pad, upper_pad, 0.05)
        return center - half, center + half
    return y_min - lower_pad, y_max + upper_pad


def _configure_single_line_figure(
    title: str,
    ylabel: str,
    times: np.ndarray,
    values: np.ndarray,
    color: tuple[float, float, float],
    value_range: tuple[float, float] | None = None,
) -> mujoco.MjvFigure:
    fig = mujoco.MjvFigure()
    mujoco.mjv_defaultFigure(fig)
    fig.title = f"{title} [{ylabel}]"
    fig.xlabel = "t (s)"
    fig.flg_legend = 0
    fig.gridsize = np.array([4, 4])
    fig.linewidth = 3
    if value_range is None:
        value_range = _series_bounds(values, 0.02, 0.02, (-0.1, 0.1))
    x_min = float(times[0]) if len(times) else 0.0
    x_max = float(times[-1]) if len(times) else 1.0
    if abs(x_max - x_min) < 1e-6:
        x_max = x_min + 1.0
    fig.range[0] = np.array([x_min, x_max])
    fig.range[1] = np.array([value_range[0], value_range[1]])
    _fill_line(fig, 0, times, values, title.lower(), color)
    for line_index in range(1, len(fig.linepnt)):
        fig.linepnt[line_index] = 0
    return fig


def _configure_contact_figure(times: np.ndarray, contacts: list[np.ndarray]) -> mujoco.MjvFigure:
    fig = mujoco.MjvFigure()
    mujoco.mjv_defaultFigure(fig)
    fig.title = "Contacts [stance]"
    fig.xlabel = "t (s)"
    fig.flg_legend = 1
    fig.gridsize = np.array([4, 4])
    fig.linewidth = 3
    x_min = float(times[0]) if len(times) else 0.0
    x_max = float(times[-1]) if len(times) else 1.0
    if abs(x_max - x_min) < 1e-6:
        x_max = x_min + 1.0
    fig.range[0] = np.array([x_min, x_max])
    fig.range[1] = np.array([-0.1, 1.1])
    colors = (
        (0.90, 0.30, 0.30),
        (0.30, 0.90, 0.30),
        (0.30, 0.30, 0.90),
        (0.90, 0.90, 0.30),
    )
    names = ("FR", "FL", "BR", "BL")
    for line_index, (series, color, name) in enumerate(zip(contacts, colors, names)):
        _fill_line(fig, line_index, times, series, name, color)
    for line_index in range(len(names), len(fig.linepnt)):
        fig.linepnt[line_index] = 0
    return fig


def update_live_plots(viewer: mujoco.viewer.Handle, history: dict[str, object]) -> bool:
    viewport = viewer.viewport
    if viewport is None or viewport.width <= 140 or viewport.height <= 120:
        return False

    panel_count = 3
    gap = 12
    outer_margin = 12
    available_width = viewport.width - 2 * outer_margin
    available_height = viewport.height - 2 * outer_margin - (panel_count - 1) * gap
    if available_width < 180 or available_height < 180:
        return False

    width = int(min(480, max(320, viewport.width * 0.42)))
    width = min(width, available_width)

    height = int(min(170, max(120, viewport.height * 0.24)))
    height = min(height, max(90, available_height // panel_count))
    left = max(0, viewport.width - width - 12)

    times = np.asarray(history["time"], dtype=float)
    if times.size == 0:
        return False
    times = times - times[0]
    pitch = np.asarray(history["pitch"], dtype=float)
    vx = np.asarray(history["vx"], dtype=float)
    contacts = [np.asarray(series, dtype=float) for series in history["contacts"]]  # type: ignore[index]

    pitch_fig = _configure_single_line_figure("Pitch", "rad", times, pitch, (0.95, 0.55, 0.25))
    vx_fig = _configure_single_line_figure("Forward Vx", "m/s", times, vx, (0.20, 0.80, 1.00))
    contact_fig = _configure_contact_figure(times, contacts)

    candidate_figures = (pitch_fig, vx_fig, contact_fig)
    figures = []
    top = viewport.height - height - outer_margin
    for fig in candidate_figures:
        if top < 0:
            break
        figures.append((mujoco.MjrRect(left, top, width, height), fig))
        top -= height + gap

    if not figures:
        return False

    viewer.set_figures(figures)
    return True


def run_loop(args: argparse.Namespace, model: mujoco.MjModel, data: mujoco.MjData, viewer=None) -> None:
    config, controller, state = initialize_controller(args)
    observation_interface = SimObservationInterface(model, data)
    imu = SimIMU(observation_interface)
    hardware_interface = SimHardwareInterface(
        model,
        data,
        kp=args.kp,
        kd=args.kd,
        torque_limit=args.torque_limit,
    )
    clock = SimControlClock(model.opt.timestep, config.dt, viewer=viewer)
    command_source = create_command_source(args, config)
    print(f"task sequence: {command_source.scheduler.sequence_text()}")
    print(f"activation delay: {args.activation_delay:.2f}s")
    print(f"default transition: {args.transition_time:.2f}s")
    base_z = args.base_z
    if base_z is None:
        base_z = float(-np.min(state.foot_locations[2, :]) + config.FOOT_RADIUS + 0.004)
    hardware_interface.set_initial_pose(state.joint_angles, base_z)
    plot_history = initialize_plot_history(config, args.plot_window) if plots_enabled(args) else None
    observation_interface.sync_state(
        state,
        stance_state_blend=args.stance_state_blend,
        swing_state_blend=args.swing_state_blend,
        contact_threshold=args.contact_threshold,
    )
    state.quat_orientation = imu.read_orientation()

    total_ticks = clock.total_ticks(args.duration)
    torso_start, _, _ = observation_interface.torso_pose()
    max_roll_pitch = np.zeros(2)
    next_telemetry_time = 0.0
    next_plot_time = args.plot_start_delay
    plot_runtime_enabled = plot_history is not None
    previous_behavior_state = state.behavior_state

    for tick_index in range(total_ticks):
        if viewer is not None and not viewer.is_running():
            break
        plot_dirty = False
        sim_time = tick_index * config.dt

        with clock.viewer_lock():
            observation_interface.sync_state(
                state,
                stance_state_blend=args.stance_state_blend,
                swing_state_blend=args.swing_state_blend,
                contact_threshold=args.contact_threshold,
            )
            state.quat_orientation = imu.read_orientation()
            step_update = command_source.apply_step_config(config, state, sim_time)
            if step_update is not None:
                step_changed, rendered_step = step_update
                if step_changed:
                    print(f"[{sim_time:5.2f}s] task step: {rendered_step}")
            command = command_source.get_command(state, sim_time)
            if command is not None:
                target_mode = command_source.target_mode(sim_time)
                feedback_params = command_source.feedback_params(sim_time)
                command = apply_feedback(command, state, args, target_mode, feedback_params)

            if command is not None:
                controller.run(state, command)
                hardware_interface.set_actuator_postions(state.joint_angles)
                if state.behavior_state != previous_behavior_state:
                    print(
                        f"[{sim_time:5.2f}s] behavior: "
                        f"{previous_behavior_state.name} -> {state.behavior_state.name}"
                    )
                    previous_behavior_state = state.behavior_state

            if plot_history is not None:
                record_plot_sample(plot_history, sim_time, state)
                plot_dirty = True
            if args.telemetry_interval > 0 and sim_time >= next_telemetry_time:
                print(f"[{sim_time:5.2f}s] {observation_interface.telemetry_line()}")
                next_telemetry_time += args.telemetry_interval

            hardware_interface.step(clock.control_interval)

            _, rotation, _ = observation_interface.torso_pose()
            roll, pitch, _ = mat2euler(rotation)
            max_roll_pitch = np.maximum(max_roll_pitch, np.abs([roll, pitch]))

        if viewer is not None:
            if (
                plot_runtime_enabled
                and plot_dirty
                and plot_history is not None
                and sim_time >= next_plot_time
            ):
                try:
                    if update_live_plots(viewer, plot_history):
                        next_plot_time = sim_time + args.plot_update_interval
                except Exception as exc:
                    plot_runtime_enabled = False
                    print(f"[warn] live plots disabled: {exc}")
        clock.finish_tick()

        if not np.isfinite(data.qpos).all() or data.qpos[2] < 0.05:
            raise RuntimeError(f"Simulation became unstable at t={sim_time:.3f}s")

    torso_end, _, _ = observation_interface.torso_pose()
    displacement = torso_end - torso_start
    print(f"torso start xyz: {torso_start.round(4)}")
    print(f"torso end xyz:   {torso_end.round(4)}")
    print(f"torso delta xyz: {displacement.round(4)}")
    print(f"final foot error: {observation_interface.pose_error(state):.4f} m")
    print(f"touch forces: {np.round(observation_interface.contact_forces(), 3)}")
    print(f"max |roll|, |pitch|: {max_roll_pitch.round(4)} rad")


def main() -> None:
    args = parse_args()
    xml_path = Path(__file__).with_name("pupper_floating.xml")
    builder_path = Path(__file__).with_name("build_floating_base_mjcf.py")
    if args.rebuild or not xml_path.exists() or xml_path.stat().st_mtime < builder_path.stat().st_mtime:
        build_mjcf(xml_path)

    model = mujoco.MjModel.from_xml_path(str(xml_path))
    data = mujoco.MjData(model)

    if args.headless:
        run_loop(args, model, data)
        return

    viewer = mujoco_viewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False)
    try:
        run_loop(args, model, data, viewer=viewer)
    finally:
        viewer.close()
        time.sleep(0.05)


if __name__ == "__main__":
    main()
