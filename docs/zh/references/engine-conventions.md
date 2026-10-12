# 已验证的引擎约定（Effekseer Core 1.80.7 + EffekseerForGodot4 1.80.5.1）

下面每一条都在真实渲染中确认过。照原样使用；不要重新猜坐标轴、单位或混合行为。确认了新的约定时，把它连同测量方法一起补充到这里
（请补充到英文原文 `skills/effekseer-vfx/references/engine-conventions.md`）。

目录：角度与坐标轴 · 力与运动 · 网格与 fresnel · 纹理与序列帧 · 继承与寿命 · 游戏输入与动态方程 · 渲染、HDR 与 Lab · 锚点与放置 ·
扩展编译器

## 角度与坐标轴

- **Ring 角度**：0° 指向上方，90° 指向左方，逆时针递增。要让一段扫掠弧以锚点为中心，就把环的中心朝其扫掠中点的反方向偏移。
- **Sprite 的 Z 旋转**是逆时针的。绝不目测手绘形状的朝向：`vfx texture-info <name>` 会报告覆盖率、包围盒、贴边情况、主朝向，
  以及月牙形的弧顶凸出方向，采用同一约定（+x 为 0°，逆时针）。在配方中使用实测的角度。例如：`T_Slash02` 实测弧顶凸出为 108°，`slash_set()` 使用
  `SLASH02_BULGE = 105`；如果替换这张纹理，要重新实测并更新这个常量。
- **`billboard='Billboard'` 会忽略 Z 旋转**（`rotation=[0,0,90]` 的 sprite 仍然直立）。需要滚转的 sprite 使用默认的 `RotatedBillboard`。
- **`rotate=True` 的球形发射**：粒子的局部 +Y 指向外侧，所以 `travel.end=[0,d,0]` 向外飞，负值则向内吸。
- **`rotate=True` 的圆形发射（默认 Y 轴）不同**：Core 构造的是 `Translation(r,0,0)*RotationY(angle)`，所以局部 **+X** 指向外侧，
  +Y 仍然向上。沿地面向外滚动的烟需要 `travel.end=[[d0,d1],0,0]`；`[0,d,0]` 会把它变成笔直上升的柱子。`rotate=False` 时位移按世界方向计算
  （上升的粒子用它）。
- **`rotate=True` 的球形发射也会旋转 PVA `velocity`**：`velocity=[0, v, 0]` 沿每个粒子随机的出生方向飞，而不是向上。
  这样发射的烟柱向侧面漂移并下沉（复查的 `sinks` flag）；`spawn=dict(shape='Sphere', radius=[...], rotate=False)` 让 `velocity`
  保持世界方向。
- **轴向 billboard**：`billboard='YAxisFixed'` 配 `pivot='bottom'` 是一张从原点沿局部 +Y 延伸的面片，绕该轴旋转以面向镜头 ——
  这样的光束从任何角度看都保持宽度，只有正对着它的轴看时除外。`DirectionalBillboard` 让 +Y 对齐粒子的运动方向；
  配一个察觉不到的速度（1e-4 单位/帧，`charge_chain`），它不用欧拉角就能把一个静止的 sprite 瞄准任意点（实测：在弯曲脊背上的
  7 点链中，电弧连上了每一个锚点）。
- **`travel.end` 是绝对的局部位置**，不是相对 `position` 的偏移，而且 `rotate=True` 的发射也会旋转这个局部坐标系。
  把沿地面滚动的烟放在一个 `renderer='None'`、`position` 位于地面高度的枢轴下；需要按世界方向位移时用 `spawn rotate=False`（`spray`）。

## 力与运动

- **Drag 只衰减力场累积的速度，不衰减 PVA 速度。** "先爆出再悬停"必须用带 EaseOut 的 `travel`，而不是速度 + drag。
- **重力的单位是 单位/帧²。** 下落的火花 0.001–0.002，石块 0.004，上升的烟 0.0003–0.0006。再大一个数量级，粒子就会飞出画面
  （lint 拒绝大于 0.01 的值）。
- **地面碰撞 `collide`**：世界坐标系；`height` 是世界高度（Lab 地面是 0.02）。从 1.35 m 高的命中点出发、重力 0.0015 时，20 帧内什么都到不了地面，
  所以弹跳只对爆炸、Boss 重击和会落地的东西有意义。
