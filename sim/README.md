# MuJoCo 最小学习环境

这个目录提供一个“固定机身 + 12 关节可视化”的最小版本，用来复用本仓库的：

- 步态/落脚点规划：`src/Controller.py`
- 逆运动学：`pupper/Kinematics.py`
- 机器人参数：`pupper/Config.py`

它会直接把控制器输出的关节角写入 MuJoCo 模型，重点是学习运动学控制，不是完整动力学仿真。

这里桥接时做了一个关键转换：原项目第三个角更接近“下杆绝对角”，MuJoCo 串联铰链里会自动转成相对膝角。

## 环境

建议使用你现有的 `mujoco_learn`：

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mujoco_learn
pip install transforms3d
```

## 运行

先做无界面检查：

```bash
python sim/run_fixed_base.py --headless --duration 2 --mode rest --rebuild
python sim/run_fixed_base.py --headless --duration 2 --mode trot
```

再打开 MuJoCo 可视化：

```bash
python sim/run_fixed_base.py --mode trot --duration 20
```

如果你想让机身也动，用浮动机身版本。

现在 `run_floating_base.py` 走“仿真本地任务层 + 实机同款控制器”的链路：

- `TaskScheduler -> TaskCommandSource -> Controller -> IK -> PD torque -> MuJoCo`
- 不依赖 `UDPComms`
- 不需要 `JoystickInterface`
- 任务层会自动发出 `activate_event / trot_event`

浮动机身版本常见运行方式：

```bash
python sim/run_floating_base.py --headless --duration 4 --mode rest --rebuild
python sim/run_floating_base.py --headless --duration 6 --mode trot
python sim/run_floating_base.py --mode trot --duration 20
python sim/run_floating_base.py --mode rest
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0,rest:1.0"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0@height=-0.17,trot:4.0@vx=0.08;pitch=0.03,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;z_clearance=0.04;overlap_time=0.18;swing_time=0.10,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;attitude_kp=0.03;attitude_kd=0.005;velocity_kp=0.2,rest"
python sim/run_floating_base.py --duration 8 --transition-time 0.3 --task-sequence "rest:1.0,trot:4.0,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;transition_time=0.4,rest"
```

打开 viewer 时，右侧会实时显示 3 个曲线面板：

- `Pitch`
- `Forward Vx`
- `Contacts`

如果你本机的 viewer 对曲线刷新比较敏感，先用：

```bash
python sim/run_floating_base.py --mode trot --no-plots
```

现在曲线面板默认已经改成“延迟启动 + 低频刷新”，也可以手动调：

```bash
python sim/run_floating_base.py --mode trot --plot-window 8 --plot-update-interval 0.2
```

当前默认参数已经切到“接触感知回灌”版：`x_vel=0.06`、`z_clearance=0.03`、`overlap_time=0.16`、`swing_time=0.11`、`stance_state_blend=0.5`、`swing_state_blend=0.05`、`kp=24`、`kd=2.2`、`settle=1.0`。
在我这边的无界面测试里，`20s` 可以稳定前进，机身前移约 `0.90m`，最大 pitch 约 `0.091rad`；如果把 `x_vel` 降到 `0.05`，最大 pitch 可进一步压到约 `0.086rad`。

浮动机身版本现在还额外做了两件事：

- 把 MuJoCo 的关节、足端、机身姿态、机身速度直接写回 `State`
- 按接触状态做状态校正：支撑腿更强回灌，摆动腿更弱回灌

常用参数：

```bash
python sim/run_fixed_base.py --mode rest --pitch 0.2 --roll 0.1
python sim/run_fixed_base.py --mode trot --x-vel 0.15 --y-vel 0.05
python sim/run_fixed_base.py --mode trot --yaw-rate 0.8
python sim/run_floating_base.py --mode trot --x-vel 0.06 --kp 24 --kd 2.2 --settle 1.0
python sim/run_floating_base.py --mode trot --x-vel 0.06
python sim/run_floating_base.py --mode trot --x-vel 0.05
python sim/run_floating_base.py --mode trot --activation-delay 0.5 --settle 1.0
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0@height=-0.18,trot:4.0@vx=0.08;vy=0.02;pitch=0.03,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;z_clearance=0.04;overlap=0.18;swing=0.10,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;att_kp=0.03;att_kd=0.005;vel_kp=0.2,rest"
python sim/run_floating_base.py --duration 8 --transition-time 0.3 --task-sequence "rest:1.0,trot:4.0,rest"
python sim/run_floating_base.py --duration 8 --task-sequence "rest:1.0,trot:4.0@vx=0.08;blend=0.4,rest"
python sim/run_floating_base.py --mode rest --height -0.17 --base-z 0.18
python sim/run_floating_base.py --mode trot --telemetry-interval 0
python sim/run_floating_base.py --mode trot --stance-state-blend 0.5 --swing-state-blend 0.05
python sim/run_floating_base.py --mode trot --z-clearance 0.03 --overlap-time 0.16 --swing-time 0.11
python sim/run_floating_base.py --mode trot --attitude-kp 0.03 --attitude-kd 0.005
python sim/run_floating_base.py --mode trot --plot-window 8
python sim/run_floating_base.py --mode trot --plot-window 8 --plot-update-interval 0.2
python sim/run_floating_base.py --mode trot --no-plots
```

## 文件

- `sim/build_fixed_base_mjcf.py`：按 `pupper/Config.py` 生成 `sim/pupper_fixed.xml`
- `sim/run_fixed_base.py`：控制器到 MuJoCo 的最小桥接
- `sim/build_floating_base_mjcf.py`：生成 `sim/pupper_floating.xml`
- `sim/sim_robot.py`：MuJoCo 版 IMU / 执行器 / 状态观测 / 时钟适配层
- `sim/run_floating_base.py`：浮动机身 + PD 力矩控制
- `sim/pupper_fixed.xml`：首次运行自动生成
- `sim/pupper_floating.xml`：首次运行自动生成

## 说明

浮动机身版本现在的命令链路就是“本地任务层 + 轻量状态反馈”：

- 关节目标来自原仓库 `Controller + IK`
- MuJoCo 里通过 PD 力矩追踪关节目标
- 控制器状态里会保存测得的关节角、关节速度、足端位置、机身姿态、机身速度
- 接触腿默认强回灌，摆动腿默认弱回灌
- 启动流程更接近 `run_robot.py`：`DEACTIVATED -> REST -> TROT`
- 现在可以用 `TaskScheduler` 显式编排任务序列，例如 `rest -> trot -> rest`
- 每个任务段还能覆盖步态参数，如 `z_clearance / overlap_time / swing_time`
- 每个任务段还能覆盖姿态/速度反馈增益，如 `attitude_kp / attitude_kd / velocity_kp`
- 现在还支持段间平滑过渡，避免参数一步跳变
- 终端会定期打印 `xyz / rpy / touch` 遥测
- viewer 模式会实时显示 `pitch / vx / contact` 曲线面板

`--task-sequence` 的格式是：

- `rest:1.0,trot:3.0,rest:1.0`
- `rest:1.0@height=-0.17,trot:3.0@vx=0.08;pitch=0.03,rest`
- `rest:1.0,trot:3.0@vx=0.08;z_clearance=0.04;overlap_time=0.18;swing_time=0.10,rest`
- `rest:1.0,trot:3.0@vx=0.08;attitude_kp=0.03;attitude_kd=0.005;velocity_kp=0.2,rest`
- `rest:1.0,trot:3.0@vx=0.08;transition_time=0.3,rest`
- 只有最后一段可以省略时长，例如 `rest:1.0,trot:3.0,rest`
- 每段都可以在 `@` 后面写局部参数，多个参数用 `;` 分隔
- `--transition-time` 可以设置所有任务段的默认平滑过渡时间
- 单段也可以单独覆盖：`transition_time`，别名 `transition` / `blend_time` / `blend`
- 当前支持的局部参数：`vx`、`vy`、`yaw_rate`、`height`、`pitch`、`roll`、`z_clearance`、`overlap_time`、`swing_time`、`attitude_kp`、`attitude_kd`、`velocity_kp`、`transition_time`
- 其中别名也可用：`x_vel`/`vx`、`y_vel`/`vy`、`yaw`/`yaw_rate`、`z`/`height`、`clearance`/`z_clearance`、`overlap`/`overlap_time`、`swing`/`swing_time`、`att_kp`/`attitude_kp`、`att_kd`/`attitude_kd`、`vel_kp`/`velocity_kp`、`transition`/`transition_time`、`blend`/`transition_time`
- 如果提供了 `--task-sequence`，它会覆盖 `--mode` 和 `--settle` 的默认调度逻辑

如果你更关注“稳”而不是“快”，优先用：

- 更小的 `x_vel`
- 更小的 `z_clearance`
- 更大的 `overlap_time`

所以它很适合学习“步态规划如何推动机身前进”，也能初步观察状态估计误差如何影响步态，但还不是严格的高保真全状态闭环。

## 后续可扩展

下一步如果你想继续学：

1. 把 `qpos` 直写改成 position actuator + PD
2. 把 MuJoCo 的关节/足端状态真正回灌到控制器
3. 打开更完整的地面接触和重力下稳定性调参
4. 把 MuJoCo 姿态回灌到 `state.quat_orientation`
