# 复查循环、证据与交付

静帧无法展示节奏。每次修改之后：`vfx lint`、`vfx build --ids <ID>`、`vfx review --ids <ID>
--note "<one problem, one change>"`（`--note` 写一个问题、一个改法），然后**打开图片**。

目录：review 产出什么 · flags · 阅读连拍图 · 轮次与历史 · 独立评审 · 验证 · 变体 · 采集行为

## `vfx review` 产出什么

Godot Lab 在隐藏 UI 的真实 viewport 中渲染效果，使用对战站位（两个假人站在平台两端；效果按其 `delivery` 演出）。
帧号从效果本身开始的那一帧算起（出拳、施法、飞行体到达）；假人保持待机姿势。飞行体连拍在到达时结束，不包含它的命中；
命中连拍保持同一落点和到达时刻，但不含前导飞行体的残留。命令返回：

- `sheets` —— 全时间轴连拍图 `vfx/previews/strips/<ID>.png`（最多 18 格；关键帧从不被丢弃）；
- `compare` —— `<ID>_compare.png`，存在上一轮连拍时生成，上方是上一轮，下方是当前轮；
- `details.<ID>.sheet` —— 关键帧拼图（接触前后、简报 beats、主体、退场和 duration 之后的检查帧），以及
  `details.<ID>.frames` —— 原尺寸帧；
- `flags`、`changes`（与上一轮相比新增或消除的 flag 类型、移动了的关键时间）、`metrics`、`history`，以及本次采集的 `evidence` ID。

之后可以用 `vfx strip <ID> [--compare]`、`vfx frames <evidence_id> <frames...>` 和 `vfx history <ID>` 重新读取。
有对比图时先看对比图。

## Flags

像素指标是相对空舞台的"变化能量"，因此一大片淡烟和一个小白闪可以相互比较。它们是辅助阅读的工具，**不是** GPU 或 overdraw 测量。

| Flag | 含义 | 先怎么修 |
|---|---|---|
| `barely visible` | 最强一帧时舞台变化不到 0.25 % | 主体太小或太暗 |
| `dead tail` | 最后 35 % 中没有任何一帧超过峰值能量的 5 % 或舞台变化 0.25 % | 缩短 `duration` 和尾部寿命，或让消散可见 |
| `blown out` | 超过两个采样帧中纯白超过 10 % | 缩小光晕，降低 emissive |
| `cut off` | 最后一帧仍然清晰可见 | duration 太短 |
| `off-peak contact` | 最白的一帧与 manifest 的 `peak` 相差超过 6 帧 | 移动接触或 `peak`；否则 Lab 的闪光和镜头抖动落在别处 |
| `lingering flash` | 接触前后接近峰值的白色持续超过 12 帧 | 接触应为 2–5 帧；持续的热主体（光束核心、尖刺）不算 |
| `no white-hot core` / `washed out` | 峰值时几乎没有像素超过 85 % 亮度 / 几乎没有饱和的中间调主体 | 加热核心 / 恢复主体的饱和度 |
| `sinks`（仅火） | 接触后团块向下移动 | 火应该上升 |
| `expands while charging`（仅暗） | 释放前半径变大 | 暗应该向内吸 |

阈值是在真实效果库渲染上逐格校准的；理由写在 `scripts/vfxkit/review.py` 的开头。只有在检查过真实连拍之后才能修改阈值，
并在那里补一行理由。

## 阅读连拍图

只有 flag 不算复查。在连拍图和关键帧拼图中问：

1. 从第一个亮起的格子能看出这是什么效果吗？接触是否是最亮的时刻，且只有几帧？
2. 主形状是在侵蚀或扫掠，还是只在缩放和淡出？
3. 次级粒子是否先快后慢，并沿元素的方向运动（火向上、冰向下、暗向内）？
4. 弧、光柱和地面贴花是否位于假人身上或脚下，而不是偏在一旁或悬空？
5. 在亮背景（`--bright`）上，alpha 混合的层是否仍然成立？

