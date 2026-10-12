class_name CombatVfxHandle
extends Node3D
## One controllable game VFX instance. Finite effects clean themselves up;
## looping effects replay their complete recipe until stop() is called.
## Projectiles fly() to a point, emit `arrived` there and release() their trail.
## Beams aim() from a point at a point; the recipe's bind equations read the length (@In0) and power (@In1).
signal arrived(position: Vector3)
## Current values of the game inputs @In0..@In3, pushed to the emitter every frame (a value set before the
## native effect exists would otherwise be lost).
var inputs: Array[float] = [0.0, 0.0, 0.0, 0.0]
var beam_mode: bool = false
var beam_power: float = 1.0
var ignite_time: float = 0.08
var fade_time: float = 0.12
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

## Turn this handle into a beam: power ramps 0 -> 1 over `ignite` seconds and back to 0 over `fade` after release().
func start_beam(ignite: float, fade: float) -> void:
	beam_mode = true
	ignite_time = maxf(ignite, 0.0)
	fade_time = maxf(fade, 0.0)
	beam_power = 0.0 if ignite_time > 0.0 else 1.0
	inputs[1] = beam_power

## Point the effect's +Y axis from `from` to `to` and stretch its bound length (@In0) to the distance, in the effect's
## own units (a scaled handle divides by its scale). Call it every frame to sweep.
func aim(from: Vector3, to: Vector3) -> void:
	global_position = from
	var axis := to - from
	var length := axis.length()
	if length < 0.0001: return
	var y := axis / length
	var side := Vector3.UP if absf(y.dot(Vector3.UP)) < 0.98 else Vector3.RIGHT
	var x := side.cross(y).normalized()
	var z := x.cross(y)
	var size := scale
	global_basis = Basis(x * size.x, y * size.y, z * size.z)
	inputs[0] = length / maxf(size.y, 0.0001)

func set_input(index: int, value: float) -> void:
	inputs[index] = value

## Send the current inputs to the native effect now (Vfx.play/beam call it right after creating the handle, so the
## first frame does not use the .efk defaults).
func push_inputs() -> void:
	if not is_instance_valid(emitter): return
	for i in inputs.size(): emitter.set_dynamic_input(i, inputs[i])

func _process(delta: float) -> void:
	if paused: return
	if beam_mode:
		var step := delta * speed
		if released: beam_power = maxf(0.0, beam_power - step / maxf(fade_time, 0.001)) if fade_time > 0.0 else 0.0
		else: beam_power = minf(1.0, beam_power + step / maxf(ignite_time, 0.001)) if ignite_time > 0.0 else 1.0
		inputs[1] = beam_power
	push_inputs()
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
	inputs[index] = value
	if is_instance_valid(emitter): emitter.set_dynamic_input(index,value)

func send_trigger(index: int) -> void:
	if is_instance_valid(emitter): emitter.send_trigger(index)
