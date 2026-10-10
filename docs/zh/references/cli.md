# 命令参考

`sh <skill>/scripts/vfx [--project DIR] <command> [options]`。输出：stdout 上的一个 JSON 对象；构建期间的进度和 lint 警告写到 stderr。
退出码：0 成功，1 检查失败或出错（`{"ok": false, "error": {...}}`），2 需要先安装：缺少工具链（`SetupRequired`）或这里没有工作区（`WorkspaceMissing`）。
图片结果是文件路径 —— 要打开它们。

除 `doctor`、`init`、`examples`、`rubric`、`layer-schema` 和 `process-texture` 之外，每个命令都需要由 `vfx init` 创建的工作区
（`vfx/src/` 和 `vfx/vfx_manifest.json`）。在游戏项目中运行，或传入 `--project`；在错误的文件夹中运行的命令会以 `WorkspaceMissing`
失败，而不会创建一个多余的 `vfx/`。当前目录不在 Python 的 import 路径上，`vfx/src` 中的辅助模块只按 `_name` 文件解析，
因此项目文件绝不会遮蔽标准库。

环境变量：`VFX_PROJECT`（项目，默认当前目录）、`EFFEKSEER_VFX_HOME`（工具链，默认 `~/.cache/effekseer-vfx`）、
`GODOT`（Godot 4 可执行文件，默认先找 PATH 上的 `godot`，再找 `/Applications/Godot.app`）。

