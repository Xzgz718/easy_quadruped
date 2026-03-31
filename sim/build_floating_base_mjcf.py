from __future__ import annotations

from pathlib import Path

from pupper.Config import Configuration, SimulationConfig
from sim.model_constants import JOINT_NAMES, LEG_SPECS


def _fmt(values) -> str:
    return " ".join(f"{float(value):.6f}" for value in values)


def _leg_block(config: Configuration, sim_config: SimulationConfig, prefix: str, leg_index: int, rgba: str) -> str:
    origin = config.LEG_ORIGINS[:, leg_index]
    abad_offset = config.ABDUCTION_OFFSETS[leg_index]
    upper_mass = config.LEG_MASS * 0.33
    lower_mass = config.LEG_MASS * 0.52
    foot_mass = config.LEG_MASS * 0.15
    return f"""
    <body name="{prefix}_abad_body" pos="{_fmt(origin)}">
      <joint name="{prefix}_abad" type="hinge" axis="1 0 0" range="-1.4 1.4" damping="{sim_config.REV_DAMPING:.6f}" armature="{sim_config.ARMATURE:.6f}"/>
      <geom name="{prefix}_abad_link" type="capsule" fromto="0 0 0 0 {abad_offset:.6f} 0" size="0.009" mass="{upper_mass * 0.25:.6f}" contype="0" conaffinity="0" rgba="{rgba}"/>
      <body name="{prefix}_hip_body" pos="0 {abad_offset:.6f} 0">
        <joint name="{prefix}_hip" type="hinge" axis="0 1 0" range="-2.5 2.5" damping="{sim_config.REV_DAMPING:.6f}" armature="{sim_config.ARMATURE:.6f}"/>
        <geom name="{prefix}_upper_link" type="capsule" fromto="0 0 0 0 0 {-config.LEG_L1:.6f}" size="0.008" mass="{upper_mass:.6f}" contype="0" conaffinity="0" rgba="{rgba}"/>
        <body name="{prefix}_knee_body" pos="0 0 {-config.LEG_L1:.6f}">
          <joint name="{prefix}_knee" type="hinge" axis="0 1 0" range="-2.8 0.4" damping="{sim_config.REV_DAMPING:.6f}" armature="{sim_config.ARMATURE:.6f}"/>
          <geom name="{prefix}_lower_link" type="capsule" fromto="0 0 0 0 0 {-config.LEG_L2:.6f}" size="0.007" mass="{lower_mass:.6f}" contype="0" conaffinity="0" rgba="{rgba}"/>
          <geom name="{prefix}_foot_geom" type="sphere" pos="0 0 {-config.LEG_L2:.6f}" size="{config.FOOT_RADIUS:.6f}" mass="{foot_mass:.6f}" friction="{sim_config.MU:.3f} 0.02 0.01" solref="{sim_config.GEOM_SOLREF}" solimp="{sim_config.GEOM_SOLIMP}" rgba="{rgba}"/>
          <site name="{prefix}_foot" pos="0 0 {-config.LEG_L2:.6f}" size="0.012" rgba="{rgba}"/>
          <site name="{prefix}_contact" pos="0 0 {-config.LEG_L2:.6f}" size="0.016" rgba="{rgba[:-1]}0.25"/>
        </body>
      </body>
    </body>
    """


def _actuator_block(sim_config: SimulationConfig) -> str:
    torque_limit = sim_config.MAX_JOINT_TORQUE
    return "\n".join(
        f'    <motor name="{joint_name}_motor" joint="{joint_name}" gear="1" ctrllimited="true" ctrlrange="-{torque_limit:.3f} {torque_limit:.3f}"/>'
        for joint_name in JOINT_NAMES
    )


def _sensor_block() -> str:
    sensors = [
        '    <framepos name="torso_pos" objtype="site" objname="torso_center"/>',
        '    <framequat name="imu_quat" objtype="site" objname="imu_site"/>',
        '    <gyro name="imu_gyro" site="imu_site"/>',
        '    <accelerometer name="imu_acc" site="imu_site"/>',
        '    <velocimeter name="imu_vel" site="imu_site"/>',
    ]
    for prefix, _, _ in LEG_SPECS:
        sensors.append(f'    <framepos name="{prefix}_foot_pos" objtype="site" objname="{prefix}_foot"/>')
        sensors.append(f'    <touch name="{prefix}_touch" site="{prefix}_contact"/>')
    for joint_name in JOINT_NAMES:
        sensors.append(f'    <jointpos name="{joint_name}_pos" joint="{joint_name}"/>')
        sensors.append(f'    <jointvel name="{joint_name}_vel" joint="{joint_name}"/>')
    return "\n".join(sensors)


def build_mjcf(xml_path: str | Path | None = None) -> Path:
    config = Configuration()
    sim_config = SimulationConfig()
    if xml_path is None:
        xml_path = Path(__file__).with_name("pupper_floating.xml")
    xml_path = Path(xml_path)

    leg_blocks = "\n".join(
        _leg_block(config, sim_config, prefix, leg_index, rgba)
        for prefix, leg_index, rgba in LEG_SPECS
    )
    torso_mass = config.FRAME_MASS + config.MODULE_MASS * 4

    xml = f"""<mujoco model="stanford_quadruped_floating">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{sim_config.DT:.6f}" integrator="RK4" gravity="0 0 -9.81" iterations="50" ls_iterations="20"/>
  <visual>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.75 0.75 0.75" specular="0.20 0.20 0.20"/>
    <map znear="0.01"/>
  </visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.20 0.20 0.20" rgb2="0.10 0.10 0.10" width="512" height="512"/>
    <material name="grid" texture="grid" texrepeat="4 4" reflectance="0.15"/>
  </asset>
  <worldbody>
    <light name="sun" pos="0 0 2.0" dir="0 0 -1" directional="true"/>
    <geom name="floor" type="plane" size="4 4 0.1" material="grid" friction="{sim_config.MU:.3f} 0.05 0.01" solref="{sim_config.GEOM_SOLREF}" solimp="{sim_config.GEOM_SOLIMP}"/>
    <camera name="overview" pos="1.00 -1.40 0.70" xyaxes="1.0 0.0 0.0 0.0 0.55 0.84"/>
    <body name="torso" pos="0 0 0.19">
      <freejoint name="root"/>
      <geom name="torso_geom" type="box" size="{config.L / 2:.6f} {config.W / 2:.6f} {config.T / 2:.6f}" mass="{torso_mass:.6f}" contype="0" conaffinity="0" rgba="0.18 0.18 0.18 1"/>
      <site name="torso_center" pos="0 0 0" size="0.01" rgba="1 1 1 1"/>
      <site name="imu_site" pos="0 0 0" size="0.006" rgba="0.2 0.8 1 0.8"/>
{leg_blocks}
    </body>
  </worldbody>
  <actuator>
{_actuator_block(sim_config)}
  </actuator>
  <sensor>
{_sensor_block()}
  </sensor>
</mujoco>
"""
    xml_path.write_text(xml)
    return xml_path


if __name__ == "__main__":
    path = build_mjcf()
    print(path)
