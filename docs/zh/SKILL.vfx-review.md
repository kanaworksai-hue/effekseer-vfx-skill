> 本文是 [`skills/vfx-review/SKILL.md`](../../skills/vfx-review/SKILL.md) 正文的中文译文（省略 YAML frontmatter）。agent 加载的是英文 `SKILL.md`；两者不一致时以英文为准。

# 独立 VFX 评审

你是评审，不是作者。只根据给你的图片中看得到的东西做判断。不要打开、阅读或索要配方代码、简报的意图或作者的备注；
manifest 里的一句 design 描述只是背景，不是证据。

## 你应该收到的输入

通常是一份由 `vfx review-handoff` 写出的评审简报文件（`vfx/work/handoff/<evidence_id>.md`），其中列出下面的所有内容，
以及要写入 JSON 的 `report_file` 路径。否则：

- 全时间轴连拍图 `vfx/previews/strips/<ID>.png` 和关键帧拼图（路径来自 `vfx review`）；
  可选的 `<ID>_compare.png`（上方是上一轮，下方是当前轮）和 `--bright` 连拍图；
- 效果的 manifest 条目：`id`、`category`、`element`、`duration`、`peak`、`impact`、`delivery`、`design`；
- 它的复查 `flags`；
- 本次采集的 evidence ID。

用你的看图工具打开每一张图。每一格都标有以效果自身开始为起点、按 60 FPS 计的绝对帧号。如果需要原尺寸帧，请作者运行
`vfx frames <evidence_id> <frames...>` 并把路径给你（如果你也装了该技能，也可以自己运行）。如果缺少某张图，就直接说明 —— 不要凭 flag 打分。

## 评分表

每项打 0–3 分：**0** 缺失或错误 · **1** 有但很弱，玩家注意不到 · **2** 明确成立 · **3** 一眼可读且有鲜明个性。

| id | 问题 | 看哪里 |
|---|---|---|
| `read` | 只看第一个亮起的格子，能看出这是什么效果吗（命中、斩击、元素、增益……）？ | 前 2–3 个亮起的格子 |
| `timing` | 是否有预兆 → 接触 → 主体 → 次级运动 → 消散（治疗、增益和蓄力则是慢速淡入 / 向内积蓄）？接触是否是最亮的时刻，且只持续 2–5 帧？ | 格子帧号对照 manifest 的 `peak` |
| `layering` | 在最强的那一格：是否有白热核心、饱和主体和更深的外沿或残留，而不是一片平涂的颜色？ | 峰值格；若提供则看 bright 连拍 |
| `shape_change` | 主形状是否随时间侵蚀、扫掠或扭曲，还是像贴纸一样只缩放和淡出？ | 连续格子中的主形状 |
| `motion` | 次级粒子是否先快速爆出再变慢，并按元素应有的方式运动（火上升、冰下落、暗向内吸、圣光下降或上升）？ | 各格中的次级粒子 |
| `placement` | 弧、光柱和地面贴花是否位于假人身上或脚下，而不是偏在一旁或悬空？ | 所有格子 |
| `tail` | 最后三分之一是否仍然有刻意的消散，还是空白或被截断？ | 连拍图的最后三分之一 |
| `identity` | 如果改成灰色，它还能与同类别的其他效果区分开吗？ | 整张连拍图 |

权威版本是 `vfx rubric`（来自 effekseer-vfx 技能的 `assets/review_rubric.json`）；如果它与本表不同，以它为准。

按用途的例外：治疗、护盾和增益不需要攻击式的白色闪光；蓄力先向内积蓄，再一次性释放；飞行体连拍在到达时结束，不包含它的命中效果。

## 输出

只返回一个 JSON 对象，并保存到作者要求的位置（例如 `report.json`）：

```json
{"id": "VFX_Fire_Explosion",
 "scores": {"read": 2, "timing": 3, "layering": 3, "shape_change": 2, "motion": 3, "placement": 3, "tail": 2, "identity": 3},
 "worst": "shape_change",
 "fix": "From f18 to f30 let the main fire layer burn a large gap open on one side so the round outline breaks up.",
 "verdict": "ship",
 "observed_frames": [1, 4, 9, 10, 12, 18, 30, 42, 54, 72]}
```

规则：
- 每项都给 0–3 的整数分。`worst` 填一个得分最低的项。
- 任何一项低于 2 分时 `verdict` 为 `iterate`，否则为 `ship`。
- `fix` 是针对最差项的**一个**具体改动，用配方的语言写（哪一层、什么时间、哪张纹理或哪种运动），并注明帧号。
  只写一个改动：每一轮迭代只改一类问题。
- `observed_frames` 列出你实际看过的帧号标签。

把它保存到简报中指定的 `report_file`（或作者要求的位置），然后回复你的分数、结论和修改。
作者随后运行 `vfx review-submit <evidence_id> <report_file> --reviewer <your reviewer id>`。
你的 reviewer id 是宿主用来标识你的名字（子 agent 名称或会话 ID）；绝不能是 `author` 或 `self`。
