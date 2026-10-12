# 在 Godot 中使用效果

`vfx init` 生成 `vfx/godot/`，这是一个 Godot 4 项目，包含官方 Effekseer 插件、`Vfx` autoload、每个实例一个的 `CombatVfxHandle`
以及 VfxLab 场景。只有在维护本技能时才修改技能中 `assets/godot-lab/` 副本里的运行时逻辑；在游戏项目中，把 `scripts/Vfx.gd`、
`scripts/VfxHandle.gd`、`effects/` 文件夹（连同 `resources/`）和 `vfx_manifest.json` 按相同的 `res://` 路径复制到游戏里（`Vfx.gd` 读取
`res://vfx_manifest.json`），在那里启用 Effekseer 插件，并注册 autoload：项目设置 → 全局 → 自动加载，或在 `project.godot` 的 `[autoload]`
下写 `Vfx="*res://scripts/Vfx.gd"`。不注册的话 `Vfx.play()` 不存在。

## API

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position, rotation, effect_scale)   # rotation in radians
Vfx.set_speed(0.5)      # all active effects, 0.05–4
Vfx.set_paused(true)
handle.stop()           # immediately
handle.release()        # stop emitting; live particles finish, then it frees itself

# Projectiles: flight time from the manifest unless options.speed (m/s) or options.flight (s); options.arc lifts it.
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

要点：`rotation` 的单位是弧度；`Vfx.set_speed` 作用于所有活动效果，范围 0.05–4；`handle.stop()` 立即停止；`handle.release()`
停止发射，存活的粒子播完后自动释放。飞行体的飞行时间取自 manifest，除非指定 `options.speed`（m/s）或 `options.flight`（s）；
`options.arc` 让它抬升。

有限时长的效果在 `duration` 之后自行清理；循环效果一直重播，直到 `stop()`。manifest（`vfx_manifest.json`）包含 `id`、`duration`、
`peak`、`impact`、`light`、`delivery`、`flight`、`arc`、`hold`、`inputs`、`scale`、`attach` 和 `design`；Lab 用 `impact`/`light`/`peak`
驱动舞台闪光和镜头抖动，这些需要你的游戏自己实现。

## 光束

用 `beam()` 构建的配方（manifest 中 `delivery.kind == "beam"`）是一个持续效果，它的长度和功率由游戏通过其 `bind` 方程读取的输入来驱动
（`@In0` 是以世界单位计的长度，`@In1` 是 0–1 的功率）：

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth.global_position, target_point)   # ignites: power 0 -> 1
func _process(_delta):
	if is_instance_valid(ray) and not ray.released:
		ray.aim(mouth.global_position, raycast_hit_point)   # every frame: sweep, follow the head, stop at walls
# when the breath ends:
ray.release()           # the beam narrows (power -> 0) and its last instances fade; the handle frees itself
```

（`Vfx.beam()` 点燃光束，功率 0 -> 1；每帧调用 `aim()`：扫动、跟随头部、停在墙上；吐息结束时调用 `release()`：光束变细（功率 -> 0），
最后的实例淡出，handle 自行释放。）

`aim(from, to)` 把 handle 放在 `from`，把它的 +Y 转向 `to`，并把 `@In0` 设为以效果自身单位计的距离（缩放过的 handle 会除以它的缩放）。
`options.ignite` / `options.fade`（秒）设置功率的渐变；`handle.set_input(index, value)` 驱动配方绑定的任何其他输入。火花、蒸汽和焦痕
在世界空间中发射，所以扫动的光束会沿路径留下它们。让终点来自物理射线检测，光束就会停在它击中的表面上；想要单独表面命中效果的游戏，
仍然可以在该点再播放一个效果。

每个 handle 从 manifest 的 `inputs` 默认值开始，创建后立刻、之后每帧都把它的 `inputs` 推送给发射器，所以第一帧就用上真实的值。

## 放大的效果

用 `scale` 构建的效果（manifest 的 `scale.world`，见 [scale](scale.md)）已经是世界单位：以缩放 1 播放它。确保游戏的 Effekseer 上限
能容纳怪兽尺寸的效果库（`project.godot` 中 `[effekseer]` 的 `instance_max_count`、`square_max_count`；Lab 用 2000 / 8000），
并且镜头的远裁剪面覆盖整个效果。

## 软粒子

带 `soft` 的层在与不透明几何体相接处淡出。它们需要 Forward+ 渲染器的深度纹理（已验证；Mobile 也有深度纹理，但未经验证）；
在 Compatibility 下它们几乎看不见。透明表面（水）除非写入深度，否则不在深度纹理中。

## Lab

`vfx showcase`（或 `godot --path vfx/godot`）打开 Lab：两个假人 PLAYER 和 TARGET 相对而立，每个效果按它的 `delivery` 演出 ——
`self` 在施法者身上，`melee` 在出招时打在目标身上，`projectile` 从施法者飞向目标并在到达时播放命中，`targeted` 降落在目标身上，
`area` 以 Boss 重击为中心，`beam` 从施法者的口部射向目标前方的地面，再扫到目标胸口（如果 `delivery.charge` 指定了蓄力，就在蓄力之后）。
舞台随所选效果的 `scale.world` 缩放：怪兽效果在 70 m 高的假人之间演出，镜头按相同倍数拉远。按键：←/→ 切换，Space 重播，C 切换对战/单目标舞台，L 循环，P 暂停，1–4 速度，B 背景，S 自动展示。
`-- --no-glow` 关闭 HDR 泛光以便对比。

假人是胶囊体。可以用可选的绑骨替身角色替换它们：把 `player.glb` 和 `target.glb`（约 1 个单位高，Mixamo 风格的骨骼名称，
动作片段命名为 `idle`、`cast_a_spell`、`box_03`、`hit_to_head`、`hit_to_body_01`、`jump`）以及可选的 `<name>.materials.json`
部件 → 着色用途映射放进 `vfx/characters/`，然后运行 `vfx init`。更换假人会改变舞台：要重新渲染基线并重新测量泛光阈值（见
[引擎约定](engine-conventions.md)）。

## 检查

`godot --path vfx/godot --fixed-fps 60 --script res://scripts/TestApi.gd` 针对当前 manifest 测试播放、发射、光束（瞄准、功率、释放）、暂停、速度、循环和自动回收。
`godot --headless --path vfx/godot --script res://scripts/ExportRuntime.gd` 导出 Godot 运行时资源。只有实际运行过之后，才能报告它们通过。
