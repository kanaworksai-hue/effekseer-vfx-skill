class_name CombatVfxHandle
extends Node3D
## One controllable game VFX instance. Finite effects clean themselves up;
## looping effects replay their complete recipe until stop() is called.
## Projectiles fly() to a point, emit `arrived` there and release() their trail.
signal arrived(position: Vector3)
var emitter: EffekseerEmitter3D
var loop_enabled: bool = false
var duration: float = 1.0
var elapsed: float = 0.0
var released: bool = false
var flight_from := Vector3.ZERO
var flight_to := Vector3.ZERO
var flight_time: float = 0.0
var flight_arc: float = 0.0
var flight_elapsed: float = -1.0
var speed: float = 1.0:
	set(value):
		speed = value
		if is_instance_valid(emitter): emitter.speed = value
var paused: bool = false:
	set(value):
		paused = value
		if is_instance_valid(emitter): emitter.paused = value

func start(resource: EffekseerEffect, loop_value: bool, duration_value: float) -> void:
	loop_enabled = loop_value
	duration = duration_value
	emitter = EffekseerEmitter3D.new()
	emitter.autoplay = false
	emitter.autofree = false
	emitter.effect = resource
	add_child(emitter)
	emitter.speed = speed
	emitter.paused = paused
	emitter.finished.connect(_finished)
	emitter.play()

## Move from `from` to `to` in `seconds` of effect time, lifted by `arc` metres at the midpoint.
## Trail layers spawn in world space, so the path stays behind the head.
func fly(from: Vector3, to: Vector3, seconds: float, arc: float = 0.0) -> void:
	flight_from = from
	flight_to = to
	flight_time = maxf(seconds, 0.01)
	flight_arc = arc
	flight_elapsed = 0.0
	global_position = from

func _process(delta: float) -> void:
	if paused: return
	elapsed += delta * speed
	if flight_elapsed >= 0.0:
		flight_elapsed += delta * speed
		var p := minf(flight_elapsed / flight_time, 1.0)
		global_position = flight_from.lerp(flight_to, p) + Vector3.UP * flight_arc * 4.0 * p * (1.0 - p)
		if p >= 1.0:
			flight_elapsed = -1.0
			arrived.emit(flight_to)
			release()
	if loop_enabled and elapsed >= duration:
		elapsed = fmod(elapsed,duration)
		emitter.stop()
		emitter.play()

func _finished() -> void:
	if not loop_enabled: queue_free()

## Stop emitting but let live particles finish (trails, embers); frees itself when they are gone.
func release() -> void:
	loop_enabled = false
	released = true
	if is_instance_valid(emitter): emitter.stop_root()

func stop() -> void:
	loop_enabled = false
	if is_instance_valid(emitter): emitter.stop()
	queue_free()

func set_dynamic_input(index: int, value: float) -> void:
	if is_instance_valid(emitter): emitter.set_dynamic_input(index,value)

func send_trigger(index: int) -> void:
	if is_instance_valid(emitter): emitter.send_trigger(index)
