extends Node

## Headless verification test for Breakneck's Godot 4.6 skeleton:
## 1. GameState autoload exists with DriverProfile and CarBuild.
## 2. Profile/build values and object identity persist across Overworld -> TrackLoop -> Overworld.
## 3. TrackLoop contains a closed Path3D placeholder with no geometry/art.
## 4. Save/load (.tres) round-trip restores DriverProfile and nested CarBuild values.

const TEST_SAVE_PATH: String = "user://test_skeleton_save.tres"


class SkeletonTestRunner extends Node:
	var _failures: Array[String] = []
	var _tree: SceneTree

	func _ready() -> void:
		_tree = get_tree()
		call_deferred("_start_suite")

	func _start_suite() -> void:
		await _run_tests()
		_cleanup_test_save()
		if _failures.is_empty():
			print("PASS: Breakneck skeleton headless tests succeeded.")
			_tree.quit(0)
		else:
			for msg: String in _failures:
				push_error("FAIL: " + msg)
				printerr("FAIL: " + msg)
			_tree.quit(1)

	func _assert(cond: bool, message: String) -> void:
		if not cond:
			_failures.append(message)

	func _wait_for_scene(expected_path: String, max_frames: int = 30) -> Node:
		for _i in range(max_frames):
			await _tree.process_frame
			var cur: Node = _tree.current_scene
			if cur != null and cur.scene_file_path == expected_path:
				return cur
		return null

	func _run_tests() -> void:
		var gs: Node = _tree.root.get_node_or_null("GameState")
		_assert(gs != null, "GameState autoload must be registered at /root/GameState")
		if gs == null:
			return

		# 1. Switch to Overworld and verify clean empty root.
		var err: Error = gs.goto_overworld()
		_assert(err == OK, "goto_overworld() returned error %d" % err)
		var overworld: Node = await _wait_for_scene(gs.OVERWORLD_SCENE_PATH)
		_assert(overworld != null, "Failed to switch to Overworld scene")
		_assert(overworld is OverworldScene, "Overworld root must use OverworldScene script")
		if overworld == null:
			return

		# 2. Populate DriverProfile and CarBuild (no balance constants, pure test data).
		gs.reset_state()
		var profile: DriverProfile = gs.driver_profile
		_assert(profile != null, "GameState.driver_profile must not be null")
		profile.schema_version = 1
		profile.driver_name = "TestDriver"
		profile.unlocks = ["route_loop_test"]
		profile.credits = 1234
		profile.technique_xp = {"grip": 10}
		profile.racing_spirit_xp = {"draft": 5}
		profile.stamina_xp = 20
		profile.total_races = 3
		profile.total_wins = 2

		var build: CarBuild = gs.set_active_car("car_test_01")
		_assert(build != null, "set_active_car() must return a CarBuild")
		build.installed_parts = {"exhaust": "part_exhaust_01", "tires": "part_tires_01"}
		build.owned_part_ids = ["part_exhaust_01", "part_tires_01"]
		build.unlocked_special_ids = ["special_test_01"]
		build.mastery_xp = 45
		build.races_driven = 3
		build.wins = 2

		# 3. Overworld -> TrackLoop via scene hook.
		err = (overworld as OverworldScene).enter_track()
		_assert(err == OK, "OverworldScene.enter_track() returned error %d" % err)
		var track: Node = await _wait_for_scene(gs.TRACK_LOOP_SCENE_PATH)
		_assert(track != null, "Failed to switch to TrackLoop scene")
		_assert(track is TrackLoopScene, "TrackLoop root must use TrackLoopScene script")
		if track == null:
			return

		var loop_path: Path3D = track.get_node_or_null("LoopPath") as Path3D
		_assert(loop_path != null, "TrackLoop must have LoopPath Path3D child")
		if loop_path != null:
			_assert(loop_path.curve != null and loop_path.curve.closed, "LoopPath Curve3D must be closed")

		# Verify exact same instances and values persisted across Overworld -> TrackLoop.
		_assert(is_same(gs.driver_profile, profile), "DriverProfile instance must persist to TrackLoop")
		_assert(is_same(gs.active_car_build, build), "Active CarBuild instance must persist to TrackLoop")
		_assert(gs.driver_profile.driver_name == "TestDriver", "driver_name must persist on TrackLoop")
		_assert(gs.driver_profile.owned_car_ids == ["car_test_01"], "owned_car_ids must persist on TrackLoop")
		_assert(gs.active_car_build.car_id == "car_test_01", "active car_id must persist on TrackLoop")
		_assert(gs.active_car_build.installed_parts.get("exhaust") == "part_exhaust_01", "installed_parts must persist on TrackLoop")

		# 4. TrackLoop -> Overworld via scene hook.
		err = (track as TrackLoopScene).return_to_overworld()
		_assert(err == OK, "TrackLoopScene.return_to_overworld() returned error %d" % err)
		var overworld_again: Node = await _wait_for_scene(gs.OVERWORLD_SCENE_PATH)
		_assert(overworld_again != null, "Failed to switch back to Overworld scene")

		_assert(is_same(gs.driver_profile, profile), "DriverProfile instance must persist back to Overworld")
		_assert(is_same(gs.active_car_build, build), "Active CarBuild instance must persist back to Overworld")
		_assert(gs.driver_profile.credits == 1234, "credits must persist back to Overworld")
		_assert(gs.active_car_build.mastery_xp == 45, "mastery_xp must persist back to Overworld")

		# 5. Save/load .tres round-trip.
		_cleanup_test_save()
		err = gs.save_state(TEST_SAVE_PATH)
		_assert(err == OK, "save_state() returned error %d" % err)

		gs.reset_state()
		_assert(gs.driver_profile.driver_name == "", "reset_state() should clear driver_name")
		_assert(not is_same(gs.driver_profile, profile), "reset_state() should create a fresh DriverProfile")

		err = gs.load_state(TEST_SAVE_PATH)
		_assert(err == OK, "load_state() returned error %d" % err)
		_assert(gs.driver_profile.schema_version == 1, "Loaded schema_version mismatch")
		_assert(gs.driver_profile.driver_name == "TestDriver", "Loaded driver_name mismatch")
		_assert(gs.driver_profile.unlocks == ["route_loop_test"], "Loaded unlocks mismatch")
		_assert(gs.driver_profile.owned_car_ids == ["car_test_01"], "Loaded owned_car_ids mismatch")
		_assert(gs.driver_profile.active_car_id == "car_test_01", "Loaded active_car_id mismatch")
		_assert(gs.driver_profile.credits == 1234, "Loaded credits mismatch")
		_assert(gs.driver_profile.technique_xp.get("grip") == 10, "Loaded technique_xp mismatch")
		_assert(gs.driver_profile.racing_spirit_xp.get("draft") == 5, "Loaded racing_spirit_xp mismatch")
		_assert(gs.driver_profile.stamina_xp == 20, "Loaded stamina_xp mismatch")
		_assert(gs.active_car_build != null, "Loaded active_car_build must not be null")
		_assert(gs.active_car_build.car_id == "car_test_01", "Loaded CarBuild car_id mismatch")
		_assert(gs.active_car_build.installed_parts.get("tires") == "part_tires_01", "Loaded CarBuild installed_parts mismatch")
		_assert(gs.active_car_build.owned_part_ids == ["part_exhaust_01", "part_tires_01"], "Loaded CarBuild owned_part_ids mismatch")
		_assert(gs.active_car_build.unlocked_special_ids == ["special_test_01"], "Loaded CarBuild unlocked_special_ids mismatch")
		_assert(gs.active_car_build.mastery_xp == 45, "Loaded CarBuild mastery_xp mismatch")
		_assert(gs.active_car_build.races_driven == 3, "Loaded CarBuild races_driven mismatch")
		_assert(gs.active_car_build.wins == 2, "Loaded CarBuild wins mismatch")

	func _cleanup_test_save() -> void:
		if FileAccess.file_exists(TEST_SAVE_PATH):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(TEST_SAVE_PATH))


func _ready() -> void:
	var runner := SkeletonTestRunner.new()
	runner.name = "SkeletonTestRunner"
	get_tree().root.add_child.call_deferred(runner)
