---
marp: true
paginate: true
theme: default
size: 16:9
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