- **Track + Circle 的 `Order` 发射做不出螺旋**：它每帧前进一段，所以在飞行速度下螺距被拉成一条扁平的锯齿线。改用在头部周围以随机倾角排布的 `wisps` 笔触。

## 网格与 fresnel

- **程序化圆柱和圆锥**沿其轴从 `DepthMin` 延伸到 `DepthMax`；`mesh()` 把它们立在原点上。**球体**使用 -1..1 的归一化 depth：
  用 `scale_start` 控制尺寸，绝不用 Depth。
- **Cone 尖端朝下**（底面在 +Y 端）。要做尖端朝上的晶体，用 `radius2≈0` 的 `Cylinder`（`crystal()` 就是这样做的）。
  `Mesh/Divisions/X=6` 生成六棱柱。`ShapeNoise/WaveNoisePower` 把球体变成凹凸不平的液团。大球体需要 `rings ≥ 24`，否则剪影会出现棱面。
- **程序化模型的 V 从上到下。** 滚动的颜色纹理必须可平铺（`T_NoiseStreak02`）；渐变放在不滚动的 alpha 纹理里（`T_GradientV01`），
  否则会出现硬接缝。
- **Falloff**：`begin` 是面向镜头的中心，`end` 是边缘，`pow` 越大，`begin` 区域**越小**（红/绿测试：pow 8 时几乎整个球都显示 `end`）。
  细亮边（fresnel、冲击壳）用 `pow` 0.25–0.5。用 `culling='Front'` 只绘制球体的正面（Effekseer 的命名：`Front` 显示正面；
  `Double` 会把内侧背面也当作边缘照亮，球就变成实心的）。护盾照亮边缘；光柱让边缘透明。
- **带颜色纹理或常驻 cutoff + edge 的 Model 层**，在 Godot 插件中用于壳球体时会渲染成灰色斑块。用纯色 + fresnel，只在到期时溶解；
  需要可见的破碎时，用 `shell_fragments`（真实几何），而不是对整个壳做 cutoff。
- 黑洞、暗球或蓄力**不要用面向镜头的"漩涡贴纸"**：用 `orbit_band` 把环放在倾斜平面里，并按绘制顺序叠放 ——
  远半环 → 核心（Blend 黑色圆盘或亮核心）→ 光子环 → 近半环 —— 这样近半部分会从核心前面经过。插件**在效果层之间忽略 ZWrite**
  （写深度的球体加上做深度测试的环没有任何效果）；遮挡只来自列表顺序。用 `alpha_scroll` 让环表面旋转，使条纹绕环流动，而不是用 Z 旋转。

## 纹理与序列帧

- **UV 扰动纹理必须是不透明的 RG 偏移图**（`T_Distort01/02`）。把白色带 alpha 的遮罩用作扰动图，什么也不会扭曲。
- **Alpha 纹理读取 alpha 通道**；每个 `T_Noise*` 遮罩都可以直接用于 `cutoff` 溶解。
- **溶解阈值只有写成 Easing 才会动。** 在 Godot 渲染中实测（EffekseerForGodot4 1.80.5.1，Lab 与 Mobile 渲染器游戏）：
  `AlphaCutoffParam/Type = FCurve`（Percent 或 Time 时间轴）时，阈值整个生命周期都停在第一个关键帧，形状永远不会被侵蚀；
  `Type = Easing` 时会正常变化，曲线形状由缓动类型决定（`Linear`、`EaseInQuadratic`、`EaseInCubic`、`EaseInQuartic`、
  `EaseInQuintic`、`EaseOut*`）。Core 会把起止阈值限制在 0..1，所以“先保持再侵蚀”要用 ease-in，而不是负的起始值。
  编译器总是写成 Easing：需要精确控制时写 `cutoff=dict(start=a, end=b, easing='EaseInQuadratic')`；写曲线
  `[[percent, value], ...]` 时，编译器会用最接近的缓动拟合（`cutoff_easing`）。仅靠读回无法发现这个问题，要看条带图。
- **序列帧整数**：`flipbook.frame_length`、`x` 和 `y` 是 Core 的整数属性，必须是正整数（4.5 会被原生拒绝；字段校验器会先拦下它）。
  要延长播放，就同时调整整数的帧长度和寿命。
