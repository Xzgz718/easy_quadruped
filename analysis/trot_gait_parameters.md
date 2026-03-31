# Trot 步态规划参数说明

## 1. 先说结论

这个工程里的 `trot` **不是一个单独的配置文件**，而是下面几部分一起决定的：

- **参数定义**：`pupper/Config.py`
- **步态时序**：`src/Gaits.py`
- **摆腿规划**：`src/SwingLegController.py`
- **支撑腿规划**：`src/StanceController.py`
- **总控制入口**：`src/Controller.py`
- **运行时命令输入**：`src/Command.py`
- **真机输入来源**：`src/JoystickInterface.py`
- **仿真覆盖入口**：`sim/run_floating_base.py`、`sim/task_scheduler.py`、`sim/sim_robot.py`

如果你现在主要看的是：

- **真机 `run_robot.py`**：默认使用 `pupper/Config.py` 里的参数
- **MuJoCo 仿真**：会先读取 `pupper/Config.py`，但又会被 `sim/run_floating_base.py` 里的命令行默认值覆盖一部分

---

## 2. 参数到底在哪里

### 2.1 最核心的位置

最主要的 `trot` 参数都在：

- `pupper/Config.py:98`
- `pupper/Config.py:108`
- `pupper/Config.py:122`

`run_robot.py` 里启动后还会直接打印几项关键信息：

- `run_robot.py:36`

打印的是：

- `overlap_time`
- `swing_time`
- `z_clearance`
- `x_shift`

---

## 3. 核心步态参数总结

下面这张表是最重要的。

| 参数 | 真机默认值 | 仿真默认值 | 定义/覆盖位置 | 作用 |
|---|---:|---:|---|---|
| `dt` | `0.01` | `0.01` | `pupper/Config.py:124` | 控制周期，决定每次步态更新的时间间隔 |
| `num_phases` | `4` | `4` | `pupper/Config.py:126` | 一个 gait cycle 分成 4 个相位 |
| `contact_phases` | 固定矩阵 | 固定矩阵 | `pupper/Config.py:128` | 定义每个相位哪些腿着地、哪些腿摆动 |
| `overlap_time` | `0.10` | `0.16` | `pupper/Config.py:131` / `sim/run_floating_base.py:56` | 四脚都在地面的时间 |
| `swing_time` | `0.15` | `0.11` | `pupper/Config.py:135` / `sim/run_floating_base.py:57` | 对角摆腿相位持续时间 |
| `z_clearance` | `0.07` | `0.03` | `pupper/Config.py:112` / `sim/run_floating_base.py:55` | 摆腿抬脚高度 |
| `alpha` | `0.5` | `0.5` | `pupper/Config.py:113` | 决定线速度对目标落脚点的影响强弱 |
| `beta` | `0.5` | `0.5` | `pupper/Config.py:117` | 决定偏航角速度对目标落脚点旋转补偿的强弱 |

> 结论：真正最核心、最常调的，一般就是  
> `overlap_time`、`swing_time`、`z_clearance`、`alpha`、`beta`。

---

## 4. `contact_phases` 到底表示什么

这一部分最容易看错。

`contact_phases` 定义在：

- `pupper/Config.py:128`

源码是：

```python
[[1, 1, 1, 0],
 [1, 0, 1, 1],
 [1, 0, 1, 1],
 [1, 1, 1, 0]]
```

### 4.1 最容易误解的点

很多人第一眼会把它读成：

- 每一行是一个 phase

但这在这份代码里是错的。

真正的读取方式在：

- `src/Gaits.py:81`

代码是按下面这个方式取当前接触状态的：

```python
self.config.contact_phases[:, self.phase_index(ticks)]
```

这说明：

- **行 = 腿**
- **列 = phase**

也就是说，`contact_phases` 是一个 **`4 条腿 × 4 个相位`** 的矩阵。

---

### 4.2 腿的顺序

腿的顺序是：

- `FR` 前右
- `FL` 前左
- `BR` 后右
- `BL` 后左

这个顺序可以从下面看到：

- `sim/build_fixed_base_mjcf.py:7`

---

### 4.3 更直观的矩阵读法

如果按“行是腿、列是相位”来重写，可以读成：

| 腿 / phase | phase 0 | phase 1 | phase 2 | phase 3 |
|---|---:|---:|---:|---:|
| `FR` | 1 | 1 | 1 | 0 |
| `FL` | 1 | 0 | 1 | 1 |
| `BR` | 1 | 0 | 1 | 1 |
| `BL` | 1 | 1 | 1 | 0 |

