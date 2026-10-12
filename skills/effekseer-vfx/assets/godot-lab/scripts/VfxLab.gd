extends Node3D

var index: int = 0
var elapsed: float = 0.0
var looped: bool = true
var showcase: bool = false
var bright: bool = false
var environment: Environment
var floor_material: StandardMaterial3D
var title: Label
var subtitle: Label
var fps_label: Label
var info: Label
var status: Label
var timeline: ProgressBar
var library_list: ItemList
var loop_button: CheckButton
var pause_button: CheckButton
var showcase_button: CheckButton
var capture_mode: bool = false
var capture_dir: String = ""
var capture_frame: int = 0
var capture_started: bool = false
var capture_end: int = 0
var capture_samples: Array[int] = []
var capture_ids: Array[String] = []
var captured: int = 0
var movie_mode: bool = false
var hide_dummies: bool = false
var target_position := Vector3(0, 1.35, 0)
# Combat staging: the effect is performed by one dummy on itself or on the other, the way a game
# would trigger it (manifest `delivery`). Captures and review strips use the same staging; --isolated is the
# legacy single-target stage.
const ISOLATED_PLAYER := Vector3(-1.7, 0, 0)
const ISOLATED_ENEMY := Vector3(0, 0, -0.12)
# Combat: the two dummies stand at opposite ends of the platform, the camera looks at the middle.
const COMBAT_PLAYER := Vector3(-2.55, 0, 0)
const COMBAT_ENEMY := Vector3(2.55, 0, 0)
# Where each attach point sits relative to its dummy; equals the isolated stage's fixed anchors.
const ATTACH_OFFSET := {"ground": Vector3(0, 0, 0.12), "body": Vector3(0, 0.95, 0.12), "impact": Vector3(0, 1.35, 0.12), "caster": Vector3(0, 1.2, 0), "caster_ground": Vector3.ZERO}
# Optional rigged stand-ins (Mixamo bone names, e.g. from an auto-rigging service) replace the capsule dummies
# when present: copy them to vfx/characters/ and run `vfx init`. The clips keep their root motion in the hips
# track, so the body travels with the steps and planted feet stay put.
# The GLBs are expected 1 unit tall; 1.75 puts the hips at the "body" anchor.
const CHARACTERS := {"PlayerDummy": "res://characters/player.glb", "EnemyDummy": "res://characters/target.glb"}
const CHARACTER_SCALE := 1.75
# Where a ranged attack leaves the caster (hand or mouth), relative to the caster's feet.
const MUZZLE := Vector3(0.45, 1.3, 0.12)
# Each faces the other, turned 25° toward the camera so the action reads in three-quarter view.
const CHARACTER_YAW := {"PlayerDummy": 65.0, "EnemyDummy": -65.0}
# Clip times measured from the bone data (hand speed, hips height): the moment each clip is synced to.
const CAST_RELEASE := 1.45   # cast_a_spell: arm thrust toward the target
const CAST_END := 2.0        # ...before its second, punch-like push at 2.4 s; the clip is cut here
const PUNCH_STRIKE := 0.7    # box_03: the stepping jab reaches full extension (planted feet hold within 5 cm)
const JUMP_CROUCH := 0.5     # jump (a run of hops): the first crouch...
const JUMP_LAND := 1.0       # ...and the landing that follows it
const CLIP_BLEND := 0.15
const IDLE_BLEND := 0.35     # settling back to idle (e.g. landing from the cast's float) is slower
# Clip roles → animation name prefixes, first match wins (an export may suffix them, e.g. "box_03_001").
const CLIP_ROLES := {
	"idle": ["idle"],
	"cast": ["cast_a_spell"],
	"punch": ["box_03"],
	"hit_heavy": ["hit_to_head"],
	"hit_light": ["hit_to_body_01"],
	"jump": ["jump"],
}
# The cast floats up off the ground; it may rise but must not drift toward the target.
const IN_PLACE_ROLES := ["cast"]
var combat: bool = true
var combat_button: CheckButton
var player: Node3D
var enemy: Node3D
var isolated_camera: Transform3D
var combat_camera: Transform3D
var events: Array = []          # [{t, do}] fired once elapsed reaches t
var moves: Dictionary = {}      # dummy name -> [{kind, t, ...}] pose keys, evaluated every frame
var sequence_end: float = 1.0
# When the reviewed effect itself starts inside the staged exchange (after a punch's windup, a cast or a projectile's
# flight); captures number their frames from here so they line up with the manifest timing.
var effect_start: float = 0.0
var capture_offset: int = 0
var sequence_id: int = 0
var delivery_text: String = ""
var strip_mode: bool = false
var strip_step: int = 4
var strip_plan: Dictionary = {}
var review_view: String = "standard"
var stage_feedback: bool = true
var ui_layer: CanvasLayer
var camera: Camera3D
var camera_home: Transform3D
var flash_light: OmniLight3D
var impact_fired: bool = false
var shake: float = 0.0
# World scale of the selected effect (manifest scale.world): the whole stage, the dummies and the camera grow with it, so
# a kaiju effect is staged between 70 m dummies and frames the same as a character-scale one.
var stage_scale: float = 1.0
var stage: Node3D
var sun: DirectionalLight3D
var isolated_camera_base: Transform3D
var combat_camera_base: Transform3D
# The beam the current sequence is firing and how it sweeps: two {t, to} keys and the muzzle; released at beam_end.
var beam_handle: CombatVfxHandle
var beam_path: Array = []
var beam_end: float = 0.0

