> 本文是 [`skills/effekseer-vfx/SKILL.md`](../../skills/effekseer-vfx/SKILL.md) 正文的中文译文（省略 YAML frontmatter）。agent 加载的是英文 `SKILL.md`；两者不一致时以英文为准。

# Effekseer VFX

像 VFX 美术那样迭代制作游戏特效，只不过用代码：**简报 → 纹理 → 配方 → EffekseerCore 构建 → 真实 Godot 连拍 → 看图 → 修一处 → 重复 → 独立评审**。

下文的 `<skill>` 指包含本文件（英文 `SKILL.md`）的目录。所有命令的形式都是
`sh <skill>/scripts/vfx [--project <game project>] <command> ...`，输出一个 JSON 对象
（进度信息写到 stderr）。项目默认是当前目录，效果工作区是 `<project>/vfx/`。
运行 `sh <skill>/scripts/vfx --help` 查看全部命令；[references/cli.md](references/cli.md) 有完整说明。
在 Windows 上，`sh <skill>/scripts/vfx` 可以在 Git Bash 里运行；在 cmd 或 PowerShell 里请改用 `<skill>\scripts\vfx.cmd`
（命令相同，输出相同）。

## 在项目里第一次运行

1. `vfx doctor` —— 报告 `modes`（`authoring`、`build`、`render`）、工作区和确切的 `next` 步骤。如果它说存在一个不是由 `vfx init` 创建的 `vfx/` 文件夹，先与用户确认这就是游戏项目（或传入 `--project`），再进行初始化。
2. 如果需要安装，**先征求用户同意**（完整模式会下载约 250 MB 到 `~/.cache/effekseer-vfx`）：
   macOS ARM64 上运行 `sh <skill>/scripts/setup.sh`，Linux 上运行 `sh <skill>/scripts/setup.sh --authoring-only`；Windows 上运行
   `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1`（在 Git Bash 里也可以运行 `sh <skill>/scripts/setup.sh`，它会调用前者）。
   `doctor` 的 `next` 会打印适合本机的确切命令。
   setup 需要 Python 3.11+ 或 uv（macOS 自带的 Python 3.9 太旧）；如果 `doctor` 报告两者都没有，请用户安装其中一个。Godot 4（Forward+）必须由用户自行安装；如果它不在 `PATH` 上，设置 `GODOT`。
3. `vfx init` 创建 `vfx/`（Godot Lab、材质、数学纹理、官方 Effekseer 插件）。除非加 `--update-templates`，否则不会覆盖已有文件。
4. 可选：`vfx examples add <name>` 复制一个完成且经过独立评审的示例用于学习：配对 `fire`、`ice`、`poison`、`dark`（飞行体 + 命中），单独效果 `hit`、`slash`、`charge`、`shield`、`heal`，或 `all`。见 [references/examples.md](references/examples.md)。

`vfx review`、`preview` 和 `showcase` 会在用户桌面上打开 Godot 窗口。如果你运行在沙箱里（例如 Codex 的工作区沙箱），
请在用户批准后到沙箱外运行这些命令；无法离开沙箱时，把完整命令交给用户在自己桌面的终端里运行。以 "rendered no frame" 停止的 review
最可能是打不开窗口（请结合它附带的 Godot 输出判断）。`doctor` 的 `render: true` 只表示找到了 Godot。

没有 `build`/`render` 模式时，仍然可以写简报、配方和纹理并运行 `lint`，但无法判断外观。要明确说明：把工作报告为
**未编译、未经渲染验证**；绝不声称效果有所改善。

## 制作或修改一个效果

