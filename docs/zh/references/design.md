# 设计简报

每个新效果都从一份简报开始：在编写配方之前写好 `vfx/briefs/<ID>.json`。`vfx brief-validate <ID>` 会对照配方检查简报（层路径、节拍是否在时长内），所以在第一版配方写好后运行它，之后两者任一改动都要再跑一次。
小修改则先读现有简报，再调整受影响的目标。简报里的时间是从效果开始算起的 60 FPS 绝对帧号；manifest 保留秒。

## 简报要决定什么

写明**用途**（频繁命中、单次技能、终结技、持续状态、展示作品）、**玩家最先读到的形状**、它在标准镜头中**相对角色的尺寸**、
**释放或接触的时刻**，以及**最后留下什么**。验收条件描述可见的行为 ——"闪光消失后火焰仍持续向上翻滚"——
而不是"更多层"或"高级感"。

从三个关键画面开始：**最早可读的画面**、**主体从接触手中接过画面**、**最后一个刻意保留的残留**。对每个画面，
说明什么形状在哪里、正在如何变化，然后再选基元。"一道倾斜的弧横过目标胸口，火焰从它的下沿剥落并上升，最后只剩余烬"
比"酷炫火焰斩"更能指导代码。

| 用途 | 最先读到的形状 | 体积与尺度的决定 | 要留空的空间 |
|---|---|---|---|
| 频繁命中 | 小爆点和短的方向线 | 以命中点为中心；绝不每次都盖住整个角色 | 玩家身体和周围的战斗信息 |
| 方向性斩击 | 倾斜平面内的弧和热边 | 挥砍平面穿过目标；宽度和负空间都可见 | 弧内侧和后方的角色剪影 |
| 单次爆炸 | 从接触点喷发的体积 | 在标准镜头中主体明显变大、抬升并留下残留 | 主体之外留给次级运动的通道 |
| 持续状态 | 围绕持有者的稳定轮廓 | 不保持最高亮度；保持段有表面运动 | 壳内的角色和主视野 |

不要按纹理名来拼。同一段烟雾序列可以给火球之后的画面增加分量，也可以作为飞行路径上的残留，但出生位置、尺寸、方向、
密度和播放的帧范围必须不同。当几个重要的层共用一个中心时，写明哪个在前、哪个在后、哪个先退出。

## 调色板职责

`palette` 分配 **core**、**body**、**dark** 和 **matter**（accent 可选）。短促的热核心；带轮廓的饱和主体；
给轮廓或残留提供对比的暗色；给效果带来物质重量的烟雾和碎片。强调色在简报中声明，不要每层加一种颜色。
效果在灰度下也应该可读。见 [layering](layering.md)。

## 按用途安排时间结构

普通命中是短促的接触，然后衰减。蓄力可以逐渐积累。雷可以有明确的回击。护盾可以有一段稳定的保持。多段技能分别标明每个峰值。
爆炸的亮度下降时主体可能仍在变大、上升。一群小火花绝不能代替一个已经消失的主体。见 [timing](timing.md)。

## 风格规则的例外

"不规则"适合物质、破碎和笔触；它不会自动适用于法阵、瞄准提示或光学星芒。"多职责"适合复杂技能，不适合轻击。
"白色核心"有助于攻击的接触；它并不意味着治疗也必须闪白。[craft](craft.md) 中的参考技巧是候选工具；风格和用途由用户和简报决定。
不要读了一张表就给每个技能都配上同样的光晕、冲击环和火花。

## 简报格式

除 `reference` 外所有字段都是必填的（`assets/brief.schema.json`）。下面节选自随附的 `VFX_Fire_Explosion` 简报，
原简报规划了全部 24 层：

```json
{
  "schema_version": 1,
  "effect_id": "VFX_Fire_Explosion",
  "role": "paired ranged impact",
  "style": "stylized anime combat",
  "dominant_shape": "turbulent comet and ascending cooling smoke",
  "palette": {"core": [255, 250, 220], "body": [255, 120, 30], "dark": [60, 30, 20], "matter": [125, 110, 100]},
  "delivery": {"kind": "projectile", "projectile": "VFX_Projectile_Fire"},
  "anchor": "body",
  "beats": [
    {"frame": 4, "name": "gather", "expect": "Inward gathering at target"},
    {"frame": 10, "name": "contact", "expect": "White-hot detonation lasts only a few frames"},
    {"frame": 18, "name": "body", "expect": "Orange fire survives white flash"},
    {"frame": 54, "name": "tail", "expect": "Grey smoke thins while ascending"}
  ],
  "layer_plan": [
    {"name": "0:Scorch", "role": "ground footprint", "primitive": "Sprite T_Crack01", "exit": "gone by absolute f55"},
    {"name": "5:Detonation flash", "role": "contact", "primitive": "flash", "exit": "gone by absolute f12"}
  ],
  "acceptance": ["Head/body silhouette reads at standard camera after the brightest accent"],
  "avoid": ["Large persistent white blob erasing the body"]
}
```

- `effect_id`、`delivery` 和 `anchor` 必须分别等于配方的 `id`、`delivery` 和 `attach`。
- `beats` 是按顺序排列的绝对帧号（0 … duration + 12）；复查时总会把它们作为关键帧采集。
- `layer_plan[].name` 是层的**带索引完整路径** —— 同级索引加名称，子层用 `/` 连接（`0:Swing plane/1:Blade body`）——
  这样同名层也能区分开。层移动后要更新它。每一层都应该被规划（未规划的层会收到警告）。绝不要把简报元数据写进 layer dict。
- `brief-validate` 会展开父层的出生时间：子层的 delay 不是效果的起点。

随附的示例（`vfx examples add <pair>`）都附有完整的简报，可以直接参照。

## 开始之前

颜色、emissive、Add/Blend 以及 Lab 的 HDR 泛光共同决定画面；先了解 [引擎约定](engine-conventions.md) 中的舞台设置。
把现有效果库和假人的尺寸作为第一参照尺度，然后在标准镜头中检查。优秀的参考作品是节奏和剪影的目标；
它的尺寸和亮度数值并不是本引擎的默认值。
