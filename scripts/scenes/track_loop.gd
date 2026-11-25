class_name TrackLoopScene
extends Node3D

## Empty closed-loop track root with minimal hook to return to the overworld.


func return_to_overworld() -> Error:
	return GameState.goto_overworld()
