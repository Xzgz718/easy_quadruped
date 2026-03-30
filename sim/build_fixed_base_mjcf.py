from __future__ import annotations

from pathlib import Path

from pupper.Config import Configuration, SimulationConfig

LEG_SPECS = (
    ("fr", 0, "0.90 0.30 0.30 1"),
    ("fl", 1, "0.30 0.90 0.30 1"),
    ("br", 2, "0.30 0.30 0.90 1"),
    ("bl", 3, "0.90 0.90 0.30 1"),
)
JOINT_NAMES = tuple(
    name
    for prefix, _, _ in LEG_SPECS
    for name in (f"{prefix}_abad", f"{prefix}_hip", f"{prefix}_knee")
)
FOOT_SITE_NAMES = tuple(f"{prefix}_foot" for prefix, _, _ in LEG_SPECS)


def _fmt(values) -> str:
    return " ".join(f"{float(value):.6f}" for value in values)


def _leg_block(config: Configuration, sim_config: SimulationConfig, prefix: str, leg_index: int, rgba: str) -> str:
    origin = config.LEG_ORIGINS[:, leg_index]
    abad_offset = config.ABDUCTION_OFFSETS[leg_index]
    return f"""
    <body name="{prefix}_abad_body" pos="{_fmt(origin)}">
      <joint name="{prefix}_abad" type="hinge" axis="1 0 0" range="-1.4 1.4" damping="{sim_config.REV_DAMPING:.6f}" armature="{sim_config.ARMATURE:.6f}"/>
      <geom name="{prefix}_abad_link" type="capsule" fromto="0 0 0 0 {abad_offset:.6f} 0" size="0.009" rgba="{rgba}"/>
      <body name="{prefix}_hip_body" pos="0 {abad_offset:.6f} 0">
        <joint name="{prefix}_hip" type="hinge" axis="0 1 0" range="-2.5 2.5" damping="{sim_config.REV_DAMPING:.6f}" armature="{sim_config.ARMATURE:.6f}"/>
        <geom name="{prefix}_upper_link" type="capsule" fromto="0 0 0 0 0 {-config.LEG_L1:.6f}" size="0.008" rgba="{rgba}"/>
        <body name="{prefix}_knee_body" pos="0 0 {-config.LEG_L1:.6f}">
          <joint name="{prefix}_knee" type="hinge" axis="0 1 0" range="-2.8 0.4" damping="{sim_config.REV_DAMPING:.6f}" armature="{sim_config.ARMATURE:.6f}"/>
          <geom name="{prefix}_lower_link" type="capsule" fromto="0 0 0 0 0 {-config.LEG_L2:.6f}" size="0.007" rgba="{rgba}"/>
          <geom name="{prefix}_foot_geom" type="sphere" pos="0 0 {-config.LEG_L2:.6f}" size="{config.FOOT_RADIUS:.6f}" rgba="{rgba}"/>
          <site name="{prefix}_foot" pos="0 0 {-config.LEG_L2:.6f}" size="0.012" rgba="{rgba}"/>
        </body>
      </body>
    </body>
    """


def build_mjcf(xml_path: str | Path | None = None) -> Path:
    config = Configuration()
    sim_config = SimulationConfig()
    if xml_path is None:
        xml_path = Path(__file__).with_name("pupper_fixed.xml")
    xml_path = Path(xml_path)

    leg_blocks = "\n".join(
        _leg_block(config, sim_config, prefix, leg_index, rgba)
        for prefix, leg_index, rgba in LEG_SPECS
    )

    xml = f"""<mujoco model="stanford_quadruped_fixed">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{sim_config.DT:.6f}" integrator="RK4" gravity="0 0 -9.81"/>
  <visual>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.75 0.75 0.75" specular="0.20 0.20 0.20"/>
    <map znear="0.01"/>
  </visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.20 0.20 0.20" rgb2="0.10 0.10 0.10" width="512" height="512"/>
    <material name="grid" texture="grid" texrepeat="4 4" reflectance="0.15"/>
  </asset>
  <worldbody>
    <light name="sun" pos="0 0 1.8" dir="0 0 -1" directional="true"/>
    <geom name="floor" type="plane" size="3 3 0.1" material="grid" friction="{sim_config.MU:.3f} 0.05 0.01"/>
    <camera name="overview" pos="0.70 -1.10 0.55" xyaxes="1.0 0.0 0.0 0.0 0.6 0.8"/>
    <body name="torso" pos="0 0 {sim_config.START_HEIGHT:.6f}">
      <geom name="torso_geom" type="box" size="{config.L / 2:.6f} {config.W / 2:.6f} {config.T / 2:.6f}" rgba="0.18 0.18 0.18 1"/>
      <site name="torso_center" pos="0 0 0" size="0.01" rgba="1 1 1 1"/>
{leg_blocks}
    </body>
  </worldbody>
</mujoco>
"""
    xml_path.write_text(xml)
    return xml_path


if __name__ == "__main__":
    path = build_mjcf()
    print(path)
