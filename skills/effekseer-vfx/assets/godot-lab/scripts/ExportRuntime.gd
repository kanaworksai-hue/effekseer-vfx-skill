extends SceneTree

func _initialize() -> void:
	call_deferred("_export")

func _export() -> void:
	var entries: Array = JSON.parse_string(FileAccess.get_file_as_string("res://vfx_manifest.json"))
	DirAccess.make_dir_recursive_absolute("res://runtime")
	var failures: Array = []
	for entry in entries:
		var effect: EffekseerEffect = load(entry.file)
		if effect == null:
			failures.append(entry.id)
			continue
		var error := ResourceSaver.save(effect,"res://runtime/"+entry.id+".res")
		if error != OK: failures.append(entry.id)
	print(JSON.stringify({"exported":entries.size()-failures.size(),"failures":failures}))
	quit(0 if failures.is_empty() else 1)
