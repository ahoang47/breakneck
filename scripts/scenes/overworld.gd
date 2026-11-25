class_name OverworldScene
extends Node3D

## Empty overworld root with minimal hook to enter a closed-loop track.


func enter_track(track_scene_path: String = GameState.TRACK_LOOP_SCENE_PATH) -> Error:
	return GameState.goto_scene(track_scene_path)
