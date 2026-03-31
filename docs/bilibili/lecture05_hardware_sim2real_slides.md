---
marp: true
paginate: true
theme: default
size: 16:9
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
