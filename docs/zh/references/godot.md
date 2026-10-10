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
`peak`、`impact`、`light`、`delivery`、`flight`、`arc`、`attach` 和 `design`；Lab 用 `impact`/`light`/`peak` 驱动舞台闪光和镜头抖动，
这些需要你的游戏自己实现。

## Lab

`vfx showcase`（或 `godot --path vfx/godot`）打开 Lab：两个假人 PLAYER 和 TARGET 相对而立，每个效果按它的 `delivery` 演出 ——
`self` 在施法者身上，`melee` 在出招时打在目标身上，`projectile` 从施法者飞向目标并在到达时播放命中，`targeted` 降落在目标身上，
`area` 以 Boss 重击为中心。按键：←/→ 切换，Space 重播，C 切换对战/单目标舞台，L 循环，P 暂停，1–4 速度，B 背景，S 自动展示。
`-- --no-glow` 关闭 HDR 泛光以便对比。

假人是胶囊体。可以用可选的绑骨替身角色替换它们：把 `player.glb` 和 `target.glb`（约 1 个单位高，Mixamo 风格的骨骼名称，
动作片段命名为 `idle`、`cast_a_spell`、`box_03`、`hit_to_head`、`hit_to_body_01`、`jump`）以及可选的 `<name>.materials.json`
部件 → 着色用途映射放进 `vfx/characters/`，然后运行 `vfx init`。更换假人会改变舞台：要重新渲染基线并重新测量泛光阈值（见
[引擎约定](engine-conventions.md)）。

## 检查

`godot --path vfx/godot --fixed-fps 60 --script res://scripts/TestApi.gd` 针对当前 manifest 测试播放、发射、暂停、速度、循环和自动回收。
`godot --headless --path vfx/godot --script res://scripts/ExportRuntime.gd` 导出 Godot 运行时资源。只有实际运行过之后，才能报告它们通过。
