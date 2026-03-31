---
marp: true
paginate: true
theme: default
size: 16:9
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
