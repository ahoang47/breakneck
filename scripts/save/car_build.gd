class_name CarBuild
extends Resource

## Per-car build, installed parts, and mastery save data.
## Values default to 0/empty here; car stats, mod catalogs, specials,
## and mastery formulas will be mirrored from Silas's sim/ once landed.

@export var car_id: String = ""
@export var installed_parts: Dictionary = {} # String (slot/mod_class) -> String (part_id)
@export var owned_part_ids: Array[String] = []
@export var unlocked_special_ids: Array[String] = []
@export var mastery_xp: int = 0
@export var races_driven: int = 0
@export var wins: int = 0
