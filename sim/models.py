"""Pure stdlib dataclasses for Breakneck progression."""

from __future__ import annotations

from dataclasses import dataclass, field

from sim.constants import (
    CAR_ROSTER,
    MOD_CATALOG,
    MOD_CLASSES,
    RACING_SPIRIT_SUBBRANCHES,
    TECHNIQUE_SUBBRANCHES,
)


@dataclass(frozen=True)
class CarSpec:
    """Static definition of a car from the roster."""

    car_id: str
    name: str
    tier: int
    primary_subbranch: str
    top_speed: float
    acceleration: float
    handling: float
    tech_reqs: dict[str, int]
    special_ids: tuple[str, ...]

    @property
    def base_stat_average(self) -> float:
        return (self.top_speed + self.acceleration + self.handling) / 3.0


@dataclass(frozen=True)
class ModPartSpec:
    """Static definition of a purchasable mod part from the shop catalog."""

    part_id: str
    name: str
    tier: int
    mod_class: str
    style_tag: str
    price: int
    top_speed_delta: float
    acceleration_delta: float
    handling_delta: float

    @property
    def stat_average_delta(self) -> float:
        return (
            self.top_speed_delta + self.acceleration_delta + self.handling_delta
        ) / 3.0


def load_roster() -> dict[str, CarSpec]:
    """Build CarSpec catalog from sim.constants.CAR_ROSTER."""
    catalog: dict[str, CarSpec] = {}
    for raw in CAR_ROSTER:
        spec = CarSpec(
            car_id=str(raw["car_id"]),
            name=str(raw["name"]),
            tier=int(raw["tier"]),
            primary_subbranch=str(raw["primary_subbranch"]),
            top_speed=float(raw["top_speed"]),
            acceleration=float(raw["acceleration"]),
            handling=float(raw["handling"]),
            tech_reqs={str(k): int(v) for k, v in dict(raw["tech_reqs"]).items()},
            special_ids=tuple(str(s) for s in raw["special_ids"]),
        )
        catalog[spec.car_id] = spec
    return catalog


def load_mod_catalog() -> dict[str, ModPartSpec]:
    """Build ModPartSpec lookup from sim.constants.MOD_CATALOG."""
    catalog: dict[str, ModPartSpec] = {}
    for raw in MOD_CATALOG:
        part = ModPartSpec(
            part_id=str(raw["part_id"]),
            name=str(raw["name"]),
            tier=int(raw["tier"]),
            mod_class=str(raw["mod_class"]),
            style_tag=str(raw["style_tag"]),
            price=int(raw["price"]),
            top_speed_delta=float(raw["top_speed_delta"]),
            acceleration_delta=float(raw["acceleration_delta"]),
            handling_delta=float(raw["handling_delta"]),
        )
        catalog[part.part_id] = part
    return catalog


@dataclass
class DriverState:
    """Persistent driver meta-progression (Technique, Racing Spirit branch, Stamina stat)."""

    technique_xp: dict[str, int] = field(
        default_factory=lambda: {branch: 0 for branch in TECHNIQUE_SUBBRANCHES}
    )
    racing_spirit_xp: dict[str, int] = field(
        default_factory=lambda: {branch: 0 for branch in RACING_SPIRIT_SUBBRANCHES}
    )
    stamina_xp: int = 0
    total_races: int = 0
    total_wins: int = 0


@dataclass
class CarState:
    """Per-car mastery, specials, and unique-per-car owned/equipped mod parts."""

    car_id: str
    xp: int = 0
    races_driven: int = 0
    wins: int = 0
    owned_parts: set[str] = field(default_factory=set)
    equipped_parts: dict[str, str | None] = field(
        default_factory=lambda: {mod_class: None for mod_class in MOD_CLASSES}
    )
    special_levels: dict[str, int] = field(default_factory=dict)
    special_progress: dict[str, float] = field(default_factory=dict)


@dataclass
class RaceOutcome:
    """Inputs from a single expressway duel into progression."""

    won: bool
    rival_tier: int
    clean_race: bool = True
    maneuvers: dict[str, int] = field(default_factory=dict)
    # Allocation weights for earned Driver XP across Technique, Racing Spirit, Stamina.
    technique_share: float = 0.60
    racing_spirit_share: float = 0.22
    stamina_share: float = 0.18
    # Optional explicit Technique subbranch target; defaults to driven car's primary.
    technique_target: str | None = None
    # Optional explicit Racing Spirit subbranch target; defaults to even split.
    racing_spirit_target: str | None = None


@dataclass
class PlayerProfile:
    """Complete progression save state (Driver, shared wallet, and Cars)."""

    driver: DriverState = field(default_factory=DriverState)
    credits: int = 0
    cars: dict[str, CarState] = field(default_factory=dict)
    active_car_id: str = "t1_s13"

    def get_or_create_car(self, spec: CarSpec) -> CarState:
        if spec.car_id not in self.cars:
            self.cars[spec.car_id] = CarState(
                car_id=spec.car_id,
                special_levels={sid: 0 for sid in spec.special_ids},
                special_progress={sid: 0.0 for sid in spec.special_ids},
            )
        return self.cars[spec.car_id]