func _ready() -> void:
	_build_stage()
	_build_ui()
	var args := OS.get_cmdline_user_args()
	for arg in args:
		if arg.begins_with("--capture="):
			capture_mode = true
			capture_dir = arg.trim_prefix("--capture=")
			DirAccess.make_dir_recursive_absolute(capture_dir)
		if arg.begins_with("--ids="):
			capture_ids.assign(arg.trim_prefix("--ids=").split(","))
		if arg.begins_with("--strip="):
			# Clean, UI-free frame sequence for motion review (see tools/review.py).
			capture_mode = true
			strip_mode = true
			capture_dir = arg.trim_prefix("--strip=")
			DirAccess.make_dir_recursive_absolute(capture_dir)
			ui_layer.hide()
			camera.h_offset = 0
		if arg.begins_with("--step="): strip_step = maxi(1, int(arg.trim_prefix("--step=")))
		if arg.begins_with("--sample-plan="):
			var parsed = JSON.parse_string(FileAccess.get_file_as_string(arg.trim_prefix("--sample-plan=")))
			if parsed is Dictionary:
				# JSON numbers are floats; Array.has uses typed equality, so normalize to frame integers.
				for id in parsed:
					var samples: Array[int] = []
					for frame_number in parsed[id]: samples.append(int(frame_number))
					strip_plan[id] = samples
		if arg.begins_with("--review-view="): review_view = arg.trim_prefix("--review-view=")
		if arg == "--bare":
			environment.glow_enabled = false
			stage_feedback = false
		if arg == "--bright": _set_background(true)
		if arg == "--no-glow": environment.glow_enabled = false
		if arg == "--movie": movie_mode = true
		if arg == "--showcase": showcase = true
		if arg == "--no-dummies": hide_dummies = true
		if arg == "--isolated": combat = false
	combat_button.set_pressed_no_signal(combat)
	# Automated captures pop a window that stray focus or Cmd+W/Q can close mid-run (exit 0, strip cut short);
	# they finish on their own, so log and ignore close requests instead of quitting.
	if capture_mode:
		get_tree().auto_accept_quit = false
		_park_capture_window()
	_layout()
	# Settle the characters into idle before the first frame: a capture's empty reference must match the replay.
	_pose(player, [], 0.0)
	_pose(enemy, [], 0.0)
	if hide_dummies:
		$PlayerDummy.hide()
		$EnemyDummy.hide()
	if capture_ids.size() > 0:
		index = _find_id(capture_ids[0])
	looped = not capture_mode
	loop_button.button_pressed = looped
	showcase_button.button_pressed = showcase
	if Vfx.manifest.is_empty():
		title.text = "No effects loaded"
		subtitle.text = "Build an effect library to begin"
	else:
		# Captures start each effect themselves, after the empty reference frame.
		_select(index, not capture_mode)

func _find_id(id: String) -> int:
	for i in range(Vfx.manifest.size()):
		if Vfx.manifest[i].id == id: return i
	return 0

func _mesh(mesh: Mesh, color: Color, position: Vector3, parent: Node = self) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	m.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.72
	m.material_override = mat
	parent.add_child(m)
	m.position = position
	return m

func _build_stage() -> void:
	var world := WorldEnvironment.new()
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = DARK_BACKGROUND
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("8ca7c9")
	environment.ambient_light_energy = 0.75
	# Forward+ keeps additive/emissive VFX above 1.0 until glow and tonemapping (cores measure 8x and more).
	# Glow ramps in by smoothstep(threshold, threshold + hdr_scale): on the lit stage the toon-shaded characters
	# peak near 3.4x (measured with a linear tonemap at 1/8 exposure), so the knee starts just below that and is
	# fully on by 6x; the characters pick up almost no glow while every VFX core blooms at full strength.
	# Additive blend feeds the halo into the HDR buffer before Filmic, and a low Filmic white burns cores to white
	# while the halo keeps the element's hue.
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.tonemap_white = 4.0
	environment.glow_enabled = true
	environment.glow_intensity = 1.5
	environment.glow_strength = 1.1
	environment.glow_bloom = 0.0
	environment.glow_hdr_threshold = 2.8
	environment.glow_hdr_scale = 3.2
	environment.glow_hdr_luminance_cap = 24.0
	# Tight halo through a wide soft bloom; the widest level stays lowest so a bolt does not haze the whole frame.
	for level in range(7): environment.set_glow_level(level, 0.0)
	environment.set_glow_level(1, 1.0)
	environment.set_glow_level(2, 1.0)
	environment.set_glow_level(3, 0.85)
	environment.set_glow_level(4, 0.6)
	environment.set_glow_level(5, 0.35)
	environment.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	world.environment = environment
	flash_light = OmniLight3D.new()
	flash_light.position = target_position + Vector3(0.4, 0.3, 1.2)
	flash_light.omni_range = 9
	flash_light.light_energy = 0
	add_child(flash_light)
	add_child(world)
	stage = Node3D.new()
	stage.name = "Stage"
	add_child(stage)
	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -25, 0)
	sun.light_energy = 1.5
	sun.shadow_enabled = true
	add_child(sun)
	var fill := OmniLight3D.new()
	fill.position = Vector3(1, 3, 3)
	fill.light_color = Color("70cbdc")
	fill.light_energy = 1.0
	fill.omni_range = 10
	add_child(fill)
	var plane := PlaneMesh.new()
	plane.size = Vector2(100, 100)
	var floor_mesh := _mesh(plane, DARK_FLOOR, Vector3(0, -0.12, 0), stage)
	floor_material = floor_mesh.material_override
	var platform := CylinderMesh.new()
	platform.top_radius = 3.0
	platform.bottom_radius = 3.0
	platform.height = 0.12
	platform.radial_segments = 96
	_mesh(platform, Color("2a3848"), Vector3(0, -0.045, 0), stage)
	# Thin concentric stage markings give a scale reference.
	for radius in [1.0, 2.0, 2.95]:
		var torus := TorusMesh.new()
		torus.inner_radius = radius - 0.012
		torus.outer_radius = radius + 0.012
		torus.rings = 64
		torus.ring_segments = 6
		_mesh(torus, Color("5f86a6"), Vector3(0, 0.018, 0), stage)
	player = _dummy("PlayerDummy", ISOLATED_PLAYER, Color("5cbbca"), "PLAYER")
	enemy = _dummy("EnemyDummy", ISOLATED_ENEMY, Color("d47f66"), "TARGET")
	camera = Camera3D.new()
	camera.position = Vector3(3.2, 4.9, 8.3)
	add_child(camera)
	camera.look_at(Vector3(-0.55, 1.0, 0))
	camera.fov = 38
	camera.h_offset = -0.75
	camera.current = true
	isolated_camera = camera.transform
	# Front-on, centred on the midpoint between the dummies so caster, flight path and target read at once.
	camera.position = Vector3(0, 3.5, 10.6)
	camera.look_at(Vector3(0, 1.25, 0))
	combat_camera = camera.transform
	isolated_camera_base = isolated_camera
	combat_camera_base = combat_camera
	camera.transform = isolated_camera
	camera_home = camera.transform

