---
marp: true
paginate: true
theme: default
size: 16:9
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
