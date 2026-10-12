# 随附示例

四组远程配对（一个飞行体加上在它到达处播放的命中效果）、五个单独效果（每个常见类别各一个）以及怪兽套组。它们是完整的成品配方，附有设计简报、
手绘纹理（处理后的副本）以及生成它们的提示词。它们的层职责就是 [skeletons](skeletons.md) 中的类别骨架。

| 配对 | 飞行体 | 命中 | 能学到什么 |
|---|---|---|---|
| `fire` | `VFX_Projectile_Fire` —— 翻滚的序列帧火球、拉长的彗星尾、世界空间中的火焰和烟雾拖尾 | `VFX_Fire_Explosion` —— 沿射击方向甩出的不对称火球、攀升的蘑菇云、衰减成烟的贴地火舌、焦痕和裂纹 | 序列帧翻滚、颜色 ramp、`decay()`、方向性的 `spray`/`debris` |
| `ice` | `VFX_Projectile_Ice` —— 带深蓝衬底的水晶冰枪、带棱镜边的飘带、冻结在路径上的霜环 | `VFX_Ice_Spikes` —— 带过冲喷出的晶体、伴随攀升光环的停顿、按时的碎裂 | `crystal` 网格、fresnel 边缘、明度衬底、先停顿后破碎的节奏 |
| `poison` | `VFX_Projectile_Poison` —— 抛射的光亮液团（变形网格）带湿润高光、酸液细丝、会落地的液滴 | `VFX_Poison_Cloud` —— 酸液飞溅、扩散并冒泡的液池、冷却成浑浊紫灰色的毒气、翻滚的雾 | `arc`、Track 拖尾、`ShapeNoise` 液体、互补色暗核、地面碰撞 |
| `dark` | `VFX_Projectile_Dark` —— 在交叉的品红丝状笔触中翻涌的 alpha 黑色球体，被吸入的细针和尘埃 | `VFX_Dark_Vortex` —— 倾斜吸积盘中不断吞噬的黑色视界、一个黑色冲击帧，然后是撕裂的释放弧和地面螺旋 | 吸光的 Blend 主体、向内的 `travel`、盘面分前后两半的遮挡、冲击帧 |

| 单独效果 | 效果 | 能学到什么 |
|---|---|---|
| `hit` | `VFX_Hit_Heavy` | 两帧预兆、5 帧接触、溶解的锯齿状爆点、三档 `spark_burst`、空气泡和折射波 |
| `slash` | `VFX_Slash_Fire` | 在偏航的 `swing()` 平面中使用 `slash_set()`（残影、主体、热边、折射、赛璐璐月牙）；剥落的火舌 |
| `charge` | `VFX_Magic_Charge` | 一秒钟的向内蓄积，带倾斜的 `orbit_band` 环和向内塌缩的壳，然后恰好一次释放 |
| `shield` | `VFX_Shield_Dome` | fresnel 壳和细边缘、过冲弹出、带扫描带的保持段、按时清空的 `shell_fragments` 破碎 |
| `heal` | `VFX_Heal` | 没有冲击帧：地面法阵、滚动的光柱、环、全部上升并缓出的加号和光点 |

| 套组 | 效果 | 能学到什么 |
|---|---|---|
| `kaiju` | `VFX_Kaiju_Atomic_Charge`、`VFX_Kaiju_Atomic_Beam`、`VFX_Kaiju_Explosion` | `scale='kaiju'`（构建时放大 40 倍、放慢 2.5 倍，[scale](scale.md)）；沿假人背部攀升的 `charge_chain()`；由游戏输入驱动、可以扫动的 `beam()`，身后留下蒸汽和焦痕；带烟灰、上升烟柱和柔和地面尘埃的照片级爆炸（[realism](realism.md)） |

怪兽套组在 70 m 高的假人之间演出（Lab 会随效果缩放舞台），它的光束在蓄力之后发射，从目标前方的地面扫到目标胸口。

```sh
vfx examples                     # list with historical scores and verdicts
vfx examples show slash          # layer plan, absolute frames, roles, budget (a pair shows both effects)
vfx examples add kaiju           # a set: the charge, the beam and the explosion
vfx examples add fire            # copy into vfx/src, vfx/briefs, vfx/textures/processed, vfx/texture_prompts.json
vfx lint --ids VFX_Projectile_Fire VFX_Fire_Explosion
vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
```

（`vfx examples` 列出示例及其历史分数和结论；`examples show` 显示层计划、绝对帧号、职责和预算（配对会同时显示两个效果）；
`examples add kaiju` 添加一个套组：蓄力、光束和爆炸；`examples add fire` 复制到 `vfx/src`、`vfx/briefs`、`vfx/textures/processed` 和 `vfx/texture_prompts.json`。）

历史分数（每个评分项 0–3）来自对本技能默认胶囊 Lab 中渲染的一次独立评审：两位评审只看了连拍图、关键帧拼图、manifest 条目和 flags。
其中十一个被判为 `ship`；`VFX_Projectile_Ice`（扁平的冰枪，没有白色核心或暗边，飞行中形状不变）和 `VFX_Projectile_Dark`
（到达之后路径上什么都不留）被判为 `iterate`。怪兽套组以同样方式、在放大的 Lab 中对其自身渲染做了独立评审，经过数轮修改后三个都被判为
`ship`（评审给出的修法：背板贴在身体上、逐块点亮的晶体背鳍、向嘴部汇聚的电光、阴燃烟以及比火焰活得更久的烟柱，用来填满收尾）。`vfx examples` 列出每个示例最弱的评分项和评审给出的一条修法（`historical_review.worst`）。
这些分数只是参考，**不是**对你的构建的验证：要重新构建、复查并再次评分。添加示例时除非加 `--force`，否则绝不覆盖已有文件。

要从示例制作新效果，把源码复制为新 ID（重命名文件和 `effect('...')` 中的名称，以及简报的 `effect_id`），然后改变形状、运动和节奏 ——
而不只是颜色（见 [craft](craft.md)）。保持飞行体/命中配对一致：命中效果的 `delivery.projectile` 必须写飞行体的 ID。
