extends SceneTree
var failures: Array[String] = []
var manager: Node
var checks: int = 0
func _initialize() -> void:
	call_deferred("_run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value: failures.append(message)
func _run() -> void:
	var scene := Node3D.new()
	root.add_child(scene)
	current_scene = scene
	var camera := Camera3D.new()
	scene.add_child(camera)
	camera.position = Vector3(0,2,8)
	camera.look_at(Vector3(0,1,0))
	manager = root.get_node("Vfx")
	check(manager.manifest.size()>0,"manifest has effects")
	var first: String = manager.manifest[0].id
	var handle: CombatVfxHandle = manager.play(first,Vector3(1,1,0),Vector3(0,.3,0),Vector3(.8,.8,.8))
	check(is_instance_valid(handle),"play returns live handle")
	check(handle.global_position.is_equal_approx(Vector3(1,1,0)),"world position")
	check(handle.scale.is_equal_approx(Vector3(.8,.8,.8)),"scale")
	manager.set_speed(.5)
	check(is_equal_approx(handle.emitter.speed,.5),"speed propagation")
	manager.set_paused(true)
	check(handle.emitter.paused,"pause propagation")
	var time_before := handle.elapsed
	await create_timer(.2).timeout
	check(is_equal_approx(handle.elapsed,time_before),"paused simulation clock")
	manager.set_paused(false)
	manager.set_speed(1.0)
	await create_timer(float(manager.manifest[0].duration)+0.6).timeout
	check(not is_instance_valid(handle),"finite effect cleanup")
	check(manager.active.is_empty(),"active list cleanup")
	# The loop option replays any finite recipe until stop(); no dedicated looping asset is required.
	var loop_handle: CombatVfxHandle = manager.play(first,Vector3(0,1,0),Vector3.ZERO,Vector3.ONE,{"loop":true})
	await create_timer(float(manager.manifest[0].duration)*2.2).timeout
	check(is_instance_valid(loop_handle),"loop remains active across cycles")
	check(loop_handle.emitter.is_playing(),"native emitter restarted")
	manager.stop_all()
	await process_frame
	await process_frame
	check(not is_instance_valid(loop_handle),"stop loop cleanup")
	# Projectiles fly to the target, announce arrival there, then release their trail and free themselves.
	var projectile_id := ""
	for item in manager.manifest:
		if item.category == "projectile": projectile_id = item.id
	if projectile_id != "":
		var arrivals: Array[Vector3] = []
		var shot: CombatVfxHandle = manager.launch(projectile_id,Vector3(-2,1,0),Vector3(2,1,0),{"flight":0.3})
		shot.arrived.connect(func(p: Vector3): arrivals.append(p))
		await create_timer(0.15).timeout
		check(shot.global_position.x > -2.0 and shot.global_position.x < 2.0,"projectile moves along its path")
		await create_timer(0.3).timeout
		check(arrivals.size() == 1 and arrivals[0].is_equal_approx(Vector3(2,1,0)),"arrived fires once at the target")
		check(not is_instance_valid(shot) or shot.released,"projectile releases on arrival")
		await create_timer(float(manager.effects[projectile_id].duration)+0.5).timeout
		check(not is_instance_valid(shot),"released projectile frees after its trail dies")
	# Beams aim from a point at a point: the handle's +Y follows the target, @In0 carries the distance in the effect's
	# own units, power ramps up on ignition and down after release, and the handle frees itself afterwards.
	var beam_id := ""
	for item in manager.manifest:
		if item.get("delivery", {}).get("kind", "") == "beam": beam_id = item.id
	if beam_id != "":
		var origin := Vector3(-2, 1, 0)
		var ray: CombatVfxHandle = manager.beam(beam_id, origin, Vector3(2, 1, 0))
		check(is_instance_valid(ray) and ray.beam_mode, "beam returns a beam handle")
		check(is_equal_approx(ray.inputs[0], 4.0), "beam length input is the distance")
		check(ray.global_basis.y.normalized().is_equal_approx(Vector3.RIGHT), "beam +Y points at the target")
		await create_timer(0.5).timeout
		check(is_equal_approx(ray.inputs[1], 1.0), "beam power ramps to 1")
		ray.aim(origin, Vector3(-2, 4, 0))
		check(is_equal_approx(ray.inputs[0], 3.0) and ray.global_basis.y.normalized().is_equal_approx(Vector3.UP), "aim re-points and re-measures the beam")
		ray.release()
		await create_timer(0.5).timeout
		check(not is_instance_valid(ray) or (ray.released and ray.inputs[1] < 0.01), "released beam powers down")
		await create_timer(float(manager.effects[beam_id].duration)+0.5).timeout
		check(not is_instance_valid(ray), "released beam frees after its last instances fade")
	print(JSON.stringify({"api_checks":checks,"failures":failures}))
	quit(0 if failures.is_empty() else 1)
