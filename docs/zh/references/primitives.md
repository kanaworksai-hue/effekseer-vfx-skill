# 配方代码与基元

目录：配方文件 · `effect()` 字段 · 基元 · 辅助函数 · 层字段 · 单位

## 配方文件

一个文件一个效果：`vfx/src/VFX_<Name>.py` 定义 `recipe()`，返回 `effect('<Name>', ...)`。ID `VFX_<Name>` 必须与文件名一致。
以 `_` 开头的文件是共享辅助模块（`from _palette import *`）。每条命令都会重新加载源码。`from vfxkit.primitives import *`
会引入所有基元、下面的辅助函数，以及 `WHITE`、`fade`、`ramp`、`walk` 和 `math`。

每个基元都返回一个普通的 layer dict；用 `| dict(...)` 覆盖或添加任意字段。纹理按文件名主干命名（`'T_Glow01'`），
在 `vfx/textures/processed/` 中解析。层按列表顺序绘制：**后面的层画在上面**（Godot 插件在效果层之间忽略 ZWrite）。

## `effect()` 字段

`effect(id, name, category, element, duration, layers, attach='impact', peak=.1, impact=0, light=(1,.85,.6), loop=False, design='', delivery=None, flight=None, arc=None, hold=None, inputs=None, scale=None)`

| 字段 | 含义 |
|---|---|
| `category` | `hit`、`slash`、`projectile`、`element`、`status`、`boss` 等（决定 lint 预算） |
| `element` | `physical`、`fire`、`ice`、`lightning`、`dark`、`holy`、`poison` 等（用于元素差别和运动检查） |
| `duration`、`peak` | 秒；`peak` 是 Lab 闪光、镜头抖动和目标反应所用的接触/释放时刻 |
| `attach` | 锚点：`ground`、`body`、`impact`、`caster`、`caster_ground`、`projectile` |
| `impact`、`light` | Lab 舞台闪光和镜头抖动的强度（0–1）和 RGB（仅用于演示舞台） |
| `delivery` | 游戏如何演出它：`SELF`、`MELEE`、`TARGETED`、`dict(kind='area')`；飞行体本身用 `dict(kind='projectile')`，它的命中用 `dict(kind='projectile', projectile='VFX_X')`；持续光束用 `BEAM` 或 `dict(kind='beam', charge='VFX_X')`（Lab 会先播放蓄力） |
| `flight`、`arc` | 仅飞行体：参考飞行秒数和抛射高度（米） |
| `hold` | 仅光束：Lab 在释放前持续发射它的秒数；`infinite` 的层一直发射到那时 |
| `inputs` | `bind` 方程读取的游戏输入 `@In0..@In3` 的默认值；光束用 `beam_inputs(length)` |
| `scale` | `'giant'`、`'kaiju'`、一个数字或 `{'world','time','budget'}`：为更大的世界构建角色尺度的配方（[scale](scale.md)） |
| `design` | 一句话描述玩家看到什么；显示在 Lab 中，并提供给评审 |

## 基元

**先想体积，再想纹理。** 主体、冲击波、晶体和光柱应该是位于倾斜 3D 平面中的网格或环，而不是面向镜头的卡片。
面向镜头的 sprite 留给本来就属于屏幕空间的东西：接触星芒、光晕、火花和烟团（叠加出体积）。

