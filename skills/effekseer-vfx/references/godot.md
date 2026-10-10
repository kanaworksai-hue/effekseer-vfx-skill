# Using the effects in Godot

`vfx init` generates `vfx/godot/`, a Godot 4 project with the official Effekseer plugin, the `Vfx` autoload, a
`CombatVfxHandle` per instance and the VfxLab scene. Edit runtime logic in the skill's `assets/godot-lab/` copy only
when you maintain the skill; in a game project, copy `scripts/Vfx.gd`, `scripts/VfxHandle.gd`, the `effects/` folder
(with `resources/`) and `vfx_manifest.json` into the game at the same `res://` paths (`Vfx.gd` reads
`res://vfx_manifest.json`), enable the Effekseer plugin there, and register the autoload: Project Settings → Globals →
Autoload, or `Vfx="*res://scripts/Vfx.gd"` under `[autoload]` in `project.godot`. Without it `Vfx.play()` does not
exist.

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

Finite effects clean themselves up after `duration`; looping effects replay until `stop()`. The manifest
(`vfx_manifest.json`) carries `id`, `duration`, `peak`, `impact`, `light`, `delivery`, `flight`, `arc`, `attach` and
`design`; the Lab uses `impact`/`light`/`peak` for its stage flash and camera kick, which your game implements itself.

## The Lab

`vfx showcase` (or `godot --path vfx/godot`) opens the Lab: two dummies, PLAYER and TARGET, face each other and every
effect is performed according to its `delivery` — `self` on the caster, `melee` on the target at the strike,
`projectile` flying from caster to target with its impact on arrival, `targeted` called down on the target, `area`
centred on a boss slam. Keys: ←/→ switch, Space replay, C combat/isolated stage, L loop, P pause, 1–4 speed,
B background, S auto showcase. `-- --no-glow` disables the HDR bloom for comparison.

The dummies are capsules. Optional rigged stand-ins replace them: put `player.glb` and `target.glb` (about 1 unit
tall, Mixamo-style bone names, clips named `idle`, `cast_a_spell`, `box_03`, `hit_to_head`, `hit_to_body_01`, `jump`)
and optional `<name>.materials.json` part-to-role maps in `vfx/characters/` and run `vfx init`. Changing the dummies
changes the stage: re-render baselines and re-measure the bloom threshold (see
[engine conventions](engine-conventions.md)).

## Checks

`godot --path vfx/godot --fixed-fps 60 --script res://scripts/TestApi.gd` exercises play, launch, pause, speed, loop
and auto-recycling against the current manifest. `godot --headless --path vfx/godot --script res://scripts/ExportRuntime.gd`
exports Godot runtime resources. Report these as passing only after running them.