func _set_stage_scale(value: float) -> void:
	# Everything in the stage frame scales about the world origin: the camera keeps its view direction and the framing
	# of the dummies, and every metric measured in stage heights compares across scales.
	stage_scale = maxf(value, 0.001)
	stage.scale = Vector3.ONE * stage_scale
	for dummy in [player, enemy]: dummy.scale = Vector3.ONE * stage_scale
	isolated_camera = Transform3D(isolated_camera_base.basis, isolated_camera_base.origin * stage_scale)
	combat_camera = Transform3D(combat_camera_base.basis, combat_camera_base.origin * stage_scale)
	camera.near = 0.05 * stage_scale
	camera.far = 4000.0 * stage_scale
	flash_light.omni_range = 9 * stage_scale
	sun.directional_shadow_max_distance = 100.0 * stage_scale

func _layout() -> void:
	player.position = (COMBAT_PLAYER if combat else ISOLATED_PLAYER) * stage_scale
	enemy.position = (COMBAT_ENEMY if combat else ISOLATED_ENEMY) * stage_scale
	camera_home = combat_camera if combat else isolated_camera
	camera.transform = camera_home
	# The offset only re-centres the view in the space the side panel leaves free.
	camera.h_offset = 0.0 if strip_mode else -1.25 if combat else -0.75
	camera.v_offset = 0.25 if combat else 0.0

func _dummy(node_name: String, pos: Vector3, color: Color, label_text: String) -> Node3D:
	var dummy := Node3D.new()
	dummy.name = node_name
	add_child(dummy)
	dummy.position = pos
	# Meshes hang off a pivot at the feet: poses lean and squash it without moving the label.
	var pivot := Node3D.new()
	pivot.name = "Pivot"
	dummy.add_child(pivot)
	var label := Label3D.new()
	label.text = label_text
	label.position = Vector3(0, 2.02, 0)
	label.font_size = 32
	label.pixel_size = 0.003
	label.modulate = color.lightened(0.3)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	dummy.add_child(label)
	var scene_path: String = CHARACTERS.get(node_name, "")
	if scene_path != "" and ResourceLoader.exists(scene_path):
		_character(dummy, pivot, scene_path)
		return dummy
	var body := CapsuleMesh.new()
	body.radius = 0.24
	body.height = 1.25
	var torso := _mesh(body, color.darkened(0.35), Vector3(0, 0.82, 0), pivot)
	var head := SphereMesh.new()
	head.radius = 0.22
	head.height = 0.44
	var skull := _mesh(head, color, Vector3(0, 1.62, 0), pivot)
	dummy.set_meta("materials", [torso.material_override, skull.material_override])
	return dummy

func _character(dummy: Node3D, pivot: Node3D, scene_path: String) -> void:
	var model: Node3D = load(scene_path).instantiate()
	pivot.add_child(model)
	model.scale = Vector3.ONE * CHARACTER_SCALE
	model.rotation.y = deg_to_rad(CHARACTER_YAW[dummy.name])
	var player_node: AnimationPlayer = model.find_children("*", "AnimationPlayer", true, false)[0]
	var clips := {}
	for role: String in CLIP_ROLES:
		for prefix: String in CLIP_ROLES[role]:
			for anim_name in player_node.get_animation_list():
				if not clips.has(role) and String(anim_name).begins_with(prefix): clips[role] = String(anim_name)
	dummy.set_meta("clips", clips)
	if clips.has("idle"): player_node.get_animation(clips.idle).loop_mode = Animation.LOOP_LINEAR
	# Pin the horizontal root motion of in-place roles; the vertical float stays.
	for role in IN_PLACE_ROLES:
		if not clips.has(role): continue
		var clip := player_node.get_animation(clips[role])
		for track in clip.get_track_count():
			if clip.track_get_type(track) != Animation.TYPE_POSITION_3D or not String(clip.track_get_path(track)).ends_with(":mixamorig_Hips"): continue
			var rest: Vector3 = clip.track_get_key_value(track, 0)
			for k in clip.track_get_key_count(track):
				var p: Vector3 = clip.track_get_key_value(track, k)
				clip.track_set_key_value(track, k, Vector3(rest.x, p.y, rest.z))
	# The hit flash rides on an additive overlay so the textured materials stay untouched.
	var flash := StandardMaterial3D.new()
	flash.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	flash.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	flash.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	flash.albedo_color = Color(1, 0.95, 0.85, 0)
	var roles := _material_roles(scene_path)
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		_toon(mesh, roles.get("parts", {}).get(String(mesh.name), roles.get("default", "cloth")))
		mesh.material_overlay = flash
	dummy.set_meta("anim", player_node)
	dummy.set_meta("model", model)
	dummy.set_meta("flash", flash)
	# Different idle phases so the two characters never breathe in lockstep.
	dummy.set_meta("idle_phase", 0.0 if dummy.name == "PlayerDummy" else 6.0)
	dummy.set_meta("clip", "")

# Cel-shading presets per material role. Skin keeps a soft warm terminator, hair a crisp cool shadow with a
# highlight band, cloth a crisp shadow plus colour-based skin detection for parts that mix skin and fabric.
const TOON_ROLES := {
	"skin": {"shade_threshold": 0.0, "shade_softness": 0.12, "shadow_color": Color(0.96, 0.74, 0.72), "rim_strength": 0.15},
	"hair": {"shade_threshold": 0.1, "shade_softness": 0.03, "shadow_color": Color(0.62, 0.66, 0.86), "rim_strength": 0.15, "highlight_strength": 0.12, "highlight_size": 0.02, "light_scale": 0.42},
	# Hair and face in one part: hair shading, with skin pixels picked out by colour (no highlight on them).
	"head": {"shade_threshold": 0.1, "shade_softness": 0.03, "shadow_color": Color(0.62, 0.66, 0.86), "rim_strength": 0.15, "highlight_strength": 0.12, "highlight_size": 0.02, "light_scale": 0.42, "skin_from_color": true},
	"cloth": {"shade_threshold": 0.05, "shade_softness": 0.03, "shadow_color": Color(0.66, 0.66, 0.82), "rim_strength": 0.25, "skin_from_color": true},
}
# Default stage: deep slate blue, bright enough that characters and floor read, dark enough that VFX dominate.
const DARK_BACKGROUND := Color("1a2433")
const DARK_FLOOR := Color("1d2733")
const TOON_SHADER := preload("res://shaders/character_toon.gdshader")
const OUTLINE_SHADER := preload("res://shaders/character_outline.gdshader")