- **序列帧上不能用 UV 扰动**：`distortion_intensity` 以整张纹理的 UV 计量，所以在 4×4 图集上 0.12 会偏移半格，采样到相邻帧 ——
  火焰会被切成硬边的方块。lint 会拒绝；需要扰动时用单帧纹理。
- **序列帧图集**：图像模型可以生成一整张 4×4 序列（1024²，每格 256²），连续性可用。用
  `vfx process-texture <original> <output> --size 1024 --grid 4 4` 处理：各格保持原位（不裁切、不重新居中，否则动画会抖动），
  每格边缘做羽化以防渗色。`frame_length` ≈ life / 16；单次播放用 `loop='Once'`，循环火焰用 `Loop` 加随机起始帧。
- **一张爆炸图集，两层**：加色火焰（ramp 白 → 黄 → 橙 → 暗红 → 消失）加上一个延迟约 8 帧的 Blend 暗烟层。烟必须**排在火之前**
  （画在火的后面），否则会在火球上打出一个黑洞。
- **侵蚀边缘颜色**叠加在冷却后的红色上；偏黄的边缘会变成橄榄色。火焰用 `(255,80,15)`，`scaling≈2`。
- **丝状笔触纹理**：手绘笔触带按行在全宽范围内裁切（这样可以横向平铺），缩放到 512×256，alpha = 亮度。默认的居中处理会添加左右留边，破坏平铺。

## 继承与寿命

- **继承**：Core 默认的 `LocationEffectType` 是 `Already`（每帧跟随父级）。`WhenCreating` 只在出生时取父级变换，
  所以 handle 移动时粒子留在原地 —— 飞行体拖尾依赖这一点。`renderer='Track'` 把同一层的相继实例连成一条带；配合 `WhenCreating` 就是一条连续的拖尾。
- **`EffekseerEmitter3D.stop_root()`** 停止新的发射；已有的粒子各自走完寿命之后才触发 `finished`。
- **子层时间**：子层的生成从其父实例的创建开始计时，而不是从它的消亡开始。`renderer='None'` 的父层可以旋转它的子层，
  子层再用 `travel` 缓动到中心，就形成螺旋内落。
- **随机尺寸不能配曲线**：随机的 `size` / `scale_start` 范围与 `size_curve` / `scale_curve` 组合会编译失败（编译器把曲线乘以固定的起始缩放；
  lint 会拒绝）。用第二层来变化尺寸。

## 游戏输入与动态方程

- **`bind` 在 Godot 插件中于运行时生效。** 带动态方程（`@O.y = @In0`）的 Fixed 位置或缩放每帧都会重新计算：一个探针在正在播放的
  handle 上把 `@In0` 从 3 改到 9 再改到 5，光束的长度和末端闪光在 2 帧内跟上；旋转发射器会重新瞄准它。编译器把方程写进
  `Core.Dynamic.Equations`（相同的代码共用一条），并在 save/open 之后检查它们。
- **新 handle 从 .efk 中的输入默认值开始**（配方的 `inputs`）：在第一帧模拟时，怪兽光束命中点的喷溅出现在默认的 160 m 处，
  而不是真实的终点。因此 `Vfx.play()` / `Vfx.beam()` 在创建 handle 后立刻推送它的输入，`CombatVfxHandle` 之后每帧再推送一次。
  （早期探针看到 0，只是因为它的 .efk 没有保存默认值。）
- **持续主体**：光束主体是一个 `held()` 交叉淡化（每个间隔一个实例，寿命 2×间隔，淡入淡出各一个间隔），而不是一个长寿命的实例，
  所以 `release()`（`stop_root()`）能按时结束它：在连拍中，怪兽光束在释放后约 15 帧内变细并消失，`TestApi.gd` 会检查
  释放后的光束会自行释放。

## 渲染、HDR 与 Lab

- **屏幕扭曲 `material='BackDistortion'`** 在 Godot 插件中可用（`hint_screen_texture`）；`distortion` 是强度（0.4–1.2）。
  它只折射不透明物体（地面、假人），不折射其他效果层。在暗色的纯色舞台上，它只在地面环和假人边缘上显现 —— 要放大帧才能看到。
  关掉扭曲时效果也必须成立。