| 基元 | 用途 | 关键原生功能 |
|---|---|---|
| `flash` / `glow` | 接触星芒、形状下方的柔和光晕 | 单值 F-Curve 缩放 |
| `shadow` | 加色核心后面的暗衬底 | Blend 柔和圆盘，在闪光后 1–2 帧达到峰值 |
| `radial_sparks` | 火花、针刺、上升条纹 | 球形/圆形发射 + 缓动的 `travel` + DirectionalBillboard |
| `spark_burst` | 三档的命中/爆炸火花 | 长而快的条纹（6–10 帧）、主体、约 20 % 的重火花，给定 `floor` 时会弹跳 |
| `motes` | 余烬、冰尘、魔法微粒、向内汇聚 | 同上 + 湍流力场 |
| `shock_ring` / `tilted_ring` | 冲击波、上升光环、收缩环；位于 3D 平面中的环 | Ring 渲染器，内径缓动；近战倾角 `(0,58,0)` 横跨从左到右的打击 |
| `slash_arc` | 刀弧 | Crescent Ring，起止角缓动扫掠 + 溶解 |
| `wisps` | 断续的能量笔触、漩涡丝、贴地火舌 | Crescent Ring + `T_WispTrail01`，每次发射随机倾角和尺寸，侵蚀从大于 0 开始，因此绝不会是完整的环 |
| `orbit_band` | 吸积盘、环绕的符文环 | 倾斜平面中的 Ring，噪声绕环流动；`arc=(-90,90)` 为远半环，`(90,270)` 为近半环 |
| `smoke` | 烟、雾、尘、暗色残留 | 手绘烟雾序列帧 `T_SmokeSheet01` + 轻度侵蚀；单张静态烟团用 `texture='T_Smoke02'` —— 冰雾保留静态烟团，以区别于火的翻滚烟雾 |
| `billow` | 火球、与烟相同的翻滚团块 | 单次播放的手绘 4×4 序列帧 `T_ExplosionSheet01` + `ramp` 颜色节点 |
| `flame` | 火舌、火墙、地面火 | 从底部生长的爆炸序列帧，从白 → 本色 → 暗色冷却，被噪声侵蚀并带热边（不用剪贴画式的火焰剪影） |
| `decal` | 法阵、裂纹、焦痕 | 地平面 sprite，开启深度测试 |
| `standing` | 尖刺、闪电、光束 | 以底部为枢轴的 YAxisFixed sprite |
| `column` | 光柱、光环 | 程序化圆柱 + 滚动条纹 + 静态 alpha 渐变 + fresnel |
| `mesh` | 球体、圆锥、圆柱 | 程序化模型 + falloff；额外的程序化字段用 `model={...}` |
| `crystal` | 冰刺、碎片、冰枪 | 收尖的六棱圆柱 + 细胞纹理 + fresnel 边缘 |
| `shell` | 冲击泡、内爆、释放 | 只绘制正面，fresnel `pow<1` 只照亮边缘，缓动扩张 |
| `shell_fragments` | 壳的真实几何破碎 | 六片部分球面（AngleBeginEnd），彼此分离并翻滚 |
| `heat_haze` / `distortion_ring` | 热浪扭曲、折射冲击波 | `BackDistortion` 屏幕折射 |
| `slice_line` | 释放时的长细线 | `T_Streak01` 从 35 % 射到全长，同时变细；`width` 是可见粗细 |
| `spray(end)` / `debris` | 沿射击方向的定向喷射、翻滚的暗色碎块 | 不旋转的发射 + 世界方向的 `travel` 盒；Blend `T_Shard01` 带重力，可以落地 |
| `decay(layer, color)` | 光 → 灰烟残影 | 复制为 Blend 灰色，晚 `lag` 帧，寿命 × `stretch`，无 emissive，流动更慢 |
| `beam(name, core, body, rim, width=.5, ...)` | 由游戏瞄准和扫动的持续光束（吐息武器、激光、死光） | 轴向 billboard（`YAxisFixed`，枢轴在底部），通过 `bind` 拉伸到 `@In0` 并按 `@In1` 加宽；`T_BeamSection01` 截面、向外流动的噪声、口部与末端闪光、末端火花，可选的 `steam` 和 `scorch` 留在世界空间中（[godot](godot.md#光束)） |
| `charge_chain(name, anchors, color, hot, step=4, ...)` | 依次点亮一串点的电弧（背鳍骨板、线圈、地脉） | 每个锚点在 `delay + i*step` 处的节点光晕 + 弹出；手绘 `T_ArcStrand01` 电弧放在 `DirectionalBillboard` 上，由一个察觉不到的速度瞄准下一个锚点，每 `restrike` 帧镜像重新击出一次，直到 `until` |

## 辅助函数

| 辅助函数 | 含义 |
|---|---|
| `ramp((0,c0),(30,c1),(100,c2))` | 用 3–5 个节点描述随寿命变化的颜色 → `color_curve`（两色插值读起来只是一层色调） |
| `fade(color, alpha=0)` | 相同的 RGB，新的 alpha |
| `POP`、`DISSOLVE` | 先弹出再缓慢漂移的缩放曲线；先保持（ease-in）再侵蚀的 cutoff 缓动 |
| `sustain(layer, interval)` | 飞行体发射器：每 `interval` 帧一个实例，直到释放 |
| `held(layer, interval)` | 持续的交叉淡化：每 `interval` 帧一个实例，每个实例在 `interval` 内淡入并淡出，因此总有两个重叠且总和恒定（没有循环接缝的稳定光束） |
| `beam_inputs(length, power=1)`、`BEAM_LENGTH`、`BEAM_POWER`、`BEAM` | 光束的默认输入、其 bind 方程使用的 `@In0`/`@In1` 名称，以及它的 delivery |
| `TRAIL` | 只在创建时继承位置/旋转/缩放：该层留在路径上 |
| `slash_set(colors, roll, sweep=(110,260), radius=1.5, offset=(0,0,.5), lean=-18, delay=1, life=14)` | 一把刀刃的三种宽度：晚两帧出现的宽而暗的残影、饱和的主体、细的白热边（`slash_arc`），一道折射弧，以及一个手绘赛璐璐月牙（`T_Slash02`，`billboard='Fixed'`，位于刀刃所在平面，按实测的 `SLASH02_BULGE` 旋转）；`colors` = (残影, 主体, 热边) |
| `swing(layers, yaw, pitch=0)` | 把刀刃层包进一个 `renderer='None'` 枢轴，让弧在 3D 空间中劈过；约 ±30–40° 的 yaw 读起来是椭圆，而不是屏幕上的月牙 |
| `contrast_pair(layer)` | 一个固定的 sprite 加上一个几何完全一致的 Blend 衬底（见 [layering](layering.md)） |
| `lifetime(layer)`、`budget(layer)` | 一个层或其子层可能存活的最后一帧；实例数 |

## 层字段

除 PVA、缩放和颜色之外，编译器还支持：`collide`（地面弹跳）、`soft`（粒子与不透明几何体相接处的淡出距离，世界单位；已在 Forward+ 中验证，见引擎约定）、
`bind`（每帧根据游戏输入重新计算的位置/缩放，见下文）、`size` / `size_end` / `size_curve`（统一缩放）、
`color_end`、`color_curve`、`travel`（缓动位移）、`spawn`（球形、圆形、线形发射器）、`forces`（重力、湍流、涡旋）、
`alpha_texture` + `cutoff` + `edge`（带热边的溶解）、`distortion_texture`、`blend_texture`、`falloff`（fresnel）、`flipbook`、`pivot`、
`ring{...}`、`inherit`、`track_size`、`material`（`BackDistortion`）、`children`。`vfx layer-schema` 列出所有接受的键；
未知的键会报错并给出拼写建议。其他任何东西都必须连同 save/open 回读测试一起加进编译器，而不是在配方里写裸属性路径（流程见 [引擎约定](engine-conventions.md#扩展编译器)）。

### `bind`：由游戏驱动的值

`bind={'position': [x, y, z], 'scale': [x, y, z]}` 把层的位置或缩放替换为一个 Fixed 向量，由 Effekseer 动态方程根据游戏输入
`@In0..@In3`（Godot 中的 `handle.set_input()` / `Vfx.beam()`）**每帧**重新计算。每个分量可以是数字、方程字符串（`'@In0'`、`'@In0 * 0.5'`）
或乘积 `[k, '@In1']`，其中常数 `k` 随配方的世界尺度缩放，而输入保持为世界值。配方必须用 `inputs=[...]` 为它读取的每个输入给出默认值。
绑定的缩放不能与 `size`/`scale_*` 字段组合，绑定的位置不能与 `travel`/`velocity` 组合；子层跟随绑定的父层。

## 单位

层的 `life`、`delay`、`interval`：60 FPS 帧数。速度和加速度：单位/帧；重力：单位/帧²。角度：度。颜色：RGBA 0–255。
曲线（`size_curve`、`color_curve` 等）：`[[percent_of_life, value], ...]`。`cutoff`（溶解阈值，0..1）可以是数字（固定）、`dict(start=a, end=b, easing='Linear')`（在粒子生命周期内变化，`EaseIn*` 会先保持形状），或者曲线（编译器会拟合为最接近的缓动）——FCurve 阈值在 Godot 中不会变化（见[引擎约定](engine-conventions.md)）。manifest 的 `duration` 和 `peak`：秒。
随机范围写作 `[min, max]`。
