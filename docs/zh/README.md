# effekseer-vfx-skill 中文文档

这里是本技能包英文文档的简体中文译文，供人阅读参考。agent 实际加载的是 `skills/` 下的英文文件
（[`skills/effekseer-vfx/SKILL.md`](../../skills/effekseer-vfx/SKILL.md)、[`skills/vfx-review/SKILL.md`](../../skills/vfx-review/SKILL.md)
和 [`skills/effekseer-vfx/references/`](../../skills/effekseer-vfx/references/)）；译文与英文不一致时以英文为准。
项目介绍见 [README.zh-CN.md](../../README.zh-CN.md)。

## 技能

| 页面 | 说明 |
|---|---|
| [SKILL.effekseer-vfx.md](SKILL.effekseer-vfx.md) | 制作技能主文档：首次运行、制作一个效果的完整流程、硬性规则、路由表和配方骨架 |
| [SKILL.vfx-review.md](SKILL.vfx-review.md) | 独立评审技能：评审应收到的输入、0–3 评分表和 JSON 输出格式 |

## 参考文档（`references/`）

| 页面 | 说明 |
|---|---|
| [craft.md](references/craft.md) | 制作规则：为什么"贴纸感"不行、时间结构、元素差别、飞行体、不规则多职责技巧、预算 |
| [design.md](references/design.md) | 设计简报：要决定什么、调色板职责、按用途的时间结构、风格例外和简报 JSON 格式 |
| [layering.md](references/layering.md) | 明暗、颜色与图层配对：调色板职责、三种副本、尺寸与寿命起点、白团/黑团的修复顺序 |
| [timing.md](references/timing.md) | 强度、体积与退场节奏：各阶段的接替、示例参考时间、曲线落帧、尾段检查 |
| [skeletons.md](references/skeletons.md) | 类别骨架：命中、斩击、爆炸、飞行体、蓄力、护盾、治疗与增益的层职责 |
| [motion.md](references/motion.md) | 运动与路径：飞行体的头部/拖尾/脱落粒子、斩击扫掠、把速度放进形状和节奏 |
| [shapes.md](references/shapes.md) | 体积与遮挡：按标准镜头选择体积、绘制顺序决定遮挡 |
| [textures.md](references/textures.md) | 纹理职责、生成与验收：图像生成模型与程序化纹理的分工、提示词写法、处理与实测 |
| [reference.md](references/reference.md) | 对照参考视频：导入、读帧、与采集帧配对比较及其局限 |
| [review.md](references/review.md) | 复查循环、证据与交付：review 产出、flag 含义、阅读连拍、独立评审、`effect-verify` |
| [cases.md](references/cases.md) | 诊断案例：火焰爆炸、飞行体烟尾、护盾破碎三个重建的前后对照案例，附真实渲染对照图 |
| [cli.md](references/cli.md) | 命令参考：所有 `vfx` 命令、所需环境和工作区结构 |
| [examples.md](references/examples.md) | 随附示例：火、冰、毒、暗四组飞行体 + 命中配对，命中、斩击、蓄力、护盾、治疗五个单独效果，以及怪兽套组及其用法 |
| [godot.md](references/godot.md) | 在 Godot 中使用效果：`Vfx` API、光束、放大的效果、软粒子、Lab 操作、替身角色和运行时检查 |
| [engine-conventions.md](references/engine-conventions.md) | 已验证的引擎约定：角度与坐标轴、力、网格与 fresnel、序列帧、继承、游戏输入与动态方程、HDR 与 Lab、锚点、扩展编译器 |
| [primitives.md](references/primitives.md) | 配方代码与基元：`effect()` 字段、基元表、辅助函数、层字段（含 `bind`）和单位 |
| [scale.md](references/scale.md) | 世界尺度：巨人、怪兽、战舰的 `scale` 档位、哪些字段会换算、放大后的 Lab 和检查 |
| [realism.md](references/realism.md) | 照片级的爆炸、火焰和烟：来自照片的颜色与亮度、照片级序列帧、与地面相接的 soft、层计划 |
