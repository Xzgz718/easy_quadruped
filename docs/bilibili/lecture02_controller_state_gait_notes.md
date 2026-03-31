# StanfordQuadruped 第 2 讲讲义：控制器内核、状态机与步态调度

这份讲义对应系列课程的第 2 讲，目标是把 `Controller.run()` 讲成整个项目的“控制中枢”，并让观众真正明白状态机、步态相位和接触表的关系。

建议时长：35~45 分钟

主文件：

- `src/Controller.py`
- `src/State.py`
- `src/Gaits.py`
- `pupper/Config.py`

## 本讲目标

- 从 `Controller.run()` 看懂整套控制决策的骨架
- 讲清楚 `BehaviorState` 怎样随手柄/任务事件切换
- 讲清楚 `GaitController` 怎样把时间分成步态相位
- 让观众知道四条腿为什么会形成对角小跑

## 先给观众一个判断

`src/Controller.py` 不是一个只做“控制律”的文件，它其实同时承担了：

- 行为状态机
- gait 分派
- stance / swing 路由
- 姿态补偿
- 逆运动学调用

所以看这个项目，真正的核心不是单个公式，而是 `Controller.run()` 这一个函数。

## 行为状态机必须讲清楚

状态枚举定义在 `src/State.py`：

- `DEACTIVATED`
- `REST`
- `TROT`
- `HOP`
- `FINISHHOP`

而事件来自两处：

- 实机：`JoystickInterface`
- 仿真：`TaskCommandSource`

状态切换逻辑建议直接用口头规则讲：

- `activate_event`：`DEACTIVATED <-> REST`
- `trot_event`：`REST <-> TROT`，也允许从跳跃相关态直接切到 `TROT`
- `hop_event`：`REST -> HOP -> FINISHHOP -> REST`

## `Controller.run()` 的主干要怎么讲

最稳的讲法是按状态分支讲。

### `TROT`

- 先调用 `step_gait()` 更新足端目标
- 再叠加命令里的期望 `roll / pitch`
- 再用 IMU 做有限的机身倾斜补偿
- 最后做四腿逆运动学，得到 12 个关节角

### `REST`

- 保持默认站姿
- 允许调高度、滚转、俯仰和缓变偏航
- 偏航不是一步到位，而是走一阶滤波

### `HOP / FINISHHOP`

- 这两个分支没有复杂轨迹
- 本质是用两组不同高度的静态足端位置实现压缩与回落
- 很适合顺手讲“这个项目的跳跃并不是动力学最优控制”

## `step_gait()` 是理解腿级逻辑的关键

这部分一定要讲成下面的结构：

```flow
for 每条腿:
  先看当前 contact_mode
    -> 1: 走 StanceController
    -> 0: 走 SwingController
```

它告诉观众一件很重要的事：

- 控制器不是“对机器人整体算一次动作”
- 而是每一拍都要分别决定四条腿当前属于支撑相还是摆动相

## `GaitController` 的三个函数

- `phase_index(ticks)`
  - 当前属于 4 个步态相位中的哪一相
- `subphase_ticks(ticks)`
  - 当前子相已经走了多少 tick
- `contacts(ticks)`
  - 当前 4 条腿的接触模式

这里最值得当场推一遍的，是 `Configuration` 里的相位参数：

```python
dt = 0.01
overlap_time = 0.10
swing_time = 0.15
```

由此得到：

- `overlap_ticks = 10`
- `swing_ticks = 15`
- 一个周期总长度 `phase_length = 50`

## 对角小跑的接触表怎么讲

`contact_phases` 是本项目最值得展示的一段参数：

```text
FR: 1 1 1 0
FL: 1 0 1 1
BR: 1 0 1 1
BL: 1 1 1 0
```

这说明：

- `FL + BR` 同时摆动
- `FR + BL` 同时摆动
- 两组对角腿交替工作

这里就是讲“为什么这是 trot，而不是 walk / pace / bound”的最好位置。

## 这一讲建议观众记住的概念

- 步态是“时间组织方式”，不是“某个关节轨迹”
- 状态机决定宏观模式
- gait 决定每条腿此刻属于 stance 还是 swing
- `ticks` 是整个控制器的时间基准

## 本讲建议演示

建议用浮动机身版演示“进入 trot 前先 settle”：

```bash
python sim/run_floating_base.py --duration 8 --mode trot --settle 1.0 --no-plots
```

也可以直接演示任务序列：

```bash
python sim/run_floating_base.py --duration 8 \
  --task-sequence "rest:1.0,trot:4.0,rest" --no-plots
```

## 本讲作业

- 让观众根据参数自己算一个 gait 周期有多少 tick
- 让观众解释对角腿为什么会同时抬起
- 让观众画出 `REST / TROT / HOP` 的切换图