其中：

- `1` = 支撑 / 着地
- `0` = 摆动 / 离地

---

### 4.4 按 phase 看，实际运行到底是什么步态

真正运行时，要按“列”来读。

所以每个 phase 的接触状态是：

| 相位 | `FR` | `FL` | `BR` | `BL` | 当前形态 |
|---|---:|---:|---:|---:|---|
| phase 0 | 1 | 1 | 1 | 1 | 四脚全着地 |
| phase 1 | 1 | 0 | 0 | 1 | `FL + BR` 摆腿，`FR + BL` 支撑 |
| phase 2 | 1 | 1 | 1 | 1 | 四脚全着地 |
| phase 3 | 0 | 1 | 1 | 0 | `FR + BL` 摆腿，`FL + BR` 支撑 |

如果只把“谁在摆腿”单独拎出来，就是：

| 相位 | 摆腿组合 | 支撑组合 |
|---|---|---|
| phase 0 | 无 | `FR + FL + BR + BL` |
| phase 1 | `FL + BR` | `FR + BL` |
| phase 2 | 无 | `FR + FL + BR + BL` |
| phase 3 | `FR + BL` | `FL + BR` |

---

### 4.5 结论

所以它并不是“单脚 trot”，而是：

**全支撑 -> 一组对角腿摆动 -> 全支撑 -> 另一组对角腿摆动**

也可以叫：

- **带 overlap 的对角 trot**
- **更稳的 trot**

这样设计的直接效果是：

- 相比纯两相对角 trot，更稳定
- 更容易起步和站住
- 但节奏会稍微保守一些

---

## 5. 每个参数是怎么生效的

### 5.1 步态相位是怎么推进的

相位推进逻辑在：

- `src/Gaits.py:10`

这里会根据：

- `phase_length`
- `phase_ticks`
- 当前 `state.ticks`

来判断当前处于哪个相位，以及当前相位已经走了多久。

相关公式在：

- `pupper/Config.py:255`
- `pupper/Config.py:263`
- `pupper/Config.py:271`
- `pupper/Config.py:279`
- `pupper/Config.py:289`

也就是：

- `overlap_ticks = overlap_time / dt`
- `swing_ticks = swing_time / dt`
- `stance_ticks = 2 * overlap_ticks + swing_ticks`
- `phase_ticks = [overlap, swing, overlap, swing]`
- `phase_length = 2 * overlap_ticks + 2 * swing_ticks`

### 5.2 摆腿是怎么规划的

摆腿逻辑在：

- `src/SwingLegController.py:12`

这里做了两件事：

#### (1) 算目标落脚点

公式在：

- `src/SwingLegController.py:16`
- `src/SwingLegController.py:23`

核心思想：

- `alpha` 越大，落脚点会更积极地朝速度方向前伸
- `beta` 越大，落脚点会更积极地补偿转向

#### (2) 算摆腿高度轨迹

在：

- `src/SwingLegController.py:33`

这里使用的是一个简单的三角形高度轨迹：

- 前半段抬脚
- 后半段落脚

抬脚最大高度由 `z_clearance` 决定。

### 5.3 支撑腿是怎么规划的

支撑腿逻辑在：

- `src/StanceController.py:13`

支撑相里脚相对机身会“向后划地”，核心受这些量影响：

- `command.horizontal_velocity`
- `command.yaw_rate`
- `z_time_constant`

其中：

- `z_time_constant` 在 `pupper/Config.py:80`

它控制支撑相里脚端 z 方向向目标高度收敛的快慢。

---

## 6. 会影响 `trot` 的运行时命令参数

这些参数本身不是“步态模板参数”，但会直接影响 `trot` 的实际效果。

定义在：

- `src/Command.py:12`

主要有：

| 参数 | 默认值 | 作用 |
|---|---:|---|
| `horizontal_velocity[0]` | `0` | 前进/后退速度命令 `vx` |
| `horizontal_velocity[1]` | `0` | 横移速度命令 `vy` |
| `yaw_rate` | `0` | 转向角速度命令 |
| `height` | `-0.16` | 机身目标高度 |
| `pitch` | `0` | 机身俯仰命令 |
| `roll` | `0` | 机身横滚命令 |

### 真机时这些命令从哪里来

来自手柄解析：

- `src/JoystickInterface.py:30`

对应关系大致是：

- 左摇杆：`vx` / `vy`
- 右摇杆：`yaw_rate` / `pitch`
- 十字键：`height` / `roll`
- `R1`：切换 `trot`

