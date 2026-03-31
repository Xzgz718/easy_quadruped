# Stanford Quadruped Fork

基于 Stanford Student Robotics 的 `StanfordQuadruped` 项目做的二次开发版本，当前公开快照主要聚焦在控制器核心、运动学与 MuJoCo 仿真链路，而不是上游仓库的完整镜像。

原始项目：
https://github.com/stanfordroboticsclub/StanfordQuadruped

说明：

- 本仓库是独立维护的 fork / derivative work。
- 本仓库不是 Stanford Student Robotics 的官方发布版本。
- `StanfordQuadruped` 这一名称在这里仅用于说明上游来源与兼容背景，不代表官方背书。

## 当前公开快照包含什么

- `src/`
  - 步态调度、支撑相控制、摆腿控制、状态机与命令结构。
- `pupper/`
  - 机器人配置、逆运动学、舵机标定参数以及硬件接口抽象。
- `sim/`
  - MuJoCo 模型生成脚本、浮动机身闭环仿真、观测/执行器适配层、任务调度器。
- `calibrate_servos.py`
  - 面向实机的舵机零位标定脚本。

## 这个公开版刻意没有带上的内容

- 本地编辑器配置、日志、缓存文件。
- 一次性分析材料、课件导出物、个人工作草稿。
- 上游仓库里与当前公开目标不直接相关的部署残留文件。

这样做是为了让公开仓库更聚焦，也避免把明显的本地环境痕迹一起推上去。

## 快速开始

建议在仓库根目录执行。

最少依赖：

```bash
pip install mujoco transforms3d numpy
```

生成浮动机身 MuJoCo XML：

```bash
python -m sim.build_floating_base_mjcf
```

运行浮动机身闭环仿真：

```bash
python sim/run_floating_base.py --mode trot --duration 20
```

无界面快速跑一个任务序列：

```bash
python sim/run_floating_base.py --headless --duration 8 --task-sequence "rest:1.0,trot:4.0,rest"
```

更详细的仿真用法见 `sim/README.md`。

## 仓库结构

- `src/Controller.py`
  - 主控制器，整合步态、足端轨迹与逆运动学调用。
- `pupper/Config.py`
  - 控制参数、几何尺寸、舵机与仿真配置。
- `sim/run_floating_base.py`
  - 当前公开快照的主要仿真入口。
- `sim/sim_robot.py`
  - MuJoCo 与控制器状态结构之间的桥接层。
- `sim/task_scheduler.py`
  - 高层任务序列和参数过渡逻辑。

## 许可证与声明

上游项目采用 MIT 许可证，本仓库保留了原始许可证文本与版权声明，见 `LICENSE`。

本仓库中的二次开发部分，除非某个文件或目录另有声明，也按 MIT 许可证公开。更完整的来源说明和非官方声明见 `NOTICE`。

