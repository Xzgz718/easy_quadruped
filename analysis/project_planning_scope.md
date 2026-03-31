# 本项目到底规划了什么 / 没规划什么

## 一句话结论

这个项目不是完整的优化式步态规划器，也不是工业级全身控制栈。  
它更准确的定位是：

**接触时序 + 脚端参考生成 + 逆运动学 + 关节 PD 跟踪** 的教学/原型控制框架。

---

## 对照表

| 层级 | 本项目已经规划了什么 | 主要代码位置 | 本项目没规划什么 | 后续可优化的方向 |
|---|---|---|---|---|
| 行为状态层 | 通过 `activate_event / trot_event / hop_event` 做离散状态切换，状态包括 `DEACTIVATED / REST / TROT / HOP / FINISHHOP` | `src/Controller.py` `src/Command.py` `src/State.py` | 没有更高层任务规划、恢复策略、失效保护状态机 | 增加更完整的任务状态机、故障恢复、急停与安全状态 |
| 步态时序层 | 通过 `contact_phases`、`phase_ticks`、`ticks` 定义 trot 的接触时序和相位推进 | `pupper/Config.py` `src/Gaits.py` | 没有在线 gait selection，没有根据速度/地形自动切换 walk/trot/bound 等 | 增加速度分段 gait 切换、在线 phase/duty factor 调度 |
| 支撑腿参考生成层 | 支撑腿按 `vx / vy / yaw_rate / height` 在 body 坐标系下做脚端增量更新 | `src/StanceController.py` | 没有基于质心动力学、地面反力、接触约束的 stance 规划 | 换成基于 COM/MPC/WBC/QP 的支撑相控制，显式考虑力分配和稳定性 |
| 摆动腿参考生成层 | 摆动腿使用 Raibert 启发式定落脚点，用三角波 `z_clearance` 生成摆腿高度，再按剩余时间逼近 touchdown | `src/SwingLegController.py` | 没有地形感知、障碍跨越、平滑样条轨迹、触地时序自适应 | 增加样条/Bezier 摆腿轨迹、地形高度图、自适应 touchdown、触地检测重规划 |
| 机身姿态参考层 | 在 trot 中叠加 `command.roll / pitch`，再做基于 IMU 的倾斜补偿；仿真中还有一个额外的姿态/速度反馈修正层 | `src/Controller.py` `sim/run_floating_base.py` | 没有显式的机身姿态轨迹规划，没有统一的姿态误差跟踪器 | 增加 `roll_des / pitch_des / yaw_des` 轨迹层，统一做姿态误差反馈而不是固定压到 0 |
| 速度参考层 | `command.horizontal_velocity` 和 `yaw_rate` 作为脚端规划的参考输入；仿真里额外用 `body_velocity` 做了一层简单速度反馈 | `src/StanceController.py` `src/SwingLegController.py` `sim/run_floating_base.py` | 没有严格的速度闭环跟踪器，没有速度工况下的参数自适应 | 增加速度控制外环、增益调度、不同速度区间的参数表或在线插值 |
| 高度参考层 | 用 `command.height` 和 `state.height` 作为站高参考，支撑腿通过一阶收敛项调整 z | `src/StanceController.py` `src/Controller.py` | 没有显式的机身高度轨迹规划，没有垂向动力学控制 | 增加机身高度轨迹、垂向速度/加速度约束、起伏地形的高度补偿 |
| 逆运动学层 | 已有足端位置到 12 个关节角的解析 IK | `pupper/Kinematics.py` | 没有考虑关节极限优化、奇异性规避、冗余优化 | 增加带约束 IK、奇异性检测、关节限位与优先级优化 |
| 低层执行层 | 用关节位置 PD 计算力矩，MuJoCo 每个子步执行一次 PD + `mj_step` | `sim/sim_robot.py` | 没有电机模型辨识、力矩前馈、关节级轨迹规划器 | 增加电机模型、前馈补偿、关节空间轨迹整形、真实执行器约束 |
| 状态估计层 | 已读取 IMU、关节、足端、接触力等观测，仿真里做了简单状态同步和脚端混合 | `sim/sim_robot.py` | 没有工业级状态估计，没有 COM/接触状态/外力估计 | 增加 EKF/UKF、接触状态估计、机身速度估计、外力扰动观测 |
| 参数管理层 | 主要靠固定配置参数，仿真里可按 task step 对部分参数做插值过渡 | `pupper/Config.py` `sim/task_scheduler.py` `sim/sim_robot.py` | 没有系统辨识后的查表，没有在线参数优化 | 增加速度-步态参数查表、参数插值、自动调参、贝叶斯优化/网格搜索 |
| 地形与环境适应层 | 默认假设平地，接触主要交给仿真器/物理世界处理 | `sim/run_floating_base.py` `sim/sim_robot.py` | 没有地形建模、落脚可行域、摩擦锥约束、滑移补偿 | 增加 terrain-aware foothold planner、摩擦约束、滑移检测与补偿 |

---

## 最值得优先优化的 6 个方向

1. **速度分段参数调度**
   
   当前 `overlap_time / swing_time / z_clearance / alpha / beta` 基本是固定值。  
   更实用的做法是按 `vx`、`yaw_rate` 建查表或插值曲线，让低速和高速使用不同步态参数。

2. **把姿态反馈改成“误差反馈”**
   
   现在仿真里的姿态修正更像“把机身压回水平”。  
   更合理的写法是显式定义 `roll_des / pitch_des`，再对 `姿态误差 = 期望 - 实际` 做控制。

3. **把支撑相从几何推进升级为动力学控制**
   
   现在 `StanceController` 本质还是几何型参考生成。  
   如果想明显提升动态性能，下一步通常是 WBC/QP/MPC 或至少显式的力分配层。

4. **把摆腿轨迹从三角波升级为平滑轨迹**
   
   当前摆腿高度轨迹简单直观，但不够平滑。  
   可以升级为三次样条、五次多项式或 Bezier 曲线，并加入 touchdown 时速度约束。

5. **增强状态估计**
   
   现在的结构足够仿真和教学，但离实机稳定运行还差更强的状态估计。  
   尤其是机身速度、接触状态、滑移和外力扰动的估计。

6. **增加地形和触地自适应**
   
   当前更适合平地。  
   若要上台阶、越障、碎石地或不平路面，需要把“地形高度”和“实时触地事件”引入 swing/stance 规划。

---

## 如果按工程路线继续演进，通常会是这个顺序

1. 先做速度分段参数表和插值调度
2. 再做姿态误差反馈和更稳定的速度外环
3. 再升级摆腿轨迹和平滑 touchdown
4. 然后引入更可靠的状态估计
5. 最后再把 stance 控制升级到动力学层

---

## 最后一句判断

如果只看当前代码，这个项目**已经有步态参考生成**，但**没有完整的优化式步态规划与全身控制**。  
所以把它理解成：

**“基于规则的 gait/reference generator + IK + PD tracking”**

会比简单说“只有跟踪、没有规划”更准确。
