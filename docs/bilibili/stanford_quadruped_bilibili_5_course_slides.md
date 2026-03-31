---
marp: true
paginate: true
theme: default
size: 16:9
---

# StanfordQuadruped 项目五讲课程
## B 站视频 PPT 文稿

- 面向对象：想借真实项目入门四足控制的人
- 课程目标：看懂主链、跑通仿真、知道如何扩展
- 核心路径：`Command -> Controller -> gait -> foot -> IK -> actuator -> State`

---

# 这套课解决什么问题

- 不再把仓库看成一堆散乱文件
- 看懂 `run_robot.py` 和 `sim/run_floating_base.py` 的关系
- 看懂 `Controller.run()` 怎样驱动四足运动
- 看懂 MuJoCo 为什么是当前最好的学习入口
- 给出从仿真走向实机的路线

---

# 建议先修

- 欧拉角、四元数、旋转矩阵
- 逆运动学基础
- PD 控制与离散时间循环
- 一点点 MuJoCo 使用经验

---

# 五讲拆分

1. 项目全景、入口与控制主循环
2. 控制器内核、状态机与步态调度
3. 足端规划、Raibert 落脚点与逆运动学
4. MuJoCo 闭环仿真、状态回灌与调参
5. 实机接口、Sim2Real 与二次开发路线

---

# 第 1 讲
## 项目全景、入口与控制主循环

- 先判断项目控制范式
- 再认仓库四层结构
- 再看两个入口文件
- 最后建立 `Command / State / Configuration` 心智模型

---

# 这到底是什么项目

- 不是 MPC
- 不是 WBC
- 不是 RL 推理框架
- 是 gait + 足端规划 + IK + 执行器桥接
- 非常适合教学和二次开发

---

# 仓库四层结构

![](../mujoco_quadruped_mastery_tutorial/assets/project_structure_map.png)

- 入口层：`run_robot.py`、`sim/run_*`
- 控制层：`src/`
- 模型与硬件层：`pupper/`
- 仿真桥接层：`sim/`

---

# 两个最重要的入口

- `run_robot.py`
  - 实机原始入口
- `sim/run_floating_base.py`
  - 当前最佳教学入口

结论：

- 先从仿真理解共享控制核心
- 再回头看实机后端

---

# 三个核心数据对象

- `Command`
  - 这一拍想做什么
- `State`
  - 系统现在认为自己在哪
- `Configuration`
  - 控制、步态、几何和平台参数

---

# 一拍控制循环

```python
command = command_source.get_command(...)
state.quat_orientation = imu.read_orientation()
controller.run(state, command)
hardware.set_actuator_postions(state.joint_angles)
```

- 主入口负责串联
- 控制逻辑在 `Controller.run()`

---

# 第 1 讲要顺手指出的问题

- `run_robot.py` 末尾直接调用 `main()`
- 主循环使用忙等
- IMU 可选
- 仿真入口更适合观察状态与调参

---

# 第 1 讲小结

- 先认“项目类型”，再读代码
- 先认入口，再认控制器
- 先认数据对象，再认具体算法

作业：

- 自己画一张控制主链图

---

# 第 2 讲
## 控制器内核、状态机与步态调度

- 重点读 `src/Controller.py`
- 看懂 `BehaviorState`
- 看懂 gait 相位和接触表

---

# `Controller.run()` 在做什么

- 更新行为状态
- 进入 `REST / TROT / HOP / FINISHHOP`
- 在 `TROT` 中进一步调用 `step_gait()`
- 再做姿态补偿和 IK

---

# 行为状态机

- `DEACTIVATED`
- `REST`
- `TROT`
- `HOP`
- `FINISHHOP`

事件：

- `activate_event`
- `trot_event`
- `hop_event`

---

# 三种常见切换规则

- `activate_event`：`DEACTIVATED <-> REST`
- `trot_event`：`REST <-> TROT`
- `hop_event`：`REST -> HOP -> FINISHHOP -> REST`

重点：

- 仿真和实机都复用了这套切换逻辑

---

# `TROT` 分支主链

```flow
step_gait()
  -> 足端目标
  -> 叠加 roll / pitch
  -> IMU 倾斜补偿
  -> inverse kinematics
  -> joint angles
```

---

