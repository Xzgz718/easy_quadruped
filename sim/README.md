# MuJoCo Simulation Guide

`sim/` 目录提供了一个围绕 `pupper/` 控制器搭建的 MuJoCo 仿真环境，目标不是复刻整套树莓派实机软件，而是把已有的步态控制、逆运动学和状态机放进一个更容易观察和调参的仿真闭环里。

当前目录包含两条仿真路径：

- 固定机身版：`run_fixed_base.py`
  - 机身不参与动力学，只把控制器输出的关节角直接写进 MuJoCo 关节位置。
  - 适合检查逆运动学、足端轨迹和控制器输出是否合理。
- 浮动机身版：`run_floating_base.py`
  - 机身使用 `freejoint`，关节由 PD 力矩驱动。
  - 通过 `SimObservationInterface` 把 MuJoCo 里的姿态、速度、触地和关节状态写回 `State`。
  - 通过 `TaskScheduler` 在本地生成任务序列，不依赖 UDP 手柄输入。

## 目录结构

- `build_fixed_base_mjcf.py`
  - 根据 `pupper.Config.Configuration` 和 `pupper.Config.SimulationConfig` 生成固定机身 XML。
- `build_floating_base_mjcf.py`
  - 生成带 `freejoint`、motor、sensor 和触地 site 的浮动机身 XML。
- `run_fixed_base.py`
  - 最小桥接版：`Controller -> IK -> qpos`。
- `run_floating_base.py`
  - 动力学版：`TaskScheduler -> Controller -> IK -> PD torque -> MuJoCo`。
- `sim_robot.py`
  - 仿真侧的 IMU、硬件接口、观测接口、控制时钟和任务命令源适配层。
- `task_scheduler.py`
  - 任务序列解析、分段参数覆盖和平滑过渡逻辑。
- `pupper_fixed.xml`
  - 固定机身模型，通常由构建脚本自动生成或更新。
- `pupper_floating.xml`
  - 浮动机身模型，通常由构建脚本自动生成或更新。

## 环境要求

建议在仓库根目录执行命令：`F:\stanford_quadruped`

最少需要的 Python 依赖：

```bash
pip install mujoco transforms3d numpy
```

说明：

- `run_fixed_base.py` 和 `run_floating_base.py` 会自行把仓库根目录加入 `sys.path`。
- `build_*.py` 直接按脚本路径执行时不一定能解析到 `pupper` 包，最稳妥的方式是使用模块形式：

```bash
python -m sim.build_fixed_base_mjcf
python -m sim.build_floating_base_mjcf
```

## 快速开始

### 1. 重新生成 XML

```bash
python -m sim.build_fixed_base_mjcf
python -m sim.build_floating_base_mjcf
```

也可以在运行脚本时附带 `--rebuild` 自动重建。

### 2. 固定机身仿真

固定机身版把控制器算出的目标角直接写入关节位置，不走力矩控制。

```bash
python sim/run_fixed_base.py --headless --duration 2 --mode rest --rebuild
python sim/run_fixed_base.py --headless --duration 2 --mode trot
python sim/run_fixed_base.py --mode trot --duration 20
```

常用参数：

- `--mode {rest,trot}`
- `--duration`
- `--headless`
- `--rebuild`
- `--x-vel`
- `--y-vel`
- `--yaw-rate`
- `--height`
- `--pitch`
- `--roll`

几个例子：

```bash
python sim/run_fixed_base.py --mode rest --pitch 0.2 --roll 0.1
python sim/run_fixed_base.py --mode trot --x-vel 0.15 --y-vel 0.05
python sim/run_fixed_base.py --mode trot --yaw-rate 0.8
```

### 3. 浮动机身仿真

浮动机身版更接近“控制器驱动真实机器人”的链路：

```text
TaskScheduler
  -> TaskCommandSource
  -> Controller
  -> four_legs_inverse_kinematics
  -> SimHardwareInterface(PD torque)
  -> MuJoCo
  -> SimObservationInterface
  -> State
```

常用运行方式：

```bash
python sim/run_floating_base.py --headless --duration 4 --mode rest --rebuild
python sim/run_floating_base.py --headless --duration 6 --mode trot
python sim/run_floating_base.py --mode trot --duration 20
python sim/run_floating_base.py --mode rest
```

浮动机身版的默认行为：

- `--mode rest` 时默认只保持静止。
- `--mode trot` 且 `--settle > 0` 时，默认任务序列是 `rest:settle -> trot`。
- `--task-sequence` 一旦提供，会覆盖 `--mode` 和 `--settle` 对任务流程的默认调度。

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
- 某一段也可以单独写 `transition_time=...` 覆盖默认值

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

## 浮动机身版的重要参数

除了固定机身版已有的 `--mode`、`--duration`、`--height`、`--pitch`、`--roll` 等参数外，浮动机身版还提供以下关键调参入口。

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

## 当前实现细节

### 固定机身版

- 使用 `Controller` 和 `four_legs_inverse_kinematics`
- 把控制器输出的 12 个关节角转换为 MuJoCo 关节位置
- 第三个关节写入的是相对膝角：`knee = alpha[2] - alpha[1]`
- 每一步通过 `pose_error()` 对比 MuJoCo 足端位置和控制器里的 `state.foot_locations`

### 浮动机身版

- `SimHardwareInterface` 维护目标关节位置，并用 PD 力矩追踪
- `SimObservationInterface` 读取：
  - 机身位置、姿态、线速度、角速度
  - 四足足端位置
  - 四足触地力
  - 12 个关节角和关节速度
- 观测会写回 `State`
  - `body_position`
  - `body_velocity`
  - `angular_velocity`
  - `measured_foot_locations`
  - `measured_joint_angles`
  - `measured_joint_velocities`
  - `foot_forces`
  - `contact_estimate`
- 足端状态融合是分腿做的：
  - 触地腿使用 `stance_state_blend`
  - 摆动腿使用 `swing_state_blend`
- 当任务段切换且模式变化时，会把 `state.ticks` 置零，便于控制器重新进入对应步态阶段

### 失稳保护

浮动机身循环里有一个简单的仿真稳定性保护：

- `data.qpos` 出现非有限值会报错
- 机身 `z` 低于 `0.05` 会报错并中断仿真

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
- 如果只是想检查控制器和逆运动学，优先用固定机身版
- 如果想观察接触、姿态、速度反馈和参数过渡，再切到浮动机身版