### 仿真时这些命令从哪里来

来自命令行参数：

- `sim/run_floating_base.py:34`

最常见的是：

- `--x-vel`
- `--y-vel`
- `--yaw-rate`
- `--height`
- `--pitch`
- `--roll`

---

## 7. 真机默认值 和 仿真默认值的区别

这一点很重要。

如果你看到 MuJoCo 里 `trot` 的动作和 `pupper/Config.py` 里的默认参数不完全一样，不是你看错了，而是因为仿真里做了覆盖：

- `sim/run_floating_base.py:73`

覆盖的是这 3 个：

| 参数 | `pupper/Config.py` 默认 | `sim/run_floating_base.py` 默认 |
|---|---:|---:|
| `z_clearance` | `0.07` | `0.03` |
| `overlap_time` | `0.10` | `0.16` |
| `swing_time` | `0.15` | `0.11` |

也就是说：

- **真机默认**：抬脚更高、摆腿更久、全支撑更短
- **仿真默认**：抬脚更低、摆腿更快、全支撑更长

仿真这一套通常会显得更稳一些，也更保守一些。

---

## 8. `run_robot.py` 里实际会用到哪些

`run_robot.py` 的入口在：

- `run_robot.py:11`

它做的事情很直接：

1. `config = Configuration()`
2. 创建 `Controller(config, ...)`
3. 通过 `JoystickInterface(config)` 读手柄命令
4. 调 `controller.run(state, command)`

所以：

- 你改 `pupper/Config.py`，真机 `run_robot.py` 会直接受影响
- `run_robot.py` 本身没有单独再定义一套 `trot` 参数

---

## 9. 如果你要调 `trot`，最常改哪些

### 最推荐优先调的 5 个

| 参数 | 建议先调它的原因 |
|---|---|
| `z_clearance` | 最直观，直接影响抬脚高低和绊脚风险 |
| `overlap_time` | 最直观，直接影响稳定性 |
| `swing_time` | 最直观，直接影响步频和动作快慢 |
| `alpha` | 直接影响前进时落脚点是否够“积极” |
| `beta` | 直接影响转向时是否跟得上 |

### 调大 / 调小的一般效果

| 参数 | 调大 | 调小 |
|---|---|---|
| `z_clearance` | 抬脚更高，更不容易蹭地，但动作更大 | 动作更省，但容易拖脚 |
| `overlap_time` | 更稳、更保守 | 更灵活，但更容易不稳 |
| `swing_time` | 摆腿更慢，更稳 | 摆腿更快，步频更高 |
| `alpha` | 落脚更靠前/更积极 | 落脚更保守，可能跟不上速度 |
| `beta` | 转向补偿更强 | 转向补偿更弱 |

---

## 10. 哪些参数现在不能直接从仿真命令行改

在当前代码里，`task-sequence` 和仿真命令行直接支持的 gait 参数主要是：

- `z_clearance`
- `overlap_time`
- `swing_time`

见：

- `sim/task_scheduler.py:7`
- `sim/sim_robot.py:277`
- `sim/README.md:136`

而这些参数**目前不能直接从仿真 CLI 改**，只能改源码：

- `alpha`
- `beta`
- `delta_x`
- `delta_y`
- `x_shift`
- `z_time_constant`
- `contact_phases`

也就是说，如果你想改“落脚点前后补偿更强/更弱”，需要直接改：

- `pupper/Config.py:113`
- `pupper/Config.py:117`

---

## 11. 如果只想快速找到源码，按这个顺序看

建议你按下面顺序读代码：

1. `run_robot.py:16`  
   看控制器和配置从哪里创建
2. `pupper/Config.py:98`  
   看默认参数定义
3. `src/Controller.py:99`  
   看 `TROT` 状态下总流程
4. `src/Gaits.py:10`  
   看相位切换
5. `src/SwingLegController.py:12`  
   看摆腿落脚点和抬脚高度
6. `src/StanceController.py:13`  
   看支撑腿推进

---

## 12. 一句话总结

这个工程里的 `trot` 步态规划，最核心可以记成下面这句话：

**用 `contact_phases + overlap_time + swing_time` 决定“什么时候哪条腿摆动”，  
再用 `z_clearance + alpha + beta + default_stance` 决定“脚摆到哪里、落在哪里”。**

如果你现在只是想知道“改哪里最有效”，优先看：

- `pupper/Config.py:112`
- `pupper/Config.py:113`
- `pupper/Config.py:117`
- `pupper/Config.py:131`
- `pupper/Config.py:135`
