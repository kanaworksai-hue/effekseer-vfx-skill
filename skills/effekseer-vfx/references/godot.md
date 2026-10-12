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
(`vfx_manifest.json`) carries `id`, `duration`, `peak`, `impact`, `light`, `delivery`, `flight`, `arc`, `hold`,
`inputs`, `scale`, `attach` and `design`; the Lab uses `impact`/`light`/`peak` for its stage flash and camera kick, which your game implements itself.

## Beams

A recipe built with `beam()` (manifest `delivery.kind == "beam"`) is a held effect whose length and power the game
drives through the inputs its `bind` equations read (`@In0` length in world units, `@In1` power 0–1):

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth.global_position, target_point)   # ignites: power 0 -> 1
func _process(_delta):
	if is_instance_valid(ray) and not ray.released:
		ray.aim(mouth.global_position, raycast_hit_point)   # every frame: sweep, follow the head, stop at walls
# when the breath ends:
ray.release()           # the beam narrows (power -> 0) and its last instances fade; the handle frees itself
```

`aim(from, to)` places the handle at `from`, turns its +Y toward `to` and sets `@In0` to the distance in the
effect's own units (a scaled handle divides by its scale). `options.ignite` / `options.fade` (seconds) set the power
ramps; `handle.set_input(index, value)` drives any other input a recipe binds. Sparks, steam and scorch marks are
emitted in world space, so a sweeping beam leaves them along its path. Let the end point come from a physics ray
cast so the beam stops on the surface it hits; a game that wants a separate surface impact can still play another
effect at that point.

Every handle starts from the manifest's `inputs` defaults and pushes its `inputs` to the emitter right away and then
every frame, so the first frame already uses the real values.

## Scaled effects

An effect built with `scale` (manifest `scale.world`, see [scale](scale.md)) is already in world units: play it at
scale 1. Make sure the game's Effekseer limits fit kaiju-sized libraries (`[effekseer]` `instance_max_count`,
`square_max_count` in `project.godot`; the Lab uses 2000 / 8000) and that the camera's far plane covers the effect.

## Soft particles

Layers with `soft` fade where they meet opaque geometry. They need the depth texture of the Forward+ renderer
(verified; Mobile also has one but is unverified); with Compatibility they turn almost invisible. Transparent surfaces (water) are not in the depth
texture unless they write depth.

## The Lab

`vfx showcase` (or `godot --path vfx/godot`) opens the Lab: two dummies, PLAYER and TARGET, face each other and every
effect is performed according to its `delivery` — `self` on the caster, `melee` on the target at the strike,
`projectile` flying from caster to target with its impact on arrival, `targeted` called down on the target, `area`
centred on a boss slam, `beam` fired from the caster's muzzle at the ground in front of the target and raked onto its
chest (after the charge named in `delivery.charge`, if any). The stage scales with the selected effect's `scale.world`:
kaiju effects play between 70 m dummies with the camera pulled back by the same factor. Keys: ←/→ switch, Space replay, C combat/isolated stage, L loop, P pause, 1–4 speed,
B background, S auto showcase. `-- --no-glow` disables the HDR bloom for comparison.

The dummies are capsules. Optional rigged stand-ins replace them: put `player.glb` and `target.glb` (about 1 unit
tall, Mixamo-style bone names, clips named `idle`, `cast_a_spell`, `box_03`, `hit_to_head`, `hit_to_body_01`, `jump`)
and optional `<name>.materials.json` part-to-role maps in `vfx/characters/` and run `vfx init`. Changing the dummies
changes the stage: re-render baselines and re-measure the bloom threshold (see
[engine conventions](engine-conventions.md)).

## Checks

`godot --path vfx/godot --fixed-fps 60 --script res://scripts/TestApi.gd` exercises play, launch, beam (aim, power,
release), pause, speed, loop and auto-recycling against the current manifest. `godot --headless --path vfx/godot --script res://scripts/ExportRuntime.gd`
exports Godot runtime resources. Report these as passing only after running them.