func _material_roles(scene_path: String) -> Dictionary:
	# <model>.materials.json beside the GLB maps part meshes to toon roles: {"default": "cloth", "parts": {"part_2": "hair"}}.
	var path := scene_path.get_basename() + ".materials.json"
	if not FileAccess.file_exists(path): return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}

func _toon(mesh: MeshInstance3D, role: String) -> void:
	for surface in mesh.mesh.get_surface_count():
		var source := mesh.get_active_material(surface) as BaseMaterial3D
		var albedo: Texture2D = source.albedo_texture if source else null
		var toon := ShaderMaterial.new()
		toon.shader = TOON_SHADER
		toon.set_shader_parameter("albedo_texture", albedo)
		for key: String in TOON_ROLES.get(role, TOON_ROLES.cloth):
			toon.set_shader_parameter(key, TOON_ROLES.get(role, TOON_ROLES.cloth)[key])
		var outline := ShaderMaterial.new()
		outline.shader = OUTLINE_SHADER
		outline.set_shader_parameter("albedo_texture", albedo)
		toon.next_pass = outline
		mesh.set_surface_override_material(surface, toon)

func _label(text: String, size: int = 16, color: Color = Color("d7e3f0")) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l

func _button(text: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(82, 38)
	b.pressed.connect(callback)
	return b

func _panel(rect: Rect2, color: Color) -> Panel:
	var p := Panel.new()
	p.position = rect.position
	p.size = rect.size
	var box := StyleBoxFlat.new()
	box.bg_color = color
	box.corner_radius_top_left = 10
	box.corner_radius_top_right = 10
	box.corner_radius_bottom_left = 10
	box.corner_radius_bottom_right = 10
	p.add_theme_stylebox_override("panel", box)
	return p

func _build_ui() -> void:
	var canvas := CanvasLayer.new()
	ui_layer = canvas
	add_child(canvas)
	var ui := Control.new()
	canvas.add_child(ui)
	ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var theme := Theme.new()
	theme.default_font_size = 15
	ui.theme = theme
	var side := _panel(Rect2(20,20,250,760), Color("0c1422"))
	ui.add_child(side)
	var brand := _label("COMBAT / VFX", 25, Color("edf7ff"))
	brand.position = Vector2(18,18)
	side.add_child(brand)
	var desc := _label("EFFEKSEER  •  ASSET LIBRARY", 11, Color("6aa8b7"))
	desc.position = Vector2(18,55)
	side.add_child(desc)
	var filter := OptionButton.new()
	filter.position = Vector2(18,94)
	filter.size = Vector2(214,36)
	var categories: Array[String] = []
	for item in Vfx.manifest:
		if not categories.has(item.category): categories.append(item.category)
	filter.add_item("All categories")
	for cat in categories: filter.add_item(cat.capitalize())
	filter.item_selected.connect(func(i: int): _filter_category(filter.get_item_text(i).to_lower() if i > 0 else ""))
	side.add_child(filter)
	library_list = ItemList.new()
	library_list.position = Vector2(14,144)
	library_list.size = Vector2(222,536)
	library_list.add_theme_constant_override("v_separation", 9)
	library_list.item_selected.connect(func(i: int): _select(int(library_list.get_item_metadata(i))))
	side.add_child(library_list)
	_filter_category("")
	var count_label := _label("%02d effects  /  %d categories" % [Vfx.manifest.size(),categories.size()], 13, Color("8194ac"))
	count_label.position = Vector2(18,703)
	side.add_child(count_label)
	var top := _panel(Rect2(290,20,970,100), Color(0.045,0.075,0.12,0.92))
	ui.add_child(top)
	title = _label("", 31, Color("eff8ff"))
	title.position = Vector2(24,16)
	top.add_child(title)
	subtitle = _label("", 13, Color("83bdc9"))
	subtitle.position = Vector2(26,60)
	top.add_child(subtitle)
	fps_label = _label("", 14, Color("8ae2b9"))
	fps_label.position = Vector2(842,24)
	top.add_child(fps_label)
	var controls := _panel(Rect2(290,656,970,124), Color("0c1422"))
	ui.add_child(controls)
	var row := HBoxContainer.new()
	row.position = Vector2(18,16)
	row.add_theme_constant_override("separation", 10)
	controls.add_child(row)
	row.add_child(_button("← Previous",func(): _select(index-1)))
	row.add_child(_button("Replay",_replay))
	row.add_child(_button("Next →",func(): _select(index+1)))
	loop_button = CheckButton.new()
	loop_button.text = "Loop"
	loop_button.button_pressed = looped
	loop_button.toggled.connect(func(b: bool): looped = b)
	row.add_child(loop_button)
	pause_button = CheckButton.new()
	pause_button.text = "Pause"
	pause_button.toggled.connect(func(b: bool): Vfx.set_paused(b))
	row.add_child(pause_button)
	var speed_select := OptionButton.new()
	for s in ["0.25×", "0.5×", "1×", "2×"]: speed_select.add_item(s)
	speed_select.select(2)
	speed_select.item_selected.connect(func(i: int): Vfx.set_speed([0.25,0.5,1.0,2.0][i]))
	row.add_child(speed_select)
	row.add_child(_button("Dark / Bright",func(): _set_background(not bright)))
	showcase_button = CheckButton.new()
	showcase_button.text = "Showcase"
	showcase_button.toggled.connect(func(b: bool): showcase = b; elapsed = 0)
	row.add_child(showcase_button)
	combat_button = CheckButton.new()
	combat_button.text = "Combat"
	combat_button.button_pressed = combat
	combat_button.toggled.connect(func(b: bool): combat = b; _layout(); _replay())
	row.add_child(combat_button)
	status = _label("", 12, Color("8c9eb4"))
	status.position = Vector2(20,71)
	controls.add_child(status)
	timeline = ProgressBar.new()
	timeline.position = Vector2(20,100)
	timeline.size = Vector2(930,5)
	timeline.show_percentage = false
	controls.add_child(timeline)
	info = _label("", 13, Color("99acbf"))
	info.position = Vector2(316,605)
	ui.add_child(info)

func _filter_category(category: String) -> void:
	library_list.clear()
	for i in range(Vfx.manifest.size()):
		var item: Dictionary = Vfx.manifest[i]
		if category != "" and item.category != category: continue
		var j := library_list.add_item("%02d  %s" % [i+1,item.name])
		library_list.set_item_metadata(j,i)

func _select(i: int, start: bool = true) -> void:
	if Vfx.manifest.is_empty(): return
	index = posmod(i,Vfx.manifest.size())
	var item: Dictionary = Vfx.manifest[index]
	var world := float(item.get("scale", {}).get("world", 1.0))
	if not is_equal_approx(world, stage_scale):
		_set_stage_scale(world)
		_layout()
	if capture_mode and review_view == "close":
		var self_cast := str(item.get("delivery", {}).get("kind", "")) == "self"
		var focus := ((COMBAT_PLAYER if self_cast else COMBAT_ENEMY) + Vector3(0, 1.0, 0)) * stage_scale
		camera.position = focus + Vector3(1.4, 2.2, 5.8) * stage_scale
		camera.look_at(focus)
		camera_home = camera.transform
	if showcase: print(JSON.stringify({"showcase_index":index+1,"id":item.id}))
	title.text = "%02d / %s" % [index+1,item.name]
	subtitle.text = "%s   /   %s   /   %s" % [item.category.to_upper(),item.element.to_upper(),item.id]
	if stage_scale != 1.0: subtitle.text += "   /   %s x%s" % [str(item.get("scale", {}).get("profile", "scale")).to_upper(), str(stage_scale)]
	info.text = "%.2f s duration     •     %d layers     •     ≤ %d particles     •     %s" % [item.duration,item.layers,item.particle_budget,item.attach.to_upper()]
	for j in range(library_list.item_count):
		if int(library_list.get_item_metadata(j)) == index:
			library_list.select(j)
			library_list.ensure_current_is_visible()
	if start: _replay()

func _replay() -> void:
	if Vfx.manifest.is_empty(): return
	if capture_mode: seed(int(Vfx.manifest[index].get("seed", 1729)))
	Vfx.stop_all()
	beam_handle = null
	beam_path = []
	elapsed = 0
	sequence_id += 1
	events.clear()
	moves.clear()
	_pose(player, [], 0.0)
	_pose(enemy, [], 0.0)
	var item: Dictionary = Vfx.manifest[index]
	impact_fired = false
	flash_light.light_energy = 0
	shake = 0
	camera.transform = camera_home
	effect_start = 0.0
	if combat:
		_stage(item)
		return
	# Isolated review stage: the effect alone at its fixed anchor, kick at the manifest peak.
	delivery_text = "ISOLATED"
	sequence_end = float(item.duration)
	if item.category == "projectile":
		var to := _anchor(item, enemy)
		Vfx.launch(item.id, to + Vector3(-3.2, -0.15, 0) * stage_scale, to)
		return
	var at := _anchor(item, player if item.attach.begins_with("caster") else enemy)
	Vfx.play(item.id,at,Vector3.ZERO,Vector3.ONE,{"loop":false})
	_at(float(item.get("peak", 0.1)), func(): _kick(item, at))

func _anchor(item: Dictionary, actor: Node3D) -> Vector3:
	return actor.position + ATTACH_OFFSET.get(item.attach, ATTACH_OFFSET.impact) * stage_scale

func _paired_impact(projectile_id: String) -> Dictionary:
	for entry in Vfx.manifest:
		if entry.get("delivery", {}).get("projectile", "") == projectile_id: return entry
	return {}

func _stage(item: Dictionary) -> void:
	# Build one exchange as timed events: who acts, where the effect lands, when the other one reacts.
	var delivery: Dictionary = item.get("delivery", {"kind": "targeted"})
	var kind: String = delivery.get("kind", "targeted")
	var impact_item := item
	if item.category == "projectile":
		kind = "projectile"
		impact_item = _paired_impact(item.id)
	match kind:
		"self":
			delivery_text = "SELF  ·  player casts on itself"
			_move(player, {"kind": "cast", "t": 0.0})
			effect_start = 0.12
			_at(0.12, func(): _play(item, _anchor(item, player)))
			_at(0.12 + float(item.peak), func(): _kick(item, _anchor(item, player)))
			sequence_end = 0.12 + float(item.duration)
		"melee":
			delivery_text = "MELEE  ·  player strikes in place; the blow lands on the target"
			var strike := 0.34
			var start := maxf(0.0, strike - float(item.peak))
			_move(player, {"kind": "punch", "t": 0.0, "strike": strike})
			effect_start = start
			_at(start, func(): _play(item, _anchor(item, enemy)))
			_hit_at(start + float(item.peak), item, player)
			sequence_end = start + float(item.duration)
		"projectile":
			var projectile_id: String = item.id if item.category == "projectile" else delivery.get("projectile", "")
			delivery_text = "RANGED  ·  %s flies to the target%s" % [projectile_id, ("  →  " + impact_item.id) if not impact_item.is_empty() else ""]
			_move(player, {"kind": "cast", "t": 0.0})
			var to := _anchor(impact_item if not impact_item.is_empty() else item, enemy)
			# Every projectile flies at the target; a ground impact (Ice Spikes) still erupts at the feet on arrival.
			if not impact_item.is_empty() and impact_item.attach == "ground": to = enemy.position + ATTACH_OFFSET.body
			var flight := float(Vfx.effects.get(projectile_id, {}).get("flight", 0.5))
			var launch_at := 0.2
			effect_start = launch_at if item.category == "projectile" else launch_at + flight
			sequence_end = launch_at + flight + (float(impact_item.duration) if not impact_item.is_empty() else 0.6)
			var current := sequence_id
			if capture_mode and item.category != "projectile":
				# Review one resource at its own start: incoming projectile tails would contaminate first frames and metrics.
				# Keep the same combat positions and arrival time; normal Lab playback still shows the complete pair.
				_at(effect_start, func():
					_play(impact_item, _anchor(impact_item, enemy))
					_hit_at(elapsed + float(impact_item.peak), impact_item, player))
				return
			_at(launch_at, func():
				var handle := Vfx.launch(projectile_id, player.position + MUZZLE * stage_scale, to)
				# A projectile's own capture stops at arrival: the paired impact has its own strip and metrics.
				if handle == null or impact_item.is_empty() or (capture_mode and item.category == "projectile"): return
				handle.arrived.connect(func(_p):
					if current != sequence_id: return
					# Impact begins on the arrival frame; the target reacts at the impact's own peak.
					_play(impact_item, _anchor(impact_item, enemy))
					_hit_at(elapsed + float(impact_item.peak), impact_item, player)))
		"beam":
			# The caster breathes the beam at the ground in front of the target and rakes it up onto the target's chest,
			# so one take shows ignition, a moving end point, the hit and the release.
			var charge_id: String = delivery.get("charge", "")
			var charge: Dictionary = Vfx.effects.get(charge_id, {})
			var launch_at := 0.2
			delivery_text = "BEAM  ·  player rakes the beam onto the target" + (("  ·  after " + charge_id) if not charge.is_empty() else "")
			_move(player, {"kind": "cast", "t": 0.0})
			if not charge.is_empty() and not capture_mode:
				_at(0.0, func(): _play(charge, _anchor(charge, player)))
				launch_at = float(charge.duration) * 0.85
			var hold := float(item.get("hold", 1.0))
			var from := player.position + MUZZLE * stage_scale
			var near := enemy.position + Vector3(-1.6, 0.0, 0.12) * stage_scale
			var chest := enemy.position + ATTACH_OFFSET.body * stage_scale
			beam_path = [{"t": launch_at, "to": near}, {"t": launch_at + hold * 0.7, "to": chest}, {"from": from}]
			beam_end = launch_at + hold
			effect_start = launch_at
			_at(launch_at, func(): beam_handle = Vfx.beam(item.id, from, near))
			_hit_at(launch_at + float(item.peak), item, player)
			sequence_end = launch_at + float(item.duration)
		"area":
			delivery_text = "AREA  ·  the boss slams the ground; the shock wave reaches the player"
			var peak := float(item.peak)
			_move(enemy, {"kind": "jump", "t": 0.0, "land": peak})
			_at(0.0, func(): _play(item, _anchor(item, enemy)))
			_at(peak, func(): _kick(item, _anchor(item, enemy)))
			_hit_at(peak + 0.08, item, enemy, player, false)
			sequence_end = float(item.duration)
		_:
			delivery_text = "TARGETED  ·  player calls the spell down on the target"
			_move(player, {"kind": "cast", "t": 0.0})
			effect_start = 0.18
			_at(0.18, func(): _play(item, _anchor(item, enemy)))
			_hit_at(0.18 + float(item.peak), item, player)
			sequence_end = 0.18 + float(item.duration)

func _play(item: Dictionary, at: Vector3) -> void:
	Vfx.play(item.id, at, Vector3.ZERO, Vector3.ONE, {"loop": false})

func _hit_at(t: float, item: Dictionary, source: Node3D, victim: Node3D = enemy, kick: bool = true) -> void:
	var power := float(item.get("impact", 0.0))
	if kick: _at(t, func(): _kick(item, _anchor(item, victim)))
	if power <= 0.0: return
	_move(victim, {"kind": "hit", "t": t, "power": power, "dir": signf(victim.position.x - source.position.x)})

func _at(t: float, action: Callable) -> void:
	events.append({"t": t, "do": action})

func _move(actor: Node3D, key: Dictionary) -> void:
	if not moves.has(actor.name): moves[actor.name] = []
	moves[actor.name].append(key)

func _run_events() -> void:
	var due := events.filter(func(e): return elapsed >= e.t)
	for e in due:
		events.erase(e)
		e.do.call()

static func _ease_out(x: float) -> float: return 1.0 - pow(1.0 - clampf(x, 0, 1), 3)
static func _ease_in(x: float) -> float: return pow(clampf(x, 0, 1), 2)
static func _smooth(x: float) -> float: return smoothstep(0.0, 1.0, x)

func _pose(actor: Node3D, keys: Array, t: float) -> void:
	# Procedural poses from timed keys: offset of the whole dummy, lean and squash of its pivot, hit flash.
	var offset := Vector3.ZERO
	var lean := 0.0       # degrees, positive tips the head toward +x
	var squash := 0.0
	var glow := 0.0
	var square := 0.0     # 0..1: how far a character turns from three-quarter view to face the opponent
	for key in keys:
		var u: float = t - float(key.t)
		if u < 0.0: continue
		match key.kind:
			"cast":
				# Dip, then rise onto the toes and lean back as the spell leaves the hand.
				squash += 0.1 * (_ease_out(u / 0.1) - _smooth((u - 0.1) / 0.15))
				offset.y += 0.12 * (_ease_out((u - 0.1) / 0.12) - _smooth((u - 0.35) / 0.35))
				lean -= 9.0 * (_ease_out((u - 0.1) / 0.12) - _smooth((u - 0.35) / 0.35))
			"punch":
				# In place: rock back on the windup, then drive the shoulder toward the target on the strike.
				var strike: float = key.strike
				# The jab lands straight ahead of the body: square up during the windup so it reads side-on.
				square = maxf(square, _smooth(u / strike) - _smooth((u - strike - 0.35) / 0.4))
				lean += -6.0 * _ease_out(u / strike) * (1.0 - _ease_out((u - strike + 0.08) / 0.08)) + 14.0 * (_ease_out((u - strike + 0.08) / 0.08) - _smooth((u - strike - 0.15) / 0.3))
			"hit":
				var power: float = key.power
				var dir: float = key.dir
				var kick := _ease_out(u / 0.09) - _smooth((u - 0.25) / 0.45)
				offset.x += dir * (0.12 + 0.38 * power) * kick
				lean += dir * (5.0 + 14.0 * power) * kick
				squash += 0.12 * power * maxf(0.0, 1.0 - u / 0.18)
				glow = maxf(glow, maxf(0.0, 1.0 - u / 0.12))
			"jump":
				# Boss: crouch, leap, slam down on the effect's peak frame, absorb the landing.
				var land: float = key.land
				var up := land * 0.65
				var y := 0.0
				if u < up: y = 0.95 * _ease_out(u / up)
				elif u < land: y = 0.95 * (1.0 - _ease_in((u - up) / (land - up)))
				offset.y += y
				squash += 0.2 * (1.0 - _smooth(u / 0.08)) * float(u < up) + 0.25 * maxf(0.0, 1.0 - (u - land) / 0.25) * float(u >= land)
	actor.position = ((COMBAT_PLAYER if actor == player else COMBAT_ENEMY) + offset if combat else (ISOLATED_PLAYER if actor == player else ISOLATED_ENEMY)) * stage_scale
	if actor.has_meta("anim"):
		# A rigged character performs the lean and squash through its clips; only the flash stays procedural.
		var flash: StandardMaterial3D = actor.get_meta("flash")
		flash.albedo_color.a = glow * 0.45
		var facing := 90.0 * signf(CHARACTER_YAW[actor.name])
		actor.get_meta("model").rotation.y = deg_to_rad(lerpf(CHARACTER_YAW[actor.name], facing, square))
		_animate(actor, _clip_for(actor, keys, t), t)
		return
	var pivot: Node3D = actor.get_node("Pivot")
	pivot.rotation.z = -deg_to_rad(lean)
	pivot.scale = Vector3(1.0 + squash * 0.5, 1.0 - squash, 1.0 + squash * 0.5)
	for mat: StandardMaterial3D in actor.get_meta("materials"):
		mat.emission_enabled = glow > 0.0
		mat.emission = Color(1, 0.95, 0.85) * glow * 0.45

func _clip_for(actor: Node3D, keys: Array, t: float) -> Dictionary:
	# The same pose keys pick a clip and the clip time that lines its key moment up with the staged event.
	var want := {"id": "idle", "clip": "idle", "from": float(actor.get_meta("idle_phase")), "start": t, "speed": 1.0}
	for key in keys:
		var u: float = t - float(key.t)
		if u < 0.0: continue
		# The sequence number restarts a clip when a new exchange repeats the same key (replay, next melee effect).
		var id := "%d:%s@%.3f" % [sequence_id, key.kind, key.t]
		match key.kind:
			"cast":
				# The arm thrust lands as the spell leaves the hand, 0.2 s into the cast.
				if u < CAST_END - (CAST_RELEASE - 0.2): want = {"id": id, "clip": "cast", "from": CAST_RELEASE - 0.2, "start": key.t, "speed": 1.0}
			"punch":
				# Bare hands: a stepping jab whose arm reaches full extension on the strike.
				if u < float(key.strike) + 0.9: want = {"id": id, "clip": "punch", "from": PUNCH_STRIKE - float(key.strike), "start": key.t, "speed": 1.0}
			"hit":
				var heavy: bool = float(key.power) >= 0.5
				if u < (1.4 if heavy else 1.0): want = {"id": id, "clip": "hit_heavy" if heavy else "hit_light", "from": 0.05, "start": key.t, "speed": 1.0}
			"jump":
				# One hop of the clip, stretched so the landing frame meets the slam, then held.
				var land: float = key.land
				if u < land + 0.5: want = {"id": id, "clip": "jump", "from": JUMP_CROUCH, "start": key.t, "speed": (JUMP_LAND - JUMP_CROUCH) / maxf(land, 0.05), "until": JUMP_LAND}
	return want

func _animate(actor: Node3D, want: Dictionary, t: float) -> void:
	var anim: AnimationPlayer = actor.get_meta("anim")
	# Only the player carries the punch clips; any role a model lacks falls back to idle.
	var clips: Dictionary = actor.get_meta("clips")
	if not clips.has(want.clip): want = {"id": "idle", "clip": "idle", "from": float(actor.get_meta("idle_phase")), "start": t, "speed": 1.0}
	if want.id != actor.get_meta("clip"):
		actor.set_meta("clip", want.id)
		anim.play(clips[want.clip], IDLE_BLEND if want.clip == "idle" else CLIP_BLEND)
		var position := float(want.from) if want.id == "idle" else float(want.from) + (t - float(want.start)) * float(want.speed)
		anim.seek(position, true)
	# Clips follow the Lab clock (pause and 0.25–2× speed); captures hold the characters still.
	var rate := 0.0 if Vfx.paused or capture_mode else Vfx.speed * float(want.speed)
	if want.has("until") and anim.current_animation_position >= float(want.until): rate = 0.0
	anim.speed_scale = rate

func _kick(item: Dictionary, at: Vector3) -> void:
	# Manifest "impact" (0..1) drives a light flash and camera kick when the effect lands,
	# so effects are judged the way a game would present them.
	if not stage_feedback: return
	var power := float(item.get("impact", 0.0))
	if power <= 0.0: return
	impact_fired = true
	var tint: Array = item.get("light", [1.0, 0.85, 0.6])
	flash_light.light_color = Color(tint[0], tint[1], tint[2])
	# Godot's omni light falls off as 1/distance (attenuation 1): at stage_scale times the distance it needs
	# stage_scale times the energy to light the stage the same.
	flash_light.light_energy = 5.0 * power * stage_scale
	flash_light.position = at + Vector3(0.4, 0.5, 1.2) * stage_scale
	shake = 0.16 * power * stage_scale

func _game_feel(delta: float) -> void:
	flash_light.light_energy = move_toward(flash_light.light_energy, 0.0, delta * 22.0 * stage_scale)
	shake = move_toward(shake, 0.0, delta * 0.7 * stage_scale)
	camera.transform = camera_home
	if shake > 0.0:
		camera.position += Vector3(randf_range(-shake, shake), randf_range(-shake, shake), 0)

func _set_background(value: bool) -> void:
	bright = value
	environment.background_color = Color("5c6873") if bright else DARK_BACKGROUND
	floor_material.albedo_color = Color("8c9da9") if bright else DARK_FLOOR

func _process(delta: float) -> void:
	fps_label.text = "%d FPS" % Engine.get_frames_per_second()
	if Vfx.manifest.is_empty(): return
	if not Vfx.paused: elapsed += delta * Vfx.speed
	var item: Dictionary = Vfx.manifest[index]
	timeline.value = minf(elapsed / sequence_end * 100,100)
	status.text = "← → Switch   •   Space Replay   •   C Combat   •   L Loop   •   P Pause   •   1–4 Speed     |     %.2f s  ·  %.2f×  ·  %s     |     %s" % [elapsed,Vfx.speed,"BRIGHT" if bright else "DARK",delivery_text]
	# While a capture waits for its empty reference frame, no flash or shake may leak into it.
	if not Vfx.paused and (not capture_mode or capture_started):
		_run_events()
		_game_feel(delta)
		_steer_beam()
	# Captures keep the dummies where they stand: a lunge or recoil would count as effect motion in the metrics.
	if combat and not capture_mode:
		_pose(player, moves.get(player.name, []), elapsed)
		_pose(enemy, moves.get(enemy.name, []), elapsed)
	if strip_mode:
		_strip_tick(item)
	elif capture_mode:
		_capture_tick(item)
	elif showcase and elapsed > maxf(sequence_end+.55,1.5):
		if movie_mode and index == Vfx.manifest.size()-1: get_tree().quit()
		else: _select(index+1)
	elif looped and not showcase and elapsed > sequence_end+.55: _replay()

func _steer_beam() -> void:
	# Sweep the beam's end point between its keys, then release it; captures and playback follow the same clock.
	if beam_handle == null or not is_instance_valid(beam_handle) or beam_handle.released or beam_path.size() < 3: return
	var a: Dictionary = beam_path[0]
	var b: Dictionary = beam_path[1]
	var u := _smooth(clampf((elapsed - float(a.t)) / maxf(float(b.t) - float(a.t), 0.001), 0.0, 1.0))
	beam_handle.aim(beam_path[2].from, (a.to as Vector3).lerp(b.to, u))
	if elapsed >= beam_end: beam_handle.release()

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST and capture_mode:
		print(JSON.stringify({"ignored_close_request":capture_frame}))

func _capture_tick(item: Dictionary) -> void:
	capture_frame += 1
	if capture_frame == 20 and not capture_started:
		_capture_image(item.id+"_baseline")
		_replay()
		capture_started = true
		var peak := maxi(2,int(float(item.get("peak",.15))*60))
		capture_samples.assign([peak,maxi(peak+1,int(float(item.duration)*60*.5)),maxi(peak+2,int(float(item.duration)*60*.85))])
		capture_offset = roundi(effect_start * 60)
		capture_end = 20 + capture_offset + maxi(peak+4,int(float(item.duration)*60)+8)
	if capture_started and capture_samples.has(capture_frame-20-capture_offset):
		var sample := capture_samples.find(capture_frame-20-capture_offset)
		_capture_image(item.id if sample == 0 else item.id+"_phase%d" % sample)
	if capture_started and capture_frame >= capture_end:
		captured += 1
		if capture_ids.size() > 0:
			if captured >= capture_ids.size(): get_tree().quit(); return
			_select(_find_id(capture_ids[captured]), false)
		else:
			if index >= Vfx.manifest.size()-1: get_tree().quit(); return
			_select(index+1, false)
		# Starting the next effect here and stopping it in the same frame let it play into the empty reference.
		Vfx.stop_all()
		capture_frame = 0
		capture_started = false

func _strip_tick(item: Dictionary) -> void:
	capture_frame += 1
	if capture_frame == 11 and not capture_started:
		_capture_image("%s_f000" % item.id)  # empty stage: the reference for visibility metrics
	if capture_frame == 12 and not capture_started:
		_replay()
		capture_started = true
		capture_offset = roundi(effect_start * 60)
		capture_end = 12 + capture_offset + int(float(item.duration) * 60) + strip_step
		if strip_plan.has(item.id):
			var wanted: Array = strip_plan[item.id]
			capture_end = 12 + capture_offset + int(wanted.max()) + 1
	if not capture_started: return
	var local := capture_frame - 12 - capture_offset
	var planned: bool = strip_plan.has(item.id) and strip_plan[item.id].has(local)
	if local > 0 and (planned or (not strip_plan.has(item.id) and local % strip_step == 0)):
		_capture_image("%s_f%03d" % [item.id, local])
	if capture_frame >= capture_end:
		captured += 1
		if capture_ids.size() > 0:
			if captured >= capture_ids.size(): get_tree().quit(); return
			_select(_find_id(capture_ids[captured]), false)
		else:
			if index >= Vfx.manifest.size()-1: get_tree().quit(); return
			_select(index+1, false)
		# Starting the next effect here and stopping it in the same frame let it play into the empty reference.
		Vfx.stop_all()
		capture_frame = 0
		capture_started = false

func _capture_image(file_name: String) -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var err := image.save_png(capture_dir.path_join(file_name+".png"))
	print(JSON.stringify({"capture":file_name,"error":err,"frame":capture_frame,"effect":Vfx.manifest[index].id}))

# Captures run while the user keeps working: macOS stops drawing a fully covered window (frames come out identical
# to the empty stage), and a centred window gets in the way. Park it always-on-top with only a sliver on screen in
# the bottom-right corner; the viewport still renders at full size, and review.py hands focus back to the user's app.
func _park_capture_window() -> void:
	var window := get_window()
	var screen := DisplayServer.screen_get_usable_rect(window.current_screen)
	window.always_on_top = true
	window.position = screen.end - Vector2i(48, 32)
	print(JSON.stringify({"capture_window":{"position":[window.position.x,window.position.y],"size":[window.size.x,window.size.y],"screen":[screen.position.x,screen.position.y,screen.size.x,screen.size.y]}}))

func _unhandled_key_input(event: InputEvent) -> void:
	# Keystrokes meant for another app can land here for a moment while a capture starts; they must not replay
	# the effect or toggle the stage mid-strip.
	if capture_mode or not event.is_pressed() or event.is_echo(): return
	match event.keycode:
		KEY_LEFT: _select(index-1)
		KEY_RIGHT: _select(index+1)
		KEY_SPACE: _replay()
		KEY_L: loop_button.button_pressed = not looped
		KEY_P: pause_button.button_pressed = not Vfx.paused
		KEY_1: Vfx.set_speed(.25)
		KEY_2: Vfx.set_speed(.5)
		KEY_3: Vfx.set_speed(1.0)
		KEY_4: Vfx.set_speed(2.0)
		KEY_B: _set_background(not bright)
		KEY_S: showcase_button.button_pressed = not showcase
		KEY_C: combat_button.button_pressed = not combat