# `step_gait()` 的本质

- 每条腿单独判断当前相位
- `contact_mode == 1`：走 `StanceController`
- `contact_mode == 0`：走 `SwingController`
- 这就是“腿级混合控制”

---

# 步态时间基准

- `dt = 0.01`
- `overlap_time = 0.10`
- `swing_time = 0.15`

所以：

- `overlap_ticks = 10`
- `swing_ticks = 15`
- `phase_length = 50`

---

# 对角小跑的接触表

```text
FR: 1 1 1 0
FL: 1 0 1 1
BR: 1 0 1 1
BL: 1 1 1 0
```

- `FL + BR` 一组
- `FR + BL` 一组
- 两组交替摆动

---

# `REST / TROT / HOP` 的区别

- `REST`
  - 默认站姿 + 姿态/高度调整
- `TROT`
  - gait + stance/swing + IK
- `HOP`
  - 两组静态足端高度切换

---

# 第 2 讲小结

- 状态机决定模式
- gait 决定哪条腿支撑、哪条腿摆动
- `ticks` 是统一时间基准

作业：

- 自己算一个 gait 周期的 tick 数

---

# 第 3 讲
## 足端规划、Raibert 落脚点与逆运动学

- 重点读 `StanceController`
- 重点读 `SwingController`
- 重点读 `pupper/Kinematics.py`

---

# 控制器内部结构

![](../../imgs/diagram2.jpg)

- gait scheduler
- stance controller
- swing controller
- inverse kinematics

---

# 支撑相在做什么

- 机身想前进
  - 足端相对机身向后划
- 机身想转向
  - 足端相对机身反向旋转
- 机身高度偏差
  - 足端 z 方向缓慢收敛

---

# `StanceController` 的三件事

- `v_xy = -command.horizontal_velocity`
- `delta_R` 由 `yaw_rate * dt` 生成
- `z_time_constant` 拉回目标高度

结论：

- 它本质是“支撑相相对运动学更新器”

---

# `SwingController` 的三件事

- 抬脚
- 朝落脚点移动
- 按时落下

实现特点：

- `z` 走三角波
- `x / y` 匀速逼近目标

---

# Raibert 落脚点

- 速度越大，落脚点越往前
- 转向越大，落脚点越需要旋转补偿

关键参数：

- `alpha`
- `beta`

---

# 为什么它适合教学

- 不是黑盒
- 不是数值优化
- 直觉非常清楚
- 改 `alpha / beta / z_clearance` 很容易看到效果

---

# 四腿逆运动学怎么做

```flow
body-frame feet
  -> 减去每条腿安装原点
  -> 单腿解析逆解
  -> 3x4 关节角矩阵
```

- 解析几何
- 不是数值优化

---

# IK 里最该讲的几何量

- `R_body_foot_yz`
- `R_hip_foot_yz`
- `R_hip_foot`
- `phi / theta / beta`

目的：

- 从足端位置直接求 `abduction / hip / knee`

---

# `TROT` 里的姿态补偿

- 从 IMU 四元数提取 `roll / pitch`
- 先裁剪，再乘补偿系数
- 反向作用到足端目标

理解：

- 轻量闭环补偿
- 不是完整姿态控制器

---

# 第 3 讲小结

- stance 解决“支撑脚怎么划地”
- swing 解决“摆动脚落在哪里”
- IK 解决“脚的位置怎样变成关节角”

作业：

- 解释 `alpha` 变大后会发生什么

---

# 第 4 讲
## MuJoCo 闭环仿真、状态回灌与调参

- 固定机身版学什么
- 浮动机身版学什么
- `sim/sim_robot.py` 为什么是关键桥

---

# 为什么 MuJoCo 是最佳教学入口

- 不依赖真实硬件
- 可重复实验
- 可直接读姿态、速度、触地
- 可做 headless 回归
- 更容易把“闭环”讲清楚

---

# Fixed-base vs Floating-base

- `run_fixed_base.py`
  - 直接写 `qpos`
  - 适合看 IK 与足端轨迹
- `run_floating_base.py`
  - PD 力矩驱动
  - 适合看动力学与反馈

---

# 浮动机身控制流

![](../mujoco_quadruped_mastery_tutorial/assets/floating_base_control_flow.png)

