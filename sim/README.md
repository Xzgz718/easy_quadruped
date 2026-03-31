# MuJoCo Simulation Guide

`sim/` 目录提供了一个围绕 `src/` 控制器和 `pupper/` 运动学配置搭建的 MuJoCo 仿真环境。当前公开快照的主要可运行入口是 `run_floating_base.py`，目标是把已有的步态控制、逆运动学和状态机放进一个便于观察和调参的闭环里。

## 当前可用的仿真入口

- `run_floating_base.py`
  - 使用 `freejoint` 机身和关节 PD 力矩控制。
  - 通过 `SimObservationInterface` 把 MuJoCo 中的姿态、速度、触地和关节状态回填到 `State`。
  - 通过 `TaskScheduler` 在本地生成高层任务序列，不依赖 UDP 手柄输入。

说明：

- 当前公开快照以浮动机身闭环仿真为主。

## 目录结构

- `build_floating_base_mjcf.py`
  - 生成带 `freejoint`、`motor`、`sensor` 和触地 site 的浮动机身 XML。
- `run_floating_base.py`
  - 闭环动力学仿真入口：`TaskScheduler -> Controller -> IK -> PD torque -> MuJoCo -> Observation -> State`。
- `sim_robot.py`
  - 仿真侧 IMU、硬件接口、观测同步和控制时钟适配层。
- `task_scheduler.py`
  - 任务序列解析、参数覆盖和平滑过渡逻辑。
- `pupper_floating.xml`
  - 浮动机身模型快照，通常由脚本生成或更新。

## 环境要求

建议在仓库根目录执行命令。

最少需要的 Python 依赖：

```bash
pip install mujoco transforms3d numpy
```

构建脚本建议使用模块方式执行：

```bash
python -m sim.build_floating_base_mjcf
```

## 快速开始

### 1. 重新生成 XML

```bash
python -m sim.build_floating_base_mjcf
```

也可以在运行仿真时附带 `--rebuild` 自动重建浮动机身 XML。

### 2. 浮动机身闭环仿真

常用运行方式：

```bash
python sim/run_floating_base.py --headless --duration 4 --mode rest --rebuild
python sim/run_floating_base.py --headless --duration 6 --mode trot
python sim/run_floating_base.py --mode trot --duration 20
python sim/run_floating_base.py --mode rest
```

浮动机身版的默认行为：

- `--mode rest` 时默认保持静止。
- `--mode trot` 且 `--settle > 0` 时，默认任务序列是 `rest:settle -> trot`。
- 一旦提供 `--task-sequence`，就会覆盖 `--mode` 和 `--settle` 的默认调度逻辑。

在 viewer 模式下，右侧会尝试显示 3 个实时曲线面板：

- `Pitch`
- `Forward Vx`
- `Contacts`

如果本机 viewer 对绘图较敏感，可以关闭：

```bash
python sim/run_floating_base.py --mode trot --no-plots
```

也可以调整绘图窗口和刷新频率：

```bash
python sim/run_floating_base.py --mode trot --plot-window 8 --plot-update-interval 0.2
```

## 任务序列语法

`task_scheduler.py` 支持把高层任务写成一串时间片段：

```text
mode[:duration][@key=value;key=value...],mode[:duration],...
```

规则：

- 只支持 `rest` 和 `trot`
- 只有最后一个片段可以省略持续时间
- 持续时间可以写成 `inf` 或 `forever`
- 参数列表放在 `@` 后面，多个参数用 `;` 或 `|` 分隔
- 全局 `--transition-time` 是默认段间过渡时间
- 某一段可以单独写 `transition_time=...` 覆盖默认值

示例：

```bash
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0@height=-0.17,trot:4.0@vx=0.08;pitch=0.03,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;z_clearance=0.04;overlap_time=0.18;swing_time=0.10,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;attitude_kp=0.03;attitude_kd=0.005;velocity_kp=0.2,rest"
python sim/run_floating_base.py --duration 8 --transition-time 0.3 --task-sequence "rest:1.0,trot:4.0,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;transition_time=0.4,rest"
```

支持的任务参数：

- 运动命令
  - `vx` / `x_vel`
  - `vy` / `y_vel`
  - `yaw_rate` / `yaw` / `wz`
  - `height` / `z`
  - `pitch`
  - `roll`
- 步态参数
  - `z_clearance` / `clearance`
  - `overlap_time` / `overlap`
  - `swing_time` / `swing`
- 反馈参数
  - `attitude_kp` / `att_kp`
  - `attitude_kd` / `att_kd`
  - `velocity_kp` / `vel_kp`
- 过渡参数
  - `transition_time` / `transition` / `blend_time` / `blend`

## 重要参数

控制与约束：

- `--kp`
- `--kd`
- `--torque-limit`
- `--base-z`
- `--activation-delay`
- `--settle`

步态与状态融合：

- `--z-clearance`
- `--overlap-time`
- `--swing-time`
- `--stance-state-blend`
- `--swing-state-blend`
- `--contact-threshold`

简单反馈补偿：

- `--attitude-kp`
- `--attitude-kd`
- `--velocity-kp`
- `--max-attitude-feedback`
- `--max-velocity-feedback`

可视化与终端输出：

- `--telemetry-interval`
- `--plot-window`
- `--plot-update-interval`
- `--plot-start-delay`
- `--no-plots`

调参示例：

```bash
python sim/run_floating_base.py --mode trot --x-vel 0.06 --kp 24 --kd 2.2 --settle 1.0
python sim/run_floating_base.py --mode trot --x-vel 0.05
python sim/run_floating_base.py --mode trot --activation-delay 0.5 --settle 1.0
python sim/run_floating_base.py --mode trot --stance-state-blend 0.5 --swing-state-blend 0.05
python sim/run_floating_base.py --mode trot --z-clearance 0.03 --overlap-time 0.16 --swing-time 0.11
python sim/run_floating_base.py --mode trot --attitude-kp 0.03 --attitude-kd 0.005
python sim/run_floating_base.py --mode rest --height -0.17 --base-z 0.18
python sim/run_floating_base.py --mode trot --telemetry-interval 0
```

## 建议的阅读顺序

如果你想理解 `sim/` 的工作方式，建议按下面顺序读：

1. `sim/run_floating_base.py`
2. `sim/sim_robot.py`
3. `sim/task_scheduler.py`
4. `sim/build_floating_base_mjcf.py`
5. `pupper/Config.py`
6. `pupper/Kinematics.py`
7. `src/Controller.py`

## 注意事项

- 该目录服务的是 `pupper/` 这条主线，不是 `woofer/`
- 文档中的命令默认都假设当前工作目录是仓库根目录
