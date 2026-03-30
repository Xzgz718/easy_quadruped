from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "mujoco_quadruped_mastery_tutorial" / "assets"
FONT_PATH = Path("/home/tangp/.local/share/fonts/wqy/wqy-microhei.ttc")

W = 1800
H = 1100
BG = "#F7F8FB"
TEXT = "#18212F"
MUTED = "#526074"
LINE = "#6D7B90"
PANEL = "#FFFFFF"
SHADOW = "#D9E0EA"
BLUE = "#D9EFFF"
GREEN = "#DDF7E7"
ORANGE = "#FFEBD7"
PURPLE = "#EEE5FF"
RED = "#FFE0E0"
YELLOW = "#FFF6CC"


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    return image, draw


def shadowed_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    radius: int = 28,
    outline: str = "#D8DEE8",
    shadow_offset: int = 8,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(
        (x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset),
        radius=radius,
        fill=SHADOW,
    )
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: str = LINE,
    width: int = 8,
    head: int = 18,
) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    left = (
        x2 - head * math.cos(angle) + head * 0.6 * math.sin(angle),
        y2 - head * math.sin(angle) - head * 0.6 * math.cos(angle),
    )
    right = (
        x2 - head * math.cos(angle) - head * 0.6 * math.sin(angle),
        y2 - head * math.sin(angle) + head * 0.6 * math.cos(angle),
    )
    draw.polygon([end, left, right], fill=fill)


def multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font_obj: ImageFont.FreeTypeFont,
    fill: str = TEXT,
    spacing: int = 8,
    anchor: str | None = None,
) -> None:
    draw.multiline_text(xy, text, font=font_obj, fill=fill, spacing=spacing, anchor=anchor)


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int = 24, fill: str = MUTED) -> None:
    draw.text(xy, text, font=font(size), fill=fill)


def title(draw: ImageDraw.ImageDraw, main: str, sub: str) -> None:
    multiline(draw, (90, 60), main, font(48), TEXT, spacing=10)
    multiline(draw, (92, 130), sub, font(24), MUTED, spacing=8)


def bullet_text(lines: list[str]) -> str:
    return "\n".join(f"• {line}" for line in lines)


