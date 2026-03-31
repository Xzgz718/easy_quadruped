---
marp: true
paginate: true
theme: default
size: 16:9
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
