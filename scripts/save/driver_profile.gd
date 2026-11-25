class_name DriverProfile
extends Resource

## Persistent driver-wide save data shared across all scenes and cars.
## Values default to 0/empty here; progression fields and balance constants
## will be mirrored from Silas's sim/ once landed.

@export var schema_version: int = 0
@export var driver_name: String = ""
@export var unlocks: Array[String] = []
@export var owned_car_ids: Array[String] = []
@export var active_car_id: String = ""
@export var car_builds: Dictionary = {} # String (car_id) -> CarBuild

# Placeholder progression counters (populated/tuned from sim/ later).
@export var credits: int = 0
@export var technique_xp: Dictionary = {}
@export var racing_spirit_xp: Dictionary = {}
@export var stamina_xp: int = 0
@export var total_races: int = 0
@export var total_wins: int = 0