- **Lab 舞台与 HDR 泛光**：默认舞台是受光的深石板蓝（背景 `1a2433`，地面 `1d2733`，ambient 0.75，key 1.5，fill 1.0）。
  在 Forward+ 中，插件的加色 / emissive 输出进入 HDR 缓冲。用受光的替身角色测得，假人高光峰值约 3.4×，而效果核心超过 8×，
  所以 Glow 按 `smoothstep(threshold, threshold + hdr_scale)` 从 2.8 开始渐入、到 6.0 完全开启，intensity 1.5，strength 1.1，
  在 tonemapping 之前加色叠加，五级模糊 1.0/1.0/0.85/0.6/0.35，Filmic white 4 让核心更早烧白，`glow_bloom=0`。
  这些数值是用带光照、卡通着色的替身角色测得的；默认 Lab 的胶囊假人尚未据此重新测量，因此把阈值当作起点，
  在改变舞台亮度、假人光照或替身角色之后，先重新测量假人峰值（线性 tonemap，在曝光 1/8 下读回），再移动阈值。`godot --path vfx/godot -- --no-glow` 关闭后处理以便对比。
  配方基元 `glow()` 是一个纹理层，不是这个 HDR 后处理。舞台改动之后重新渲染整个总览。
- 在强泛光下，接触本来就该白热的效果会在峰值帧报告 `washed out`；它只持续 1–3 帧 —— 看连拍判断，不要为了消掉这个 flag 而削弱接触。
- **软粒子 `soft` 在 Forward+ 中可用**（EffekseerForGodot4 1.80.5.1、Godot 4.7.2）。插件的着色器采样 `hint_depth_texture`，
  在不透明深度前方 `soft` 个世界单位的范围内让粒子淡出。在半埋进 Lab 地面、开启深度测试的卡片上实测：没有 `soft` 时，
  亮度在地面线处一个像素内从 206 降到 81；`soft=0.3` 时在约 9 个像素内渐变为 198 → 188 → 169 → 124 → 81；悬在空中的卡片
  有无 `soft` 颜色完全相同（216, 198, 155）。接近粒子尺寸的 `soft` 会让整张卡片淡出（lint 会警告）。深度纹理中只有不透明几何体：
  透明的水面必须写入深度（或有一个不透明的深度预渲染 pass），烟才能在它上面柔化。Compatibility 渲染器没有深度纹理：
  在早期的 Lab 中，`soft` 在那里让 sprite 几乎完全透明 —— 不要在 Compatibility 下使用它。
- **放大后的舞台闪光**：Godot 的 omni 光按 1/距离衰减（attenuation 1），所以 Lab 把闪光能量乘以舞台缩放，而不是它的平方
  （用平方时，一次怪兽命中把整个舞台都冲白了）。

## 锚点与放置

- Lab 锚点：`body` 距地面 0.95 m，`impact` 1.35 m，`ground` 0。以 `body` 为锚点的效果中，地面层位于约 `y = -0.93`，以 `impact` 为锚点的效果中位于约 `y = -1.3`；
  写得更低的话，做深度测试的贴花会消失在地面之下。
- 横跨打击方向的近战冲击环用 `tilt=(0,58,0)`：与从左到右的攻击垂直，在透视中看起来是一个竖直的椭圆。

## 扩展编译器

配方字段是 Effekseer 的一个精选子集。当某个效果需要编译器尚不具备的引擎功能时：

1. 制作一个带有该功能的参考节点（或打开一个已有该功能的效果），找出属性路径：
   `vfx discover` 把一个新节点的所有路径连同类型和枚举值导出到 `vfx/work/property_schema.json`；
   `vfx core property-list <file.efkefc> node/root/0` 列出一个真实节点的路径。
2. **先读再写**：用 `vfx core property-get <file> <path>` 读取当前值，然后 `vfx core property-set <file> <path> <json>`，
   再 `property-get` 一次，看 Core 实际保存了什么。曲线通过 `vfx core curve-list` / `curve-set`，渲染器面板通过
   `settings-list` / `settings-set`。
3. 只使用当前 Core 会保存的属性；不要依赖只在导入时读取的旧字段。
4. 把该功能作为层字段加入 `scripts/effekseer_ai/authoring.py`（它必须出现在 `vfx layer-schema` 中），并附带一个测试：
   编译一个层、保存、重新打开并读回该值。绝不把裸属性路径写进配方。
5. 渲染它，并把这条约定连同测量方法补充到本文件中。
