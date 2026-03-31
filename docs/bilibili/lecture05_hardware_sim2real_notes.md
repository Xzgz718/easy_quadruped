# StanfordQuadruped 第 5 讲讲义：实机接口、Sim2Real 与二次开发路线

这份讲义对应系列课程的第 5 讲，目标是把实机链路、仿真到实机的边界，以及后续扩展路线讲清楚，让整套课程形成真正可落地的收尾。

建议时长：35~45 分钟

主文件：

- `src/JoystickInterface.py`
- `pupper/HardwareInterface.py`
- `src/IMU.py`
- `install.sh`
- `run_robot.py`

## 本讲目标

- 讲清楚实机运行链里哪些部分和仿真不同
- 看懂 `JoystickInterface`、`HardwareInterface`、IMU、部署脚本的角色
- 给出从仿真迁移到实机的注意事项
- 说明这个项目接下来该怎么扩展，而不是只停留在“能跑”

## 实机链路怎么讲最清楚

建议直接讲成下面这条路径：

```flow
PS4 手柄
  -> UDP 消息
  -> JoystickInterface
  -> Command
  -> Controller
  -> joint angles
  -> HardwareInterface
  -> pigpio PWM
  -> 舵机
```

## `JoystickInterface.py` 的重点

- 订阅 UDP 手柄消息
- 把摇杆映射成 `horizontal_velocity / yaw_rate / pitch / height / roll`
- 把 `L1 / R1 / X` 做成边沿触发事件
- 对 `pitch` 做死区和一阶限速滤波
- 对 `height / roll` 做基于当前状态的积分式调节

这里很适合顺手讲一个工程观念：

> 好的输入层不是“原样转发手柄值”，而是先完成命令整形，再交给控制器。

## `HardwareInterface.py` 的重点

- 建立和本机 `pigpio` 守护进程的连接
- 维护 PWM 引脚、频率和范围
- 通过中立位姿和方向符号把关节角映射到舵机 PWM

这部分要强调：

- 数学模型里的关节零位，不等于真实舵机的机械零位
- 所以必须有 `ServoCalibration`
- `servo_multipliers` 用来处理不同腿、不同关节的转向差异

## IMU 与闭环补偿

`run_robot.py` 里 IMU 是可选的，但它很有教学价值，因为它说明：

- 这个项目原始设计就预留了姿态反馈入口
- 即便不是复杂状态估计器，也已经不是纯开环结构

所以第 5 讲可以把它讲成：

- 一个最小但真实存在的闭环接口
- 一个从“纯几何 gait”向“轻量姿态反馈 gait”迈出的第一步

## 安装与部署要怎么讲

`install.sh` 展示了实机版所依赖的外部世界：

- `numpy / transforms3d / pigpio / pyserial`
- `PupperCommand`
- `PS4Joystick`
- `robot.service`

这部分很适合拿来告诉观众：

- 仓库不是孤立运行的
- 实机机器人一定伴随驱动、服务、外部进程和系统级依赖

## 从仿真到实机时最容易踩的坑

- 舵机中位和机械装配偏差
- 仿真里稳定的 `kp / kd` 到真实舵机上不一定等价
- 地面摩擦、足端接触、机身重量分布会发生变化
- 手柄输入是异步网络消息，和仿真里的本地任务源不同

![从仿真到实机：共享控制核心，替换命令源、执行器与观测后端](../mujoco_quadruped_mastery_tutorial/assets/sim_to_real_migration.png)

## 第 5 讲必须给出的扩展路线

如果希望观众看完后真的能继续做项目，建议明确给出下面 5 个方向：

1. 先做工程清理
   - 给 `run_robot.py` 增加 `if __name__ == "__main__"`
   - 把忙等循环改成更稳定的定时方式
2. 再做日志和观测
   - 为 `Command`、`State`、触地和机身姿态加统一日志
3. 再做控制改造
   - 替换摆腿轨迹
   - 增加新的步态表
   - 增强姿态反馈
4. 再做平台抽象
   - 更明确地拆分 command source / hardware interface / observation interface
5. 最后再上更复杂的方法
   - 阻抗、力控制、WBC、MPC、学习策略

## 这一讲最适合布置的结课项目

- 项目 1：自己加一种新的任务序列和回归脚本
- 项目 2：把摆动相轨迹从三角波改成更平滑的曲线
- 项目 3：在仿真里增加更多实时可视化量
- 项目 4：做一次 `sim -> real` 参数迁移记录
- 项目 5：把控制器主循环重构成更可测试的形式

## 本讲建议演示

如果在实机环境下，可以演示：

```bash
python run_robot.py
```

如果没有实机，建议用第 4 讲仿真收尾，并口头说明：

- 哪些模块是共享的
- 哪些模块到实机必须替换

## 本讲作业

- 让观众自己总结“共享控制核心”和“平台相关后端”的边界
- 让观众提出一个最想扩展的方向，并说明会改哪些文件
- 让观众解释：为什么这个项目特别适合作为课程/毕设底座