| 命令 | 需要 | 作用 |
|---|---|---|
| `doctor` | — | 平台、工具链、工作区；`modes` 和 `next` 步骤 |
| `init [--update-templates] [--no-plugin]` | Python | 创建/刷新 `vfx/`（Lab、材质、数学纹理、入门手绘纹理）；下载官方 Effekseer Godot 插件（固定校验和） |
| `examples [list]` | — | 随附的配对和单独效果，以及它们的历史分数、结论和最弱项 |
| `examples show <name\|ID>` | Python | 带绝对帧号和职责的层计划（配对会同时显示两个效果） |
| `examples add <name\|ID\|all> [--force]` | Python | 把示例源码、简报、手绘纹理和提示词复制到项目中；名称：`fire`、`ice`、`poison`、`dark`、`hit`、`slash`、`charge`、`shield`、`heal` |
| `procedural` | Python | 重新生成数学基元纹理 |
| `list` | Python | `vfx/src` 中的效果及其类别、时间、delivery、design 和构建状态；加载失败的源码列在 `unloaded` 中 |
| `lint [--ids ...] [--timeline]` | Python | 静态规则（error）和制作启发式（warning），见下文 |
| `layer-schema` | Python | 编译器接受的每一个层字段 |
| `brief-validate <ID>` | Python | 简报与配方对照，并给出展开后的绝对层时间线 |
| `effect-context <ID>` | Python | 简报、构建问题、最新证据和最近 10 轮 |
| `texture-info [names...]` | Python | 覆盖率、包围盒、贴边情况、朝向、弧顶凸出、接缝比 |
| `texture-audit <name> [--role R] [--grid C R] [--loop] [--allow-empty i...]` | Python | 按职责检查 + 预览图 |
| `process-texture <src> <dst> [--size N] [--color] [--grid C R]` | Python | 裁切、alpha、留边、缩放到 2 的幂 |
| `build [--ids ...]` | Core | lint、编译、save/open 回读、manifest、构建 receipt；不带 `--ids` 时还会清除由本技能构建、但源码已离开 `vfx/src` 的效果（见下文） |
| `compile <recipe.json> [--source] [--runtime]` | Core | 编译一个配方 JSON |
| `export [--output DIR]` | Core | 把所有已构建的效果重新导出为带 `resources/` 的 `.efk` |
| `discover` | Core | 把 Core 的属性路径、类型和枚举导出到 `vfx/work/property_schema.json` |
| `core <command> ...` | Core | 内置桥接程序对明确指定的 `.efkefc` 文件执行的底层命令：`property-list`、`property-get`、`property-set`、`node-list`、`curve-list`、`curve-set`、`settings-list`、`settings-set`、……（`vfx core --help`）；见 [引擎约定](engine-conventions.md#扩展编译器) |
| `review [--ids] [--step N] [--note] [--key-frames ...] [--view standard\|close] [--profile default\|bare] [--bright]` | Core + Godot | 连拍图、关键帧拼图、flags、changes、evidence ID |
| `overview [--ids]` | 已完成 review | 取自最新标准采集的效果库总览页（`effect-verify` 检查的基线）；从未采集过的效果会被跳过并列在 `missing` 中。带 `--ids` 时生成一张临时页 `overview_select_*.png`，不会替换基线 |
| `strip <ID> [--compare] [--bright]` | 已完成 review | 连拍图路径和保存的 metrics |
| `frames <evidence_id> <frame...>` | 已完成 review | 原尺寸帧路径和新鲜度问题 |
| `history <ID> [--limit N]` | — | 复查轮次，最新的在最后 |
| `rubric` | — | 独立评审的评分表 |
| `review-handoff <ID>` | 已完成 review | 为最新的新鲜采集写出独立评审的完整简报（`prompt_file`），并给出 `report_file` 和提交命令 |
| `review-submit <evidence_id> <report.json> --reviewer ID [--frames f...]` | 已完成 review | 绑定一份独立评审报告；帧号默认取它的 `observed_frames` |
| `effect-verify <ID> [--no-overview]` | — | 除非当前构建、采集、评审和总览一致，否则以 1 退出；`--no-overview` 是部分检查，只报告 `passed_without_overview`，永远不会给出 `verified: true` |
| `preview [--ids] [--bright] [--output]` | Godot | 在基线、峰值、50 %、85 % 时刻的带 UI 截图 |
| `showcase [--movie]` | Godot（+ ffmpeg） | 打开自动播放效果库的 Lab；`--movie` 录制下来 |
| `package [--preview-dir]` | Godot | 把 Godot 项目连同纹理清单打成 zip；不声称做过设备测试 |
| `reference-import`、`reference-frames`、`reference-compare` | ffmpeg | 见 [reference](reference.md) |

## `--ids` 与损坏的源码

带 `--ids` 时，`lint` 和 `build` 只要求点名的源码能加载；其他任何加载失败的 `vfx/src/VFX_*.py`（写了一半的效果）会列在
`unloaded` 中并排除在跨效果检查之外，而不会阻塞工作。不带 `--ids` 时，每个源码都必须能加载。

## 全量构建可能删除什么

当 `vfx/src` 中没有配方时，全量 `vfx build` 拒绝运行。否则它只删除**由本技能构建**且 `vfx/src/<ID>.py` 已不存在的效果：
带有 `built_by: "effekseer-vfx"` 标记、且 `source` 等于自身 `vfx/src/<ID>.py` 的 manifest 条目；或在加这个标记之前构建的工作区里，
`vfx/work/builds/` 中构建回执仍与磁盘上 `.efkefc` 一致的效果。格式不对的 ID 永远不算本技能所有；删除任何东西之前，都会先检查每条路径
都在 `vfx/` 之内。manifest 或 `vfx/effects/` 里由其他工具或人工制作的效果会保留，`vfx doctor` 把它们计为 `unmanaged`。

全量构建还会清理没有配方使用的资源副本：只删与 `vfx/textures/processed/` 中纹理完全相同的文件（及该 PNG 自己的 `.import`），
从不删同前缀的其他文件，也从不删 unmanaged 效果可能用到的名字（其 `.efkefc` 里写着这个文件名，或其文件缺失）。Core 按文件名把每个纹理
和模型复制到 `resources/`，因此两个不同文件同名时构建会以 `Resource name conflict` 停止：同一次构建内冲突；与某个使用它、但本次没有一起
重建的自有效果冲突（把它们一起重建）；或与可能用到它的 unmanaged 效果冲突（给文件改名）。任一输出目录解析到 `vfx/` 之外（指向别处的符号
链接）时，构建拒绝运行。每份构建回执都绑定了它全部的资源副本，之后的构建若改动其中一个，之前的采集就会失效。

## lint 检查什么

Error（只要存在，构建就会拒绝）：

- 未知或拼错的层字段（附带建议），以及无效的字段值；
- `peak` 超出 duration；`infinite` 层没有 `flight` 或没有 `interval`；
- 某层存活超过 duration（非循环效果），计入出生时间和飞行体释放；
- 粒子预算超过类别上限：`hit` 60、`projectile` 100、`boss` 250，其他所有类别 150；
- 某纹理既不是数学基元，也没有记录在 `vfx/texture_prompts.json` 中，或在 `vfx/textures/processed/` 中缺失；
- `size_curve`/`scale_curve` 与随机尺寸或缩放范围同时使用（编译器无法把它们相乘）；
- 在序列帧上使用 UV 扰动（它会采样相邻格子，渲染出生硬的方形边缘）；
- 重力大于 0.01（它是按每帧的平方计算的）。

Warning（制作提示；以连拍为准）：

- `fade_in + fade_out` 长于最短寿命（该层永远达不到完全不透明）；
- `impact >= 0.3` 的效果没有接触：没有 `flash()` 层，也没有一个存活不超过 10 帧的白热 Add 层；
- 接触的开始与 manifest 的 `peak`（Lab 在此触发反馈）相差超过 6 帧；
- `flash()` 存活超过 6 帧（接触应为 2–5 帧）；
- 没有任何层改变形状：没有溶解 cutoff、环扫掠、UV 扰动或滚动、序列帧，也没有在后续帧重新击出的手绘形状；
- 没有白热的 Add 颜色（luma ≥ 0.85 且每个通道 ≥ 180）；
- 同一类别、不同元素的两个效果，在形状、运动、节奏、材质和次级运动中只有不到 3 项不同（很可能只是换色）。

## 工作区结构

```
<project>/vfx/
  src/VFX_*.py            recipe sources (yours)              ┐
  briefs/VFX_*.json       design briefs                       │
  texture_prompts.json    prompts of painted textures         │ the effect library:
  textures/generated/     image-model originals (never edited)│ keep under version control
  textures/processed/     game textures (incl. procedural)    │
  recipes/*.json          compiled recipe snapshots           │
  effects/*.efkefc        Effekseer sources + resources/      │
  exports/*.efk           runtime exports + resources/        │
  vfx_manifest.json       ids, timing, delivery, design       │
  previews/strips/overview_*.png, metrics.json                ┘
  characters/             optional rigged stand-ins (player.glb, target.glb)
  godot/                  generated Godot Lab (ignored)
  work/                   receipts, locks, reference frames, audits, property schema (ignored)
```

从 `src/` 到 `previews/strips/overview_*.png, metrics.json` 的条目构成效果库，要纳入版本控制：配方源码（你写的）、设计简报、
手绘纹理的提示词、图像模型原图（从不编辑）、游戏纹理（含程序化纹理）、编译后的配方快照、Effekseer 源文件 + `resources/`、
运行时导出 + `resources/`、manifest（ID、时间、delivery、design）以及总览页和 metrics。`characters/` 放可选的绑骨替身角色
（`player.glb`、`target.glb`）；`godot/` 是生成的 Godot Lab，`work/` 存放 receipt、锁、参考帧、audit 和属性 schema，两者都被忽略。