- 任务层
- 控制器
- 执行器桥接
- MuJoCo
- 观测回灌

---

# `sim_robot.py` 的五个桥接模块

- `SimObservationInterface`
- `SimIMU`
- `SimHardwareInterface`
- `SimControlClock`
- `TaskCommandSource`

---

# 状态回灌为什么重要

- 更新 `measured_foot_locations`
- 更新 `measured_joint_angles`
- 更新机身姿态、速度、角速度
- 更新触地估计
- 融合回 `state.foot_locations`

---

# 这是闭环，不是开环

![](../mujoco_quadruped_mastery_tutorial/assets/state_feedback_closed_loop.png)

- 姿态会回写
- 速度会回写
- 接触状态会回写

---

# PD 力矩桥接

- 控制器输出目标关节角
- 仿真执行器需要关节力矩
- `SimHardwareInterface` 把两者连起来

调参直觉：

- `kp` 提高跟踪刚度
- `kd` 提高阻尼

---

# 任务序列语法

```text
mode[:duration][@key=value;key=value...],...
```

例子：

```bash
python sim/run_floating_base.py --duration 8 \
  --task-sequence "rest:1.0,trot:4.0@vx=0.08;z_clearance=0.04,rest"
```

---

# 最推荐的调参顺序

1. `rest`
2. `fixed-base`
3. `floating-base` 小速度
4. `kp / kd / torque-limit`
5. `overlap_time / swing_time / z_clearance`
6. 反馈增益

---

# 第 4 讲小结

- fixed-base 看几何
- floating-base 看闭环
- `sim_robot.py` 是共享控制核心和 MuJoCo 之间的桥

作业：

- 自己设计一条三段任务序列

---

# 第 5 讲
## 实机接口、Sim2Real 与二次开发路线

- 手柄输入怎么进来
- 舵机命令怎么出去
- 仿真与实机到底换了哪些层

---

# 实机控制链

```flow
PS4 手柄
  -> UDP
  -> JoystickInterface
  -> Command
  -> Controller
  -> joint angles
  -> HardwareInterface
  -> pigpio PWM
  -> servos
```

---

# `JoystickInterface` 的价值

- 连续量映射
- 离散按钮边沿触发
- pitch 死区 + 滤波
- height / roll 的积分式调整

结论：

- 输入层负责命令整形

---

# `HardwareInterface` 的价值

- 管 `pigpio`
- 管 PWM 引脚与频率
- 关节角 -> PWM
- 依赖舵机中位和标定参数

---

# 为什么一定要讲标定

- 模型零位 ≠ 机械零位
- 左右腿方向不一致
- `servo_multipliers` 很关键
- `ServoCalibration` 决定实机是否能站稳

---

# IMU 与轻量闭环

- IMU 可选
- 但原始实机入口已预留姿态反馈
- 说明项目不是纯几何开环
- 是一个非常好的入门闭环示例

---

# 从仿真到实机

![](../mujoco_quadruped_mastery_tutorial/assets/sim_to_real_migration.png)

- 共享：`Controller`、gait、stance、swing、IK
- 替换：命令源、执行器、观测接口

---

# 最值得做的工程清理

- 给 `run_robot.py` 增加 `__main__` 保护
- 改善主循环定时
- 统一日志
- 明确拆分 command / hardware / observation interface

---

# 最适合学生继续做的方向

- 新步态表
- 新摆腿轨迹
- 更强姿态反馈
- 更多实时曲线
- `sim -> real` 参数迁移记录

---

# 整套课的最终目标

- 不是背术语
- 是真正讲清主链
- 是能跑通仿真
- 是知道如何进入实机和扩展

---

# 推荐阅读顺序

```text
README.md
-> sim/run_floating_base.py
-> run_robot.py
-> src/Controller.py
-> src/Gaits.py
-> src/StanceController.py
-> src/SwingLegController.py
-> pupper/Kinematics.py
-> sim/sim_robot.py
-> pupper/HardwareInterface.py
```

---

# 收尾页

- 第 1 讲：建立地图
- 第 2 讲：看懂控制器
- 第 3 讲：看懂足端与 IK
- 第 4 讲：看懂仿真闭环
- 第 5 讲：看懂实机与扩展

谢谢观看，建议配合源码边看边跑。