看尾段时，看最后三分之一的中间，而不只是最后两格；用 `vfx frames` 取实际帧，或用 `--key-frames` 补采更多时刻。
一个孤立的烟团证明不了整个退场。

## 轮次与历史

每一轮修**一类问题**，并在 `--note` 中写明；note、flags 和关键时间会追加到 `vfx/previews/strips/history/<ID>.jsonl`。
开始新一轮之前阅读历史（`vfx effect-context <ID>`），不要重复证据已经否定的改法。每个效果迭代 3–5 轮；
达到上限仍未通过时，报告未解决的项目，而不是称其完成。

## 独立评审

作者从不给自己的效果打分。`vfx review-handoff <ID>` 会把针对最新一次新鲜采集的完整评审简报写到 `vfx/work/handoff/<evidence_id>.md`：
连拍图和关键帧图片、采集到的帧号、manifest 条目和 flags、一份评分表副本、**vfx-review** 技能的路径（当它安装在本技能旁边时），
以及报告的写入位置。只把这份简报交给另一个 agent，不给其他任何东西：子 agent（告诉它的内容不超出简报），或宿主没有子 agent 时
由用户打开的新会话。不给配方代码。它把 JSON 写到 `report_file`：

```json
{"id": "VFX_X", "scores": {"read": 2, "timing": 3, "layering": 2, "shape_change": 2, "motion": 2, "placement": 3, "tail": 2, "identity": 3},
 "worst": "shape_change", "fix": "one concrete change in recipe terms", "verdict": "ship"}
```

任何一项低于 2 分时 `verdict` 为 `iterate`；`worst` 必须是一个得分最低的项。把它保存为文件，并用 `review-handoff` 返回的命令绑定：
`vfx review-submit <evidence_id> <report_file> --reviewer <reviewer id>`（`--frames` 默认取报告中的 `observed_frames`）。
工具会校验结构、新鲜度和所看帧号；它无法证明评审的独立性 —— 宿主（你）必须真正把它隔离。如果结论是 `iterate`，下一轮就采用它给出的那一个修改。

## 验证

`vfx overview` 把最新的标准采集拼成 `vfx/previews/strips/overview_*.png`。
`vfx effect-verify <ID>` 检查展开后的当前配方、输入纹理、Core 回读、构建出的资源、Lab 舞台和图片是否都与通过的那次评审所看到的一致，
并检查总览页是否包含这次采集。只有 `verified: true` 才算完成。截图存在、没有 flag 或退出码为 0 都不是质量通过。
对配方、纹理、简报或 Lab 的任何修改都会让旧证据失效；更新 Lab 模板之后，先运行 `vfx init --update-templates`。
运行时行为需要单独的 API 检查（`TestApi.gd`，见 [godot](godot.md)）；设备性能需要设备上的证据。

完成之后，把效果库（`vfx/src`、`vfx/briefs`、纹理、配方 JSON、`.efkefc`、`.efk`、manifest、总览页和 `metrics.json`）一起纳入版本控制。
逐帧采集、日志、receipt 和单效果连拍图留在本地（`init` 写入的 `vfx/.gitignore` 会处理这些）。

## 变体

`--view close` 只改变检查用的镜头；`--profile bare` 关闭 Lab 的泛光、打击灯和镜头抖动，用来单独判断效果本身；`--bright` 使用亮背景。
每种变体分开保存，绝不覆盖 standard/default 基线及其 metrics；验证所用的基线是 standard/default。

## 采集行为（macOS）

复查期间用户可能正在使用这台机器：macOS 会停止绘制被完全遮住的窗口，而 Godot 启动时会抢走焦点。在采集模式下，Lab 让窗口保持置顶，
停在右下角只露出一小部分（viewport 仍以 1280×800 渲染），忽略键盘输入和关闭请求，复查结束后把焦点交还给之前的应用
（每次启动约有 0.2 s 的闪烁）。提前退出或从未播放的效果会被重新采集（最多 3 次）。