def project_structure_map() -> Path:
    image, draw = new_canvas()
    title(draw, "StanfordQuadruped 项目结构图", "从 MuJoCo 学习入口出发，把整个仓库按职责分成 4 层")

    boxes = [
        ((120, 220, 1680, 390), BLUE, "入口层", ["run_robot.py", "sim/run_fixed_base.py", "sim/run_floating_base.py"], "负责把输入、状态、控制器和执行后端串起来"),
        ((120, 430, 1680, 620), GREEN, "控制层", ["src/Command.py", "src/State.py", "src/Controller.py", "src/Gaits.py", "src/StanceController.py", "src/SwingLegController.py"], "负责 gait、足端轨迹、状态机与 joint target"),
        ((120, 660, 1680, 840), ORANGE, "模型与硬件层", ["pupper/Config.py", "pupper/Kinematics.py", "pupper/HardwareInterface.py", "src/IMU.py"], "负责几何参数、IK、IMU、PWM 与实机接口"),
        ((120, 880, 1680, 1040), PURPLE, "仿真桥接层", ["sim/build_fixed_base_mjcf.py", "sim/build_floating_base_mjcf.py", "MuJoCo model / data / sensors / actuators"], "负责把原始项目接到 MuJoCo 动力学和可视化环境"),
    ]

    for box, color, header, items, note in boxes:
        shadowed_box(draw, box, color)
        x1, y1, x2, y2 = box
        multiline(draw, (x1 + 35, y1 + 24), header, font(34), TEXT)
        multiline(draw, (x1 + 40, y1 + 78), bullet_text(items), font(24), TEXT, spacing=10)
        multiline(draw, (x2 - 520, y1 + 44), note, font(24), MUTED, spacing=10)

    arrow(draw, (900, 390), (900, 430))
    arrow(draw, (900, 620), (900, 660))
    arrow(draw, (900, 840), (900, 880))

    out = ASSET_DIR / "project_structure_map.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def entrypoints_map() -> Path:
    image, draw = new_canvas()
    title(draw, "三个入口与学习路径图", "先学 fixed-base 运动学，再学 floating-base 闭环，再对照原始实机入口")

    core_box = (350, 760, 1450, 1000)
    shadowed_box(draw, core_box, GREEN)
    multiline(draw, (390, 805), "共享控制核心", font(36), TEXT)
    multiline(
        draw,
        (390, 865),
        "Controller.run()  ->  Gaits  ->  Stance / Swing  ->  IK  ->  joint_angles\nConfiguration / Command / State 为整套系统提供统一语义",
        font(28),
        TEXT,
        spacing=12,
    )

    top_boxes = [
        ((90, 240, 530, 640), ORANGE, "run_robot.py", ["手柄输入", "IMU 四元数", "PWM 舵机输出"], "最接近原始实机"),
        ((680, 240, 1120, 640), BLUE, "sim/run_fixed_base.py", ["固定机身", "直接写 qpos", "最适合学 gait + IK"], "先把运动学链跑通"),
        ((1270, 190, 1710, 690), PURPLE, "sim/run_floating_base.py", ["浮动机身", "关节/足端/姿态回灌", "PD torque + viewer + plots"], "当前最完整的学习入口"),
    ]

    for box, color, header, items, note in top_boxes:
        shadowed_box(draw, box, color)
        x1, y1, x2, y2 = box
        multiline(draw, (x1 + 28, y1 + 28), header, font(34), TEXT)
        multiline(draw, (x1 + 32, y1 + 95), bullet_text(items), font(24), TEXT, spacing=10)
        multiline(draw, (x1 + 32, y2 - 95), note, font(24), MUTED)
        arrow(draw, ((x1 + x2) // 2, y2), ((core_box[0] + core_box[2]) // 2 if header == "sim/run_fixed_base.py" else (x1 + x2) // 2, core_box[1]))

    arrow(draw, (1120, 440), (1270, 440), fill="#325A9B", width=10, head=22)
    label(draw, (1135, 395), "先学运动学", 22, "#325A9B")
    label(draw, (1320, 395), "再学动力学闭环", 22, "#325A9B")
    arrow(draw, (530, 360), (680, 360), fill="#A36B1B", width=8, head=20)
    label(draw, (550, 315), "对照实机接口", 22, "#A36B1B")

    out = ASSET_DIR / "entrypoints_learning_path.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def floating_control_flow() -> Path:
    image, draw = new_canvas()
    title(draw, "run_floating_base 控制流图", "主循环把 Controller、MuJoCo 传感器和 PD 力矩执行器连成一个最小闭环")

    boxes = {
        "sync": (80, 340, 430, 520),
        "cmd": (510, 340, 830, 520),
        "fb": (910, 340, 1220, 520),
        "ctrl": (1300, 300, 1710, 560),
        "qdes": (1310, 630, 1700, 790),
        "tau": (870, 630, 1220, 790),
        "mj": (430, 630, 800, 790),
        "obs": (80, 630, 350, 790),
    }
    styles = {
        "sync": (BLUE, "sync_state_from_sim()", ["读取关节/足端/IMU/接触", "写回 State", "stance 强回灌 / swing 弱回灌"]),
        "cmd": (ORANGE, "make_command()", ["根据 mode 构造 Command", "设定 x_vel / yaw / height", "首拍可打 trot_event"]),
        "fb": (YELLOW, "apply_feedback()", ["姿态反馈修正 roll/pitch", "速度反馈修正 vx", "不改原始 Controller 结构"]),
        "ctrl": (GREEN, "Controller.run()", ["状态机切换", "gait -> stance/swing", "IK 输出 joint_angles"]),
        "qdes": (PURPLE, "joint_target_array()", ["把 3x4 关节角整理成 MuJoCo 顺序", "准备 target_qpos"]),
        "tau": (RED, "compute_pd_torques()", ["tau = kp(qdes-q)+kd(0-dq)", "限幅到 torque_limit"]),
        "mj": (BLUE, "mujoco.mj_step()", ["推进动力学", "更新 contact / body motion"]),
        "obs": (ORANGE, "viewer / telemetry / plots", ["输出 xyz / rpy / touch", "显示 pitch / vx / contacts"]),
    }

    for key, box in boxes.items():
        color, header, lines = styles[key]
        shadowed_box(draw, box, color)
        x1, y1, _, _ = box
        multiline(draw, (x1 + 22, y1 + 22), header, font(28), TEXT)
        multiline(draw, (x1 + 22, y1 + 78), bullet_text(lines), font(20), TEXT, spacing=8)

    arrow(draw, (430, 430), (510, 430))
    arrow(draw, (830, 430), (910, 430))
    arrow(draw, (1220, 430), (1300, 430))
    arrow(draw, (1505, 560), (1505, 630))
    arrow(draw, (1310, 710), (1220, 710))
    arrow(draw, (870, 710), (800, 710))
    arrow(draw, (430, 710), (350, 710))

    draw.line((180, 630, 180, 585, 255, 585, 255, 520), fill="#325A9B", width=8)
    arrow(draw, (255, 520), (255, 520), fill="#325A9B", width=8, head=1)
    arrow(draw, (255, 585), (255, 520), fill="#325A9B", width=8, head=18)
    label(draw, (90, 560), "MuJoCo 传感器形成反馈闭环", 22, "#325A9B")

    out = ASSET_DIR / "floating_base_control_flow.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def tuning_flow() -> Path:
    image, draw = new_canvas()
    title(draw, "调参与排障流程图", "先判断主要现象，再按最短路径改关键参数，而不是所有旋钮一起拧")

    start = (620, 190, 1180, 330)
    shadowed_box(draw, start, BLUE)
    multiline(draw, (670, 228), "先判断主要现象", font(40), TEXT)

    symptom_boxes = [
        ((80, 430, 540, 650), ORANGE, "现象 A：点头 / 前仰后仰", ["x_vel ↓", "overlap_time ↑", "stance_state_blend ↑", "kd ↑"]),
        ((670, 430, 1130, 650), GREEN, "现象 B：拖腿 / 抬脚不够", ["z_clearance ↑", "swing_time ↑", "kp ↑", "x_vel ↓"]),
        ((1260, 430, 1720, 650), PURPLE, "现象 C：速度上不去", ["velocity_kp ↑", "kp/kd 微调", "观察 Forward Vx", "检查 contact 时序"]),
        ((230, 760, 690, 980), RED, "现象 D：起步就炸 / NaN", ["--rebuild", "先跑 rest", "kp ↓", "检查 base-z / 初始姿态"]),
        ((1110, 760, 1570, 980), YELLOW, "现象 E：viewer / plots 卡住", ["先用 --no-plots", "plot_update_interval ↑", "分离控制问题与绘图问题", "必要时杀挂起进程"]),
    ]

    for box, color, header, items in symptom_boxes:
        shadowed_box(draw, box, color)
        x1, y1, _, _ = box
        multiline(draw, (x1 + 24, y1 + 24), header, font(28), TEXT)
        multiline(draw, (x1 + 30, y1 + 86), bullet_text(items), font(24), TEXT, spacing=10)

    arrow(draw, (720, 330), (320, 430))
    arrow(draw, (900, 330), (900, 430))
    arrow(draw, (1080, 330), (1490, 430))
    arrow(draw, (520, 650), (460, 760))
    arrow(draw, (1280, 650), (1340, 760))

    note = (760, 790, 1040, 955)
    shadowed_box(draw, note, PANEL)
    multiline(draw, (790, 820), "最高优先级调参顺序", font(28), TEXT)
    multiline(draw, (790, 875), "先 gait 时序\n再 kp / kd\n再 state blend\n最后姿态/速度反馈", font(24), MUTED, spacing=10)

    out = ASSET_DIR / "tuning_troubleshooting_flow.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def feedback_closed_loop() -> Path:
    image, draw = new_canvas()
    title(draw, "状态反馈闭环图", "MuJoCo 版入口不是纯开环：实测状态会重新进入 State 和 Command，形成双层反馈")

    boxes = [
        ((90, 250, 430, 420), BLUE, "MuJoCo Sensors", ["joint pos / vel", "foot pos / touch", "imu quat / gyro / vel"]),
        ((530, 220, 920, 470), GREEN, "sync_state_from_sim()", ["measured_* 写回 State", "joint_angles / velocities 更新", "stance 强回灌, swing 弱回灌"]),
        ((1040, 240, 1380, 410), YELLOW, "apply_feedback()", ["roll / pitch / gyro -> 姿态修正", "vx 误差 -> 速度修正"]),
        ((1460, 230, 1710, 430), ORANGE, "Command", ["x_vel / yaw / height", "pitch / roll", "trot_event"]),
        ((1130, 560, 1710, 810), PURPLE, "Controller + IK", ["根据 State + Command 生成 gait", "得到 foot_locations / joint_angles", "输出给低层执行器"]),
        ((720, 610, 1020, 780), RED, "PD Torque", ["target_qpos -> tau", "kp / kd / torque_limit"]),
        ((310, 590, 620, 800), BLUE, "MuJoCo Dynamics", ["mj_step()", "自由机身 + 接触", "产生真实 body motion"]),
    ]

    for box, color, header, items in boxes:
        shadowed_box(draw, box, color)
        x1, y1, _, _ = box
        multiline(draw, (x1 + 22, y1 + 22), header, font(30), TEXT)
        multiline(draw, (x1 + 24, y1 + 78), bullet_text(items), font(22), TEXT, spacing=10)

    arrow(draw, (430, 335), (530, 335), fill="#2E6EAF", width=9, head=20)
    arrow(draw, (920, 335), (1040, 325), fill="#6D7B90", width=8, head=18)
    arrow(draw, (1380, 325), (1460, 325), fill="#B48A12", width=8, head=18)
    arrow(draw, (1585, 430), (1585, 560), fill="#6A56A5", width=9, head=20)
    arrow(draw, (1130, 685), (1020, 695), fill="#A94A4A", width=9, head=20)
    arrow(draw, (720, 695), (620, 695), fill="#A94A4A", width=9, head=20)

    draw.line((430, 800, 430, 860, 260, 860, 260, 420), fill="#2E6EAF", width=8)
    arrow(draw, (260, 420), (260, 420), fill="#2E6EAF", width=8, head=1)
    arrow(draw, (260, 430), (260, 420), fill="#2E6EAF", width=8, head=18)
    label(draw, (105, 880), "外环：MuJoCo 测得状态 -> State 回灌 -> Controller", 24, "#2E6EAF")

    draw.line((1220, 240, 1220, 150, 760, 150, 760, 220), fill="#9D840C", width=8)
    arrow(draw, (760, 220), (760, 220), fill="#9D840C", width=8, head=1)
    arrow(draw, (760, 215), (760, 220), fill="#9D840C", width=8, head=18)
    label(draw, (930, 110), "内环：姿态 / 速度误差 -> Command 修正", 24, "#9D840C")

    out = ASSET_DIR / "state_feedback_closed_loop.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def experiment_roadmap() -> Path:
    image, draw = new_canvas()
    title(draw, "实验路线图", "从零开始最稳的顺序：先几何，后动力学，再反馈，再做自己的扩展")

    stages = [
        ("阶段 1", "Fixed-base / REST", ["确认 IK 与站姿", "看关节方向对不对", "先不引入动力学"], BLUE),
        ("阶段 2", "Fixed-base / TROT", ["观察 gait phase", "调 x_vel / z_clearance", "只学运动学轨迹"], GREEN),
        ("阶段 3", "Floating-base / REST", ["确认起始姿态稳定", "检查 base-z 与接触", "避免一开始炸"], ORANGE),
        ("阶段 4", "Floating-base / TROT", ["先 headless 回归", "再 viewer 观察", "记录 delta xyz / max pitch"], PURPLE),
        ("阶段 5", "反馈与调参", ["调 state blend", "调 kp / kd", "调 attitude_kp / velocity_kp"], YELLOW),
        ("阶段 6", "自己的扩展", ["加 plots / CSV", "换低层控制器", "做更像真机的版本"], RED),
    ]

    x_positions = [80, 360, 640, 920, 1200, 1480]
    y1, y2 = 300, 780

    for index, ((tag, header, items, color), x1) in enumerate(zip(stages, x_positions)):
        box = (x1, y1, x1 + 240, y2)
        shadowed_box(draw, box, color)
        multiline(draw, (x1 + 26, y1 + 22), tag, font(24), MUTED)
        multiline(draw, (x1 + 22, y1 + 60), header, font(31), TEXT, spacing=10)
        multiline(draw, (x1 + 24, y1 + 150), bullet_text(items), font(21), TEXT, spacing=10)
        if index < len(stages) - 1:
            arrow(draw, (x1 + 240, 540), (x_positions[index + 1], 540), fill="#5C6B80", width=8, head=18)

    note = (340, 860, 1460, 1020)
    shadowed_box(draw, note, PANEL)
    multiline(draw, (380, 895), "推荐执行顺序：先把问题隔离，再逐层增加复杂度。不要一上来就在 floating-base 里同时改 gait、反馈、低层和 viewer。", font(26), MUTED, spacing=12)

    out = ASSET_DIR / "experiment_roadmap.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def variable_flow_overview() -> Path:
    image, draw = new_canvas()
    title(draw, "变量流向总图", "把最关键的变量按输入、状态、中间量、执行量和观测量放到一张图里")

    left_boxes = [
        ((70, 250, 420, 470), ORANGE, "输入命令", ["x_vel / y_vel", "yaw_rate", "height / pitch / roll", "activate / trot / hop"]),
        ((70, 560, 420, 820), BLUE, "MuJoCo 观测量", ["joint pos / vel", "foot pos / touch", "imu quat / gyro / vel", "torso xyz / rpy"]),
    ]
    center_boxes = [
        ((520, 220, 930, 470), GREEN, "State", ["foot_locations", "joint_angles", "quat_orientation", "body_velocity", "contact_estimate"]),
        ((520, 560, 930, 830), YELLOW, "控制中间量", ["contact_modes", "swing_proportion", "touchdown_location", "rotated_foot_locations"]),
    ]
    right_boxes = [
        ((1050, 250, 1430, 470), PURPLE, "执行变量", ["target_qpos", "tau", "data.ctrl", "qpos / qvel"]),
        ((1500, 250, 1730, 470), RED, "结果与指标", ["delta xyz", "max pitch", "final foot error", "plots / telemetry"]),
    ]

    for box, color, header, items in left_boxes + center_boxes + right_boxes:
        shadowed_box(draw, box, color)
        x1, y1, _, _ = box
        multiline(draw, (x1 + 22, y1 + 22), header, font(30), TEXT)
        multiline(draw, (x1 + 24, y1 + 82), bullet_text(items), font(22), TEXT, spacing=10)

    arrow(draw, (420, 360), (520, 340), fill="#B36B16", width=9, head=20)
    arrow(draw, (420, 690), (520, 700), fill="#2E6EAF", width=9, head=20)
    arrow(draw, (930, 340), (1050, 340), fill="#5C7A3A", width=9, head=20)
    arrow(draw, (930, 700), (1050, 360), fill="#8C7A13", width=9, head=20)
    arrow(draw, (1430, 340), (1500, 340), fill="#8D4F9D", width=9, head=20)

    draw.line((1180, 470, 1180, 920, 300, 920, 300, 820), fill="#5D6B80", width=8)
    arrow(draw, (300, 820), (300, 820), fill="#5D6B80", width=8, head=1)
    arrow(draw, (300, 825), (300, 820), fill="#5D6B80", width=8, head=18)
    label(draw, (530, 950), "从结果回看时，优先判断：问题出在输入、状态估计、中间轨迹，还是低层执行。", 24, MUTED)

    out = ASSET_DIR / "variable_flow_overview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def sim_to_real_migration() -> Path:
    image, draw = new_canvas()
    title(draw, "从仿真到实机迁移图", "哪些东西可以直接复用，哪些地方需要重新建模、校准和留余量")

    left = (70, 260, 800, 920)
    right = (1000, 260, 1730, 920)
    shadowed_box(draw, left, BLUE)
    shadowed_box(draw, right, ORANGE)

    multiline(draw, (105, 300), "仿真侧：MuJoCo", font(38), TEXT)
    multiline(
        draw,
        (110, 380),
        bullet_text([
            "Controller / Gaits / Stance / Swing / IK 可直接复用",
            "State 回灌来自理想化传感器",
            "PD torque 与 actuator 范围可控",
            "地面、摩擦、噪声、延迟较干净",
            "适合验证 gait、反馈方向、参数趋势",
        ]),
        font(25),
        TEXT,
        spacing=12,
    )

    multiline(draw, (1035, 300), "实机侧：Pupper Hardware", font(38), TEXT)
    multiline(
        draw,
        (1040, 380),
        bullet_text([
            "仍然复用 Controller / IK / Configuration 主链",
            "需要 ServoCalibration、PWM、舵机方向校准",
            "IMU 读数会有噪声、延迟和丢包",
            "摩擦、地毯、地面坡度、机身装配误差都会进入系统",
            "必须为速度、力矩、姿态留更大安全余量",
        ]),
        font(25),
        TEXT,
        spacing=12,
    )

    arrow(draw, (800, 470), (1000, 470), fill="#2E6EAF", width=10, head=22)
    multiline(draw, (820, 410), "可直接迁移", font(28), "#2E6EAF")
    multiline(draw, (812, 452), "Controller / gait / IK 主逻辑", font(22), "#2E6EAF")

    mid_boxes = [
        ((790, 570, 1010, 700), YELLOW, "迁移时重点补课", ["传感器噪声", "执行器饱和", "结构公差", "地面不确定性"]),
        ((790, 760, 1010, 890), RED, "实机更保守", ["x_vel ↓", "kp / kd 留余量", "更小 clearance 起步", "先低风险回归"]),
    ]
    for box, color, header, items in mid_boxes:
        shadowed_box(draw, box, color)
        x1, y1, _, _ = box
        multiline(draw, (x1 + 18, y1 + 18), header, font(24), TEXT)
        multiline(draw, (x1 + 20, y1 + 60), bullet_text(items), font(19), TEXT, spacing=8)

    label(draw, (120, 860), "结论：先在 MuJoCo 确认“方向对不对”，再在实机确认“鲁棒性够不够”。", 24, MUTED)

    out = ASSET_DIR / "sim_to_real_migration.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        project_structure_map(),
        entrypoints_map(),
        floating_control_flow(),
        tuning_flow(),
        feedback_closed_loop(),
        experiment_roadmap(),
        variable_flow_overview(),
        sim_to_real_migration(),
    ]
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
