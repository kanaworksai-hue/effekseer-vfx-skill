extends Node
## Game-facing Effekseer API. All effect internals stay behind this autoload.
var manifest: Array = []
var effects: Dictionary = {}
var active: Array[CombatVfxHandle] = []
var speed: float = 1.0
var paused: bool = false

func _ready() -> void:
	manifest = JSON.parse_string(FileAccess.get_file_as_string("res://vfx_manifest.json"))
	for item in manifest:
		effects[item.id] = item

func play(id: String, position: Vector3, rotation: Vector3 = Vector3.ZERO, effect_scale: Vector3 = Vector3.ONE, options: Dictionary = {}) -> CombatVfxHandle:
	if not effects.has(id):
		push_error("Unknown VFX: " + id)
		return null
	var resource: EffekseerEffect = load(effects[id].file)
	if resource == null:
		push_error("VFX resource failed to load: " + id)
		return null
	var handle := CombatVfxHandle.new()
	get_tree().current_scene.add_child(handle)
	handle.global_position = position
	handle.global_rotation = rotation
	handle.scale = effect_scale
	handle.speed = speed
	handle.paused = paused
	active.append(handle)
	handle.tree_exiting.connect(func(): active.erase(handle))
	handle.start(resource,bool(options.get("loop",effects[id].loop)),float(effects[id].duration))
	return handle

## Fire a projectile effect from `from` to `to`. Flight time is the manifest `flight` unless
## options.speed (m/s) or options.flight (s) is given; options.arc lifts the path (lobbed shots).
## Connect to the handle's `arrived` signal to play the impact; the trail releases itself on arrival.
func launch(id: String, from: Vector3, to: Vector3, options: Dictionary = {}) -> CombatVfxHandle:
	var handle := play(id, from, Vector3.ZERO, Vector3.ONE, {"loop": false})
	if handle == null: return null
	var item: Dictionary = effects[id]
	var seconds := float(options.get("flight", item.get("flight", 0.5)))
	if options.has("speed"): seconds = from.distance_to(to) / maxf(float(options.speed), 0.01)
	handle.fly(from, to, seconds, float(options.get("arc", item.get("arc", 0.0))))
	return handle

func stop_all() -> void:
	for emitter in active.duplicate():
		if is_instance_valid(emitter):
			emitter.stop()
	active.clear()

func set_speed(value: float) -> void:
	speed = clampf(value, 0.05, 4.0)
	for emitter in active:
		if is_instance_valid(emitter): emitter.speed = speed

func set_paused(value: bool) -> void:
	paused = value
	for emitter in active:
		if is_instance_valid(emitter): emitter.paused = paused