1. **先读再写。** 必读 [craft](references/craft.md)、[design](references/design.md)、[layering](references/layering.md)、[timing](references/timing.md) 和 [skeletons](references/skeletons.md)；再按下面的路由表读对应主题文件，并用 `vfx examples show <name>` 查看对应示例的层计划（名称：`hit`、`slash`、`charge`、`shield`、`heal`，飞行体和爆炸等命中效果用配对 `fire`、`ice`、`poison`、`dark`；也可以直接用效果 ID）。修改已有效果时运行 `vfx effect-context <ID>` 并阅读它的历史，避免重复已经失败的改法。
2. **简报。** 编写 `vfx/briefs/<ID>.json`（三个关键画面、调色板职责、节拍、层计划、验收条件、避免事项）。格式见 [design.md](references/design.md)。
3. **纹理。** `init` 之后已经有数学形状（光晕、环、噪声、拖尾、扰动图），以及一套入门用的手绘烟、爆炸、丝状笔触、裂纹和冰纹理。复杂的手绘形状（火焰、斩击、烟、裂纹、冰、符文）来自图像生成模型 —— 按 [textures.md](references/textures.md) 操作。使用任何纹理的角度之前，先用 `vfx texture-info` 实测。
4. **配方。** 编写 `vfx/src/<ID>.py`，用 [primitives.md](references/primitives.md) 中的基元定义 `recipe()`。坐标轴、单位和混合行为遵循 [engine-conventions.md](references/engine-conventions.md) 中已实测的引擎规则，不要猜。
5. `vfx brief-validate <ID>` 和 `vfx lint --ids <ID>`。lint 的 error 必须修；warning 是制作提示，以渲染结果为准。
6. `vfx build --ids <ID>`，然后 `vfx review --ids <ID> --note "<what this round changed>"`（`--note` 写明本轮改了什么）。
7. **看图。** 用你的看图工具打开 review 返回的每一个路径（`sheets`、`compare`、`details.*.sheet`）。flag 只指出可能的问题；绝不只凭 flag 下结论。流程和各 flag 的含义见 [review.md](references/review.md)。
8. **每轮只修一类问题**，每个效果迭代 3–5 轮。
9. **独立评审。** 作者从不给自己的效果打分。运行 `vfx review-handoff <ID>`：它会写出一份完整的评审简报（图片、采集到的帧号、manifest 背景、评分表、报告的保存位置，以及安装在本技能旁边的 `vfx-review` 技能的路径），并返回 `prompt_file`、`report_file` 和确切的提交命令。把这份简报原样交给另一个没有看过配方的 agent：宿主支持时就用它启动一个子 agent，除此之外不告诉它任何关于这个效果的信息；否则请用户打开一个新会话并粘贴进去。`report_file` 出现后，运行返回的 `vfx review-submit <evidence_id> <report_file> --reviewer <that agent's identifier>`（标识用子 agent 的 ID 或名称，或会话 ID，不能是 `author` 或 `self`；帧号默认取报告中的 `observed_frames`）。绝不要自己写这份报告。
10. `vfx overview`（不带 `--ids`：效果库基线），然后 `vfx effect-verify <ID>`。只有 `verified: true` 才能报告为完成；否则列出缺什么。如果达到轮数上限仍没有 ship 结论，报告未解决的项目。

## 硬性规则

- 每个效果都有时间结构（预兆 → 接触 → 主体 → 次级运动 → 消散）和亮度分层（白热核心、饱和主体、更深的外沿或残留）。治疗、护盾和蓄力有各自文档化的例外。
- 主体会改变形状（溶解、扫掠、UV 扰动、序列帧、重新击出的形状）；绝不只做缩放和淡出。粒子用缓出（先快后慢）。
- 元素之间至少在形状、运动、节奏、材质、次级运动中的三项上不同 —— 绝不只是换色。
- 不要用 Python 画复杂的手绘形状。如果没有图像生成工具，把提示词写进 `vfx/texture_prompts.json`，向用户索要图片。
- 生成的原图保留在 `vfx/textures/generated/`，处理后的副本写到 `vfx/textures/processed/`；记录每一条提示词。
- 单位：配方 timing 是 60 FPS 帧数，F-Curve 是生命周期百分比，manifest 的 duration/peak 是秒，Godot API 的 rotation 是弧度。
- 每个效果都声明 `delivery`；飞行体需要一个反向指向它的配对命中效果。
- 只使用编译器认识的层字段（`vfx layer-schema`）；需要新功能时扩展编译器，不要把裸属性路径写进配方。
- 全量 `vfx build`（不带 `--ids`）会清除由本技能构建、但源码已离开 `vfx/src/` 的效果的产物；它绝不删除不是它构建的效果，并且拒绝在空的效果库上运行。只做局部工作时用 `--ids`（其他地方损坏的源码会列在 `unloaded` 中，而不会阻塞它）。
- 没有实际运行并检查过，绝不声称导出、播放、设备性能或录像成功。

## 路由表

| 任务 | 另外阅读 |
|---|---|
| 新的手绘纹理、序列帧、纹理问题 | [textures.md](references/textures.md) |
| 斩击、飞行体、蓄力、光环，任何会移动的东西 | [motion.md](references/motion.md) |
| 护盾、光柱、Boss、状态、体积、遮挡 | [shapes.md](references/shapes.md) |
| 对照参考视频 | [reference.md](references/reference.md) |
| 具体的视觉失败（白团、尾段空白、没有破碎） | [cases.md](references/cases.md) |
| 给编译器添加引擎功能 | [engine-conventions.md](references/engine-conventions.md#扩展编译器)、`vfx discover`、`vfx core property-list/get/set` |
| 在游戏中使用效果 | [godot.md](references/godot.md) |

## 配方骨架

```python
# vfx/src/VFX_Hit_Spark.py
from vfxkit.primitives import *

def recipe():
    hot = (255, 240, 200, 255)
    return effect('Hit_Spark', 'Spark Hit', 'hit', 'physical', .4, [
        flash('Contact flash', WHITE, 2.2, life=4, delay=1),
        glow('Bloom', (255, 170, 70, 170), 1.6, life=9, delay=1),
        radial_sparks('Sparks', 10, hot, color_end=(255, 120, 30, 255), distance=(.8, 1.7), life=(12, 16), delay=1, gravity=.0018),
        smoke('Dust', (185, 160, 135, 200), count=2, size=(.5, .7), life=(13, 14), delay=4),
    ], peak=.03, impact=.3, delivery=MELEE, design='One-line description of what the player sees.')
```

`effect('Hit_Spark', ...)` 生成 ID `VFX_Hit_Spark`，它必须与文件名一致。`vfx/src/` 中以 `_` 开头的文件是共享辅助模块，
配方可以 import 它们。
