extends Node

## Autoload holding persistent DriverProfile and active CarBuild across scenes,
## plus save/load (.tres) and scene switching helpers.

signal scene_switched(scene_path: String)
signal active_car_changed(car_id: String, car_build: CarBuild)

const OVERWORLD_SCENE_PATH: String = "res://scenes/overworld/overworld.tscn"
const TRACK_LOOP_SCENE_PATH: String = "res://scenes/track/track_loop.tscn"
const DEFAULT_SAVE_PATH: String = "user://save_profile.tres"

var driver_profile: DriverProfile = DriverProfile.new()
var active_car_build: CarBuild = CarBuild.new()


func _ready() -> void:
	_ensure_valid_state()


func _ensure_valid_state() -> void:
	if driver_profile == null:
		driver_profile = DriverProfile.new()
	if active_car_build == null:
		active_car_build = CarBuild.new()


func reset_state() -> void:
	driver_profile = DriverProfile.new()
	active_car_build = CarBuild.new()


func get_or_create_car_build(car_id: String) -> CarBuild:
	_ensure_valid_state()
	var existing: Variant = driver_profile.car_builds.get(car_id)
	if existing is CarBuild:
		return existing as CarBuild
	var build := CarBuild.new()
	build.car_id = car_id
	if not car_id.is_empty():
		driver_profile.car_builds[car_id] = build
	return build


func set_active_car(car_id: String) -> CarBuild:
	_ensure_valid_state()
	if not car_id.is_empty() and not driver_profile.owned_car_ids.has(car_id):
		driver_profile.owned_car_ids.append(car_id)
	driver_profile.active_car_id = car_id
	active_car_build = get_or_create_car_build(car_id)
	active_car_changed.emit(car_id, active_car_build)
	return active_car_build


func save_state(path: String = DEFAULT_SAVE_PATH) -> Error:
	_ensure_valid_state()
	if not active_car_build.car_id.is_empty():
		driver_profile.car_builds[active_car_build.car_id] = active_car_build
		if driver_profile.active_car_id.is_empty():
			driver_profile.active_car_id = active_car_build.car_id
	return ResourceSaver.save(driver_profile, path)


func load_state(path: String = DEFAULT_SAVE_PATH) -> Error:
	if not ResourceLoader.exists(path):
		return ERR_FILE_NOT_FOUND
	var loaded: Resource = ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE)
	if loaded == null:
		return ERR_CANT_OPEN
	if not (loaded is DriverProfile):
		return ERR_INVALID_DATA
	driver_profile = loaded as DriverProfile
	var target_car_id: String = driver_profile.active_car_id
	if not target_car_id.is_empty():
		active_car_build = get_or_create_car_build(target_car_id)
	else:
		active_car_build = CarBuild.new()
	return OK


func goto_scene(scene_path: String) -> Error:
	if not ResourceLoader.exists(scene_path):
		push_error("GameState.goto_scene: scene not found: %s" % scene_path)
		return ERR_FILE_NOT_FOUND
	var err: Error = get_tree().change_scene_to_file(scene_path)
	if err == OK:
		scene_switched.emit(scene_path)
	return err


func goto_overworld() -> Error:
	return goto_scene(OVERWORLD_SCENE_PATH)


func goto_track_loop() -> Error:
	return goto_scene(TRACK_LOOP_SCENE_PATH)
