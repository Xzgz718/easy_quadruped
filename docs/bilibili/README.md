# StanfordQuadruped B 站五讲课程包

本目录给出一套围绕当前仓库整理的课程材料，适合直接作为 B 站系列视频的底稿。

包含文件：

- `stanford_quadruped_bilibili_5_course_notes.md`
  - 五讲合并讲义，按“项目主链 -> 控制器 -> 足端与 IK -> MuJoCo -> 实机与扩展”展开。
- `stanford_quadruped_bilibili_5_course_notes.pdf`
  - 由讲义 Markdown 导出的 PDF 版本，方便打印或直接阅读。
- `stanford_quadruped_bilibili_5_course_slides.md`
  - 按幻灯片分页组织的 PPT 文稿，适合直接复制到 PowerPoint / Keynote，或用 Marp 类工具转换。
- `lecture01_project_overview_notes.md` ~ `lecture05_hardware_sim2real_notes.md`
  - 5 份独立讲义，分别对应 5 次视频课程。
- `lecture01_project_overview_slides.md` ~ `lecture05_hardware_sim2real_slides.md`
  - 5 份独立 PPT 文稿，便于逐集录制。
- `lecture01_project_overview_notes.pdf` ~ `lecture05_hardware_sim2real_notes.pdf`
  - 5 份独立讲义 PDF，方便单集分发或打印。
- `lecture01_project_overview_courseware.pptx` ~ `lecture05_hardware_sim2real_courseware.pptx`
  - 5 份更像正式课件的 `.pptx` 结构稿，已带统一版式、颜色、图示位和代码页。
- `build_bilibili_pptx.py`
  - `.pptx` 生成脚本，可在后续改文案后重新构建课件。

拆分版建议顺序：

- 第 1 讲：`lecture01_project_overview_notes.md`
- 第 2 讲：`lecture02_controller_state_gait_notes.md`
- 第 3 讲：`lecture03_foot_planning_ik_notes.md`
- 第 4 讲：`lecture04_mujoco_closed_loop_notes.md`
- 第 5 讲：`lecture05_hardware_sim2real_notes.md`

使用建议：

- 录视频时，优先按讲义做主叙事，再用 PPT 文稿控制节奏。
- 代码演示建议优先选择 `sim/run_fixed_base.py` 和 `sim/run_floating_base.py`。
- 实机部分建议作为第 5 讲后半段，用于说明接口与工程落地，不建议作为第一讲入口。

如需重新导出讲义 PDF，可在仓库根目录执行：

```bash
python docs/export_markdown_pdf.py \
  docs/bilibili/stanford_quadruped_bilibili_5_course_notes.md \
  docs/bilibili/stanford_quadruped_bilibili_5_course_notes.pdf
```

如需重新生成 5 份 `.pptx` 结构稿，可执行：

```bash
python docs/bilibili/build_bilibili_pptx.py
```

说明：

- 讲义中复用了仓库已有图片资源，因此不会重复拷贝大图。
- PPT 文稿当前采用 Markdown 幻灯片格式，便于后续二次编辑。
- 合并版适合总览，拆分版适合逐集录制与单独发布。
- `.pptx` 结构稿适合直接继续美化成正式课件，比如替换字体、加学校/频道封面、补动画与讲者备注。
