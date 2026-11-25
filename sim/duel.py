"""Tick-based closed-loop duel rules, multi-track profiles, spline-gap math, and sweep."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from sim.constants import (
    CAR_MASTERY_XP_THRESHOLDS,
    DUEL_ACCEL_BASE_MPS2,
    DUEL_ACCEL_PER_STAT_MPS2,
    DUEL_BRAKE_RATE_MPS2,
    DUEL_CLEAN_DRIFT_PROB_PER_CORNER,
    DUEL_CONTACT_COOLDOWN_S,
    DUEL_CONTACT_DEFENDER_SHARE,
    DUEL_CONTACT_DRAIN_MAX,
    DUEL_CONTACT_DRAIN_PER_MPS,
    DUEL_CONTACT_EQUAL_SHARE,
    DUEL_CONTACT_INITIATOR_SHARE,
    DUEL_CONTACT_MIN_IMPACT_MPS,
    DUEL_CONTACT_PROB_PER_S,
    DUEL_CONTACT_PROXIMITY_M,
    DUEL_CONTACT_SAMPLE_IMPACT_MAX_MPS,
    DUEL_CONTACT_SAMPLE_IMPACT_MIN_MPS,
    DUEL_CONTACT_SPEED_SCRUB_RATIO,
    DUEL_CORNER_BASE_MPS,
    DUEL_CORNER_PER_HANDLING_MPS,
    DUEL_DEFAULT_TRACK_ID,
    DUEL_GAP_DEAD_ZONE_M,
    DUEL_GAP_DRAIN_BASE_PER_S,
    DUEL_GAP_DRAIN_CAP_PER_S,
    DUEL_GAP_DRAIN_SLOPE_PER_M_S,
    DUEL_MIN_SPEED_MPS,
    DUEL_NEAR_MISS_PROB_PER_S,
    DUEL_RACING_SPIRIT_LEAD_RATE_PER_S,
    DUEL_SKILL_NOISE_DECAY,
    DUEL_SKILL_NOISE_STD_MPS,
    DUEL_SLIPSTREAM_MAX_GAP_M,
    DUEL_SLIPSTREAM_SPEED_BONUS_MPS,
    DUEL_SLIPSTREAM_TICK_INTERVAL_S,
    DUEL_SPECIAL_BASE_SPEED_BONUS_MPS,
    DUEL_SPECIAL_COST,
    DUEL_SPECIAL_DURATION_S,
    DUEL_SPECIAL_SPEED_BONUS_PER_LEVEL_MPS,
    DUEL_SPEED_BASE_MPS,
    DUEL_SPEED_PER_STAT_MPS,
    DUEL_STAMINA_PCT_TIE_EPS,
    DUEL_TICK_DT_S,
    DUEL_TRACKS,
    DUEL_WALL_CORNER_EXPOSURE_MULT,
    DUEL_WALL_DRAIN_MAX,
    DUEL_WALL_DRAIN_PER_MPS,
    DUEL_WALL_HIT_PROB_PER_S,
    DUEL_WALL_MIN_IMPACT_MPS,
    DUEL_WALL_SAMPLE_IMPACT_MAX_MPS,
    DUEL_WALL_SAMPLE_IMPACT_MIN_MPS,
    DUEL_WALL_SPEED_SCRUB_RATIO,
    DUEL_WALL_STRAIGHT_EXPOSURE_MULT,
    MOD_CLASSES,
    RACING_SPIRIT_GAIN_PER_LEVEL,
    RACING_SPIRIT_METER_MAX,
    RACING_SPIRIT_SUBBRANCHES,
    RACING_SPIRIT_XP_THRESHOLDS,
    STAMINA_XP_THRESHOLDS,
    TECHNIQUE_SUBBRANCHES,
    TECHNIQUE_XP_THRESHOLDS,
)
from sim.models import (
    CarSpec,
    CarState,
    DriverState,
    ModPartSpec,
    PlayerProfile,
    load_mod_catalog,
    load_roster,
)
from sim.rules import (
    buy_mod_part,
    compute_racing_spirit_meter_gain,
    compute_racing_spirit_passives,
    compute_stamina_bar_max,
    effective_car_mastery,
    effective_car_stats,
    effective_special_levels,
    racing_spirit_level,
)

_DEFAULT_TRACK = DUEL_TRACKS[DUEL_DEFAULT_TRACK_ID]


# ---------------------------------------------------------------------------
# Pure Closed-Loop Duel Rule Functions (mirrored by Godot parity tests)
# ---------------------------------------------------------------------------
def wrapped_spline_delta(
    offset_a: float,
    offset_b: float,
    loop_length_m: float = float(_DEFAULT_TRACK["loop_length_m"]),
) -> float:
    """Shortest signed arc-length delta (offset_a - offset_b) on a closed loop.

    Wraps across the 0 / loop_length_m seam into [-loop_length_m/2, +loop_length_m/2).
    Positive means A is ahead of B along the closed loop (for gaps < half a lap).
    """
    if loop_length_m <= 0.0:
        raise ValueError("loop_length_m must be positive")
    raw = (offset_a - offset_b) % loop_length_m
    half = 0.5 * loop_length_m
    if raw >= half:
        raw -= loop_length_m
    return raw


def progress_gap(
    laps_a: int,
    offset_a: float,
    laps_b: int,
    offset_b: float,
    loop_length_m: float = float(_DEFAULT_TRACK["loop_length_m"]),
) -> float:
    """Exact signed progress difference (progress_a - progress_b) in meters."""
    if loop_length_m <= 0.0:
        raise ValueError("loop_length_m must be positive")
    return (laps_a * loop_length_m + offset_a) - (laps_b * loop_length_m + offset_b)


def compute_gap_drain_rate(
    gap_m: float,
    elapsed_s: float,
    grace_period_s: float = float(_DEFAULT_TRACK["grace_period_s"]),
) -> float:
    """Stamina drain rate (units/sec) applied to the trailing car from track gap.

    Returns 0.0 during the rolling-start grace period or inside the dead zone.
    Clamped at DUEL_GAP_DRAIN_CAP_PER_S. Leader never takes gap drain.
    """
    if elapsed_s < grace_period_s:
        return 0.0
    if gap_m <= DUEL_GAP_DEAD_ZONE_M:
        return 0.0
    raw = DUEL_GAP_DRAIN_BASE_PER_S + DUEL_GAP_DRAIN_SLOPE_PER_M_S * (
        gap_m - DUEL_GAP_DEAD_ZONE_M
    )
    return min(DUEL_GAP_DRAIN_CAP_PER_S, raw)


def compute_wall_hit_drain(
    impact_speed_mps: float,
    wall_penalty_reduction: float = 0.0,
) -> float:
    """Clamped Stamina drain from a wall impact, mitigated by slipstream_nerve passive."""
    if impact_speed_mps <= DUEL_WALL_MIN_IMPACT_MPS:
        return 0.0
    raw = (impact_speed_mps - DUEL_WALL_MIN_IMPACT_MPS) * DUEL_WALL_DRAIN_PER_MPS
    clamped = min(DUEL_WALL_DRAIN_MAX, max(0.0, raw))
    reduction = min(0.75, max(0.0, wall_penalty_reduction))
    return clamped * (1.0 - reduction)


def compute_contact_drain(
    impact_speed_mps: float,
    initiator_is_a: bool | None,
) -> tuple[float, float]:
    """Clamped Stamina drain (drain_a, drain_b) from car-to-car contact.

    Default rule: asymmetric shared drain (initiator/trailing car takes 100%,
    defending/leading car takes 60%; dead-heat side-by-side takes 80% each).
    """
    if impact_speed_mps <= DUEL_CONTACT_MIN_IMPACT_MPS:
        return (0.0, 0.0)
    raw = (impact_speed_mps - DUEL_CONTACT_MIN_IMPACT_MPS) * DUEL_CONTACT_DRAIN_PER_MPS
    clamped = min(DUEL_CONTACT_DRAIN_MAX, max(0.0, raw))
    if initiator_is_a is True:
        return (
            clamped * DUEL_CONTACT_INITIATOR_SHARE,
            clamped * DUEL_CONTACT_DEFENDER_SHARE,
        )
    if initiator_is_a is False:
        return (
            clamped * DUEL_CONTACT_DEFENDER_SHARE,
            clamped * DUEL_CONTACT_INITIATOR_SHARE,
        )
    return (
        clamped * DUEL_CONTACT_EQUAL_SHARE,
        clamped * DUEL_CONTACT_EQUAL_SHARE,
    )


def resolve_lap_cap_winner(
    stamina_a: float,
    stamina_a_max: float,
    stamina_b: float,
    stamina_b_max: float,
    progress_a: float,
    progress_b: float,
) -> tuple[str, str]:
    """Decide winner ('a' or 'b') and reason when lap cap triggers."""
    pct_a = max(0.0, stamina_a) / stamina_a_max if stamina_a_max > 0.0 else 0.0
    pct_b = max(0.0, stamina_b) / stamina_b_max if stamina_b_max > 0.0 else 0.0
    if abs(pct_a - pct_b) > DUEL_STAMINA_PCT_TIE_EPS:
        return ("a" if pct_a > pct_b else "b", "lap_cap_stamina_pct")
    if abs(progress_a - progress_b) > 1e-6:
        return ("a" if progress_a > progress_b else "b", "lap_cap_gap")
    return ("b", "lap_cap_defender_tie")


# ---------------------------------------------------------------------------
# Duel Simulation Data Structures
# ---------------------------------------------------------------------------
@dataclass
class DuelEntrant:
    """One car+driver entry in a two-car closed-loop duel."""

    entrant_id: str
    profile: PlayerProfile
    car_spec: CarSpec
    skill_rating: float = 1.0
    initial_spirit_carryover: float = 0.0


@dataclass(frozen=True)
class DuelConfig:
    track_id: str = DUEL_DEFAULT_TRACK_ID
    loop_length_m: float | None = None
    max_laps: int | None = None
    dt_s: float = DUEL_TICK_DT_S
    start_speed_mps: float | None = None
    start_gap_m: float | None = None
    grace_period_s: float | None = None
    corners_per_lap: int | None = None
    corner_duty: float | None = None
    wall_hit_rate_mult: float | None = None
    contact_rate_mult: float | None = None

    @classmethod
    def from_track(cls, track_id: str) -> DuelConfig:
        if track_id not in DUEL_TRACKS:
            raise ValueError(f"Unknown duel track_id {track_id!r}")
        return cls(track_id=track_id)

    def resolved(self) -> _ResolvedTrackConfig:
        if self.track_id not in DUEL_TRACKS:
            raise ValueError(f"Unknown duel track_id {self.track_id!r}")
        tr = DUEL_TRACKS[self.track_id]
        return _ResolvedTrackConfig(
            track_id=self.track_id,
            loop_length_m=float(self.loop_length_m if self.loop_length_m is not None else tr["loop_length_m"]),
            max_laps=int(self.max_laps if self.max_laps is not None else tr["max_laps"]),
            dt_s=float(self.dt_s),
            start_speed_mps=float(self.start_speed_mps if self.start_speed_mps is not None else tr["start_speed_mps"]),
            start_gap_m=float(self.start_gap_m if self.start_gap_m is not None else tr["start_gap_m"]),
            grace_period_s=float(self.grace_period_s if self.grace_period_s is not None else tr["grace_period_s"]),
            corners_per_lap=int(self.corners_per_lap if self.corners_per_lap is not None else tr["corners_per_lap"]),
            corner_duty=float(self.corner_duty if self.corner_duty is not None else tr["corner_duty"]),
            wall_hit_rate_mult=float(self.wall_hit_rate_mult if self.wall_hit_rate_mult is not None else tr["wall_hit_rate_mult"]),
            contact_rate_mult=float(self.contact_rate_mult if self.contact_rate_mult is not None else tr["contact_rate_mult"]),
        )


@dataclass(frozen=True)
class _ResolvedTrackConfig:
    track_id: str
    loop_length_m: float
    max_laps: int
    dt_s: float
    start_speed_mps: float
    start_gap_m: float
    grace_period_s: float
    corners_per_lap: int
    corner_duty: float
    wall_hit_rate_mult: float
    contact_rate_mult: float


@dataclass
class DuelResult:
    track_id: str
    winner: str
    loser: str
    finish_reason: str
    duration_s: float
    ticks: int
    laps_completed_leader: float
    final_gap_m: float  # signed challenger_progress - rival_progress
    challenger_stamina_remaining: float
    challenger_stamina_max: float
    challenger_stamina_pct: float
    rival_stamina_remaining: float
    rival_stamina_max: float
    rival_stamina_pct: float
    challenger_spirit_gained_total: float
    challenger_spirit_end: float
    challenger_specials_used: int
    rival_specials_used: int
    challenger_wall_hits: int
    rival_wall_hits: int
    contact_events: int
    overtakes: int
    challenger_maneuvers: dict[str, int]
    challenger_clean_race: bool


@dataclass
class _CarRuntime:
    entrant: DuelEntrant
    stats: dict[str, float]
    passives: dict[str, float]
    avg_special_level: float
    stamina_max: float
    stamina: float
    spirit_meter: float
    spirit_gained_total: float
    distance_m: float
    speed_mps: float
    noise_mps: float = 0.0
    slipstream_accum_s: float = 0.0
    special_timer_s: float = 0.0
    specials_used: int = 0
    wall_hits: int = 0
    last_sector_idx: int = -1
    sector_clean: bool = True
    maneuvers: dict[str, int] = field(
        default_factory=lambda: {
            "clean_drift": 0,
            "slipstream_tick": 0,
            "near_miss": 0,
            "clean_overtake": 0,
        }
    )


def _init_runtime(
    entrant: DuelEntrant,
    start_distance_m: float,
    start_speed_mps: float,
    mod_catalog: dict[str, ModPartSpec],
) -> _CarRuntime:
    car_state = entrant.profile.cars.get(entrant.car_spec.car_id)
    if car_state is None:
        car_state = entrant.profile.get_or_create_car(entrant.car_spec)

    stats = effective_car_stats(entrant.profile, entrant.car_spec, catalog=mod_catalog)
    passives = compute_racing_spirit_passives(entrant.profile.driver)
    mastery = effective_car_mastery(entrant.profile.driver, entrant.car_spec, car_state)
    specials = effective_special_levels(entrant.car_spec, car_state, mastery)
    avg_spec = sum(specials.values()) / len(specials) if specials else 0.0

    stamina_max = compute_stamina_bar_max(entrant.profile.driver)
    carryover_ratio = passives.get("racing_spirit_carryover_ratio_per_level", 0.0)
    start_spirit = min(
        RACING_SPIRIT_METER_MAX,
        max(0.0, entrant.initial_spirit_carryover) * carryover_ratio,
    )

    return _CarRuntime(
        entrant=entrant,
        stats=stats,
        passives=passives,
        avg_special_level=avg_spec,
        stamina_max=stamina_max,
        stamina=stamina_max,
        spirit_meter=start_spirit,
        spirit_gained_total=0.0,
        distance_m=start_distance_m,
        speed_mps=start_speed_mps,
    )


def _add_spirit(car: _CarRuntime, raw_amount: float) -> None:
    if raw_amount <= 0.0:
        return
    space = max(0.0, RACING_SPIRIT_METER_MAX - car.spirit_meter)
    added = min(space, raw_amount)
    car.spirit_meter += added
    car.spirit_gained_total += added


def _sector_state(
    offset_m: float, loop_length_m: float, corners_per_lap: int, corner_duty: float
) -> tuple[bool, int]:
    """Return (in_corner, sector_idx) along a closed-loop track profile."""
    if corners_per_lap <= 0:
        return False, 0
    scaled = (offset_m / loop_length_m) * corners_per_lap
    sector = int(scaled) % corners_per_lap
    u = scaled - math.floor(scaled)
    return u < corner_duty, sector


def _target_speed_mps(
    car: _CarRuntime,
    in_corner: bool,
    in_slipstream: bool,
) -> float:
    straight_v = DUEL_SPEED_BASE_MPS + DUEL_SPEED_PER_STAT_MPS * car.stats["top_speed"]
    corner_v = DUEL_CORNER_BASE_MPS + DUEL_CORNER_PER_HANDLING_MPS * car.stats["handling"]
    skill_factor = 1.0 + 0.25 * (car.entrant.skill_rating - 1.0)

    base_v = (corner_v if in_corner else straight_v) * skill_factor
    slip_bonus = DUEL_SLIPSTREAM_SPEED_BONUS_MPS if in_slipstream else 0.0
    spec_bonus = (
        DUEL_SPECIAL_BASE_SPEED_BONUS_MPS
        + DUEL_SPECIAL_SPEED_BONUS_PER_LEVEL_MPS * car.avg_special_level
        if car.special_timer_s > 0.0
        else 0.0
    )

    return max(DUEL_MIN_SPEED_MPS, base_v + slip_bonus + spec_bonus + car.noise_mps)


def run_duel(
    challenger: DuelEntrant,
    rival: DuelEntrant,
    seed: int = 0,
    config: DuelConfig | None = None,
    catalog: dict[str, ModPartSpec] | None = None,
) -> DuelResult:
    """Run a deterministic tick-based closed-loop duel between challenger and rival."""
    cfg = (config if config is not None else DuelConfig()).resolved()
    if cfg.loop_length_m <= 0.0:
        raise ValueError("loop_length_m must be positive")
    if cfg.max_laps < 1:
        raise ValueError("max_laps must be >= 1")
    if cfg.dt_s <= 0.0:
        raise ValueError("dt_s must be positive")

    mod_catalog = catalog if catalog is not None else load_mod_catalog()
    rng = random.Random(seed)

    car_a = _init_runtime(challenger, 0.0, cfg.start_speed_mps, mod_catalog)
    car_b = _init_runtime(rival, cfg.start_gap_m, cfg.start_speed_mps, mod_catalog)

    elapsed_s = 0.0
    ticks = 0
    max_distance_m = cfg.max_laps * cfg.loop_length_m
    noise_innov_std = DUEL_SKILL_NOISE_STD_MPS * math.sqrt(
        max(1e-6, 1.0 - DUEL_SKILL_NOISE_DECAY**2)
    )

    contact_cooldown_s = 0.0
    contact_events = 0
    overtakes = 0
    prev_leader: str = "b" if cfg.start_gap_m > 0.0 else "a"
    finish_reason = "lap_cap_stamina_pct"
    winner_slot = "b"

    while True:
        ticks += 1
        elapsed_s += cfg.dt_s
        contact_cooldown_s = max(0.0, contact_cooldown_s - cfg.dt_s)

        gap_ab = car_a.distance_m - car_b.distance_m
        leader_slot = "a" if gap_ab > 0.0 else ("b" if gap_ab < 0.0 else prev_leader)
        abs_gap = abs(gap_ab)

        # 1. Update driver skill noise, Special timers, braking/corner-exit kinematics, and maneuvers
        for slot, car in (("a", car_a), ("b", car_b)):
            if car.special_timer_s > 0.0:
                car.special_timer_s = max(0.0, car.special_timer_s - cfg.dt_s)
            elif car.spirit_meter >= DUEL_SPECIAL_COST:
                # Specials spend Racing Spirit, NEVER Stamina.
                car.spirit_meter -= DUEL_SPECIAL_COST
                car.special_timer_s = DUEL_SPECIAL_DURATION_S
                car.specials_used += 1

            car.noise_mps = (
                DUEL_SKILL_NOISE_DECAY * car.noise_mps
                + rng.gauss(0.0, noise_innov_std)
            )
            in_slipstream = (
                slot != leader_slot and 0.0 < abs_gap <= DUEL_SLIPSTREAM_MAX_GAP_M
            )
            offset_m = car.distance_m % cfg.loop_length_m
            in_corner, sector = _sector_state(
                offset_m, cfg.loop_length_m, cfg.corners_per_lap, cfg.corner_duty
            )
            target_v = _target_speed_mps(car, in_corner, in_slipstream)

            if target_v >= car.speed_mps:
                # Corner-exit / straight pull depends on acceleration + drift_flow traction passive
                traction_mult = 1.0 + car.passives.get("corner_exit_traction_per_level", 0.0)
                max_up = (
                    (DUEL_ACCEL_BASE_MPS2 + DUEL_ACCEL_PER_STAT_MPS2 * car.stats["acceleration"])
                    * traction_mult
                    * cfg.dt_s
                )
                car.speed_mps = min(target_v, car.speed_mps + max_up)
            else:
                # Braking into corner apexes
                max_down = DUEL_BRAKE_RATE_MPS2 * cfg.dt_s
                car.speed_mps = max(DUEL_MIN_SPEED_MPS, max(target_v, car.speed_mps - max_down))

            car.distance_m += car.speed_mps * cfg.dt_s

            # Corner exit clean_drift Racing Spirit check
            if sector != car.last_sector_idx:
                if car.last_sector_idx != -1 and car.sector_clean:
                    if rng.random() < DUEL_CLEAN_DRIFT_PROB_PER_CORNER:
                        car.maneuvers["clean_drift"] += 1
                        gain = compute_racing_spirit_meter_gain(
                            car.entrant.profile.driver, {"clean_drift": 1}
                        )
                        _add_spirit(car, gain)
                car.last_sector_idx = sector
                car.sector_clean = True

            # Barrier-shave near-miss Racing Spirit check (no traffic on closed loops)
            if rng.random() < DUEL_NEAR_MISS_PROB_PER_S * cfg.dt_s:
                car.maneuvers["near_miss"] += 1
                gain = compute_racing_spirit_meter_gain(
                    car.entrant.profile.driver, {"near_miss": 1}
                )
                _add_spirit(car, gain)

        # 2. Wall-hit random process (scaled by track wall_hit_rate_mult and stat_average)
        wall_hit_this_tick = {"a": False, "b": False}
        for slot, car in (("a", car_a), ("b", car_b)):
            avg_factor = max(0.75, 1.05 - 0.001 * car.stats["stat_average"])
            skill_factor = max(0.5, 1.0 / max(0.5, car.entrant.skill_rating))
            offset_m = car.distance_m % cfg.loop_length_m
            in_corner, _ = _sector_state(
                offset_m, cfg.loop_length_m, cfg.corners_per_lap, cfg.corner_duty
            )
            exposure_mult = (
                DUEL_WALL_CORNER_EXPOSURE_MULT
                if in_corner
                else DUEL_WALL_STRAIGHT_EXPOSURE_MULT
            )
            p_wall = min(
                0.5,
                DUEL_WALL_HIT_PROB_PER_S
                * cfg.dt_s
                * cfg.wall_hit_rate_mult
                * avg_factor
                * skill_factor
                * exposure_mult,
            )
            if rng.random() < p_wall:
                wall_hit_this_tick[slot] = True
                car.wall_hits += 1
                car.sector_clean = False
                impact = rng.uniform(
                    DUEL_WALL_SAMPLE_IMPACT_MIN_MPS, DUEL_WALL_SAMPLE_IMPACT_MAX_MPS
                )
                wall_red = car.passives.get("wall_stamina_penalty_reduction_per_level", 0.0)
                drain = compute_wall_hit_drain(impact, wall_penalty_reduction=wall_red)
                car.stamina -= drain
                car.speed_mps = max(
                    DUEL_MIN_SPEED_MPS,
                    car.speed_mps * (1.0 - DUEL_WALL_SPEED_SCRUB_RATIO),
                )

        # 3. Car-to-car contact random process when proximate
        new_gap_ab = car_a.distance_m - car_b.distance_m
        contact_this_tick = False
        if (
            abs(new_gap_ab) <= DUEL_CONTACT_PROXIMITY_M
            and contact_cooldown_s <= 0.0
            and rng.random() < min(0.5, DUEL_CONTACT_PROB_PER_S * cfg.dt_s * cfg.contact_rate_mult)
        ):
            contact_this_tick = True
            contact_events += 1
            contact_cooldown_s = DUEL_CONTACT_COOLDOWN_S
            impact = rng.uniform(
                DUEL_CONTACT_SAMPLE_IMPACT_MIN_MPS, DUEL_CONTACT_SAMPLE_IMPACT_MAX_MPS
            )
            if abs(new_gap_ab) < 0.75:
                initiator_is_a: bool | None = None
            else:
                initiator_is_a = new_gap_ab < 0.0
            drain_a, drain_b = compute_contact_drain(impact, initiator_is_a)
            car_a.stamina -= drain_a
            car_b.stamina -= drain_b
            car_a.speed_mps = max(
                DUEL_MIN_SPEED_MPS,
                car_a.speed_mps * (1.0 - DUEL_CONTACT_SPEED_SCRUB_RATIO),
            )
            car_b.speed_mps = max(
                DUEL_MIN_SPEED_MPS,
                car_b.speed_mps * (1.0 - DUEL_CONTACT_SPEED_SCRUB_RATIO),
            )

        # 4. Track-gap Stamina drain (trailing car drains; leader gap drain = 0)
        new_leader = "a" if new_gap_ab > 0.0 else ("b" if new_gap_ab < 0.0 else prev_leader)
        abs_new_gap = abs(new_gap_ab)
        gap_rate = compute_gap_drain_rate(
            abs_new_gap, elapsed_s, grace_period_s=cfg.grace_period_s
        )
        if new_gap_ab > 0.0:
            car_b.stamina -= gap_rate * cfg.dt_s
        elif new_gap_ab < 0.0:
            car_a.stamina -= gap_rate * cfg.dt_s

        # 5. Racing Spirit fill from leading, slipstream, and clean overtakes
        # Gate positional Racing Spirit gains on grace_period_s so the trailing
        # rolling-start challenger does not harvest free slipstream/overtake Spirit
        # while the leader is barred from earning lead Spirit.
        if new_leader != prev_leader:
            overtakes += 1
            if elapsed_s >= cfg.grace_period_s and not contact_this_tick:
                overtaker = car_a if new_leader == "a" else car_b
                overtaker.maneuvers["clean_overtake"] += 1
                gain = compute_racing_spirit_meter_gain(
                    overtaker.entrant.profile.driver, {"clean_overtake": 1}
                )
                _add_spirit(overtaker, gain)
            prev_leader = new_leader

        if elapsed_s >= cfg.grace_period_s:
            if not wall_hit_this_tick[new_leader]:
                leader_car = car_a if new_leader == "a" else car_b
                clean_lvl = racing_spirit_level(leader_car.entrant.profile.driver, "clean_line")
                lead_gain = (
                    DUEL_RACING_SPIRIT_LEAD_RATE_PER_S
                    * cfg.dt_s
                    * (1.0 + RACING_SPIRIT_GAIN_PER_LEVEL * clean_lvl)
                )
                _add_spirit(leader_car, lead_gain)

            trailer_car = car_b if new_leader == "a" else car_a
            if 0.0 < abs_new_gap <= DUEL_SLIPSTREAM_MAX_GAP_M:
                trailer_car.slipstream_accum_s += cfg.dt_s
                while trailer_car.slipstream_accum_s >= DUEL_SLIPSTREAM_TICK_INTERVAL_S:
                    trailer_car.slipstream_accum_s -= DUEL_SLIPSTREAM_TICK_INTERVAL_S
                    trailer_car.maneuvers["slipstream_tick"] += 1
                    gain = compute_racing_spirit_meter_gain(
                        trailer_car.entrant.profile.driver, {"slipstream_tick": 1}
                    )
                    _add_spirit(trailer_car, gain)
            else:
                trailer_car.slipstream_accum_s = 0.0

        # 6. Termination checks: Stamina KO or Lap-Cap Fallback
        a_ko = car_a.stamina <= 0.0
        b_ko = car_b.stamina <= 0.0
        if a_ko or b_ko:
            if a_ko and not b_ko:
                winner_slot = "b"
                finish_reason = "stamina_ko"
            elif b_ko and not a_ko:
                winner_slot = "a"
                finish_reason = "stamina_ko"
            else:
                if abs(car_a.stamina - car_b.stamina) > 1e-6:
                    winner_slot = "a" if car_a.stamina > car_b.stamina else "b"
                elif abs(car_a.distance_m - car_b.distance_m) > 1e-6:
                    winner_slot = "a" if car_a.distance_m > car_b.distance_m else "b"
                else:
                    winner_slot = "b"
                finish_reason = "double_ko_fallback"
            break

        if max(car_a.distance_m, car_b.distance_m) >= max_distance_m:
            winner_slot, finish_reason = resolve_lap_cap_winner(
                car_a.stamina,
                car_a.stamina_max,
                car_b.stamina,
                car_b.stamina_max,
                car_a.distance_m,
                car_b.distance_m,
            )
            break

    winner_id = challenger.entrant_id if winner_slot == "a" else rival.entrant_id
    loser_id = rival.entrant_id if winner_slot == "a" else challenger.entrant_id
    a_rem = max(0.0, car_a.stamina)
    b_rem = max(0.0, car_b.stamina)

    return DuelResult(
        track_id=cfg.track_id,
        winner=winner_id,
        loser=loser_id,
        finish_reason=finish_reason,
        duration_s=round(elapsed_s, 4),
        ticks=ticks,
        laps_completed_leader=round(max(car_a.distance_m, car_b.distance_m) / cfg.loop_length_m, 4),
        final_gap_m=round(car_a.distance_m - car_b.distance_m, 3),
        challenger_stamina_remaining=round(a_rem, 2),
        challenger_stamina_max=round(car_a.stamina_max, 2),
        challenger_stamina_pct=round(a_rem / car_a.stamina_max, 4),
        rival_stamina_remaining=round(b_rem, 2),
        rival_stamina_max=round(car_b.stamina_max, 2),
        rival_stamina_pct=round(b_rem / car_b.stamina_max, 4),
        challenger_spirit_gained_total=round(car_a.spirit_gained_total, 2),
        challenger_spirit_end=round(car_a.spirit_meter, 2),
        challenger_specials_used=car_a.specials_used,
        rival_specials_used=car_b.specials_used,
        challenger_wall_hits=car_a.wall_hits,
        rival_wall_hits=car_b.wall_hits,
        contact_events=contact_events,
        overtakes=overtakes,
        challenger_maneuvers=dict(car_a.maneuvers),
        challenger_clean_race=(car_a.wall_hits == 0 and contact_events == 0),
    )


# ---------------------------------------------------------------------------
# Sweep & CSV Export Helpers
# ---------------------------------------------------------------------------
def build_entrant_with_loadout(
    entrant_id: str,
    car_id: str,
    mod_tier: int,
    driver_level: int = 3,
    skill_rating: float = 1.0,
    style: str = "balanced",
) -> DuelEntrant:
    """Create a DuelEntrant with a requested mod tier (0 = stock) and driver level."""
    roster = load_roster()
    catalog = load_mod_catalog()
    spec = roster[car_id]

    tech_xp = {b: 0 for b in TECHNIQUE_SUBBRANCHES}
    for branch, req_lvl in spec.tech_reqs.items():
        lvl = min(10, max(req_lvl, driver_level))
        tech_xp[branch] = TECHNIQUE_XP_THRESHOLDS[lvl]

    mastery_lvl_needed = {0: 0, 1: 0, 2: 2, 3: 4, 4: 7, 5: 9}[mod_tier]
    driver = DriverState(
        technique_xp=tech_xp,
        racing_spirit_xp={
            b: RACING_SPIRIT_XP_THRESHOLDS[min(10, driver_level)]
            for b in RACING_SPIRIT_SUBBRANCHES
        },
        stamina_xp=STAMINA_XP_THRESHOLDS[min(10, driver_level)],
    )
    car_state = CarState(
        car_id=car_id,
        xp=CAR_MASTERY_XP_THRESHOLDS[mastery_lvl_needed],
    )
    profile = PlayerProfile(
        driver=driver,
        credits=500_000,
        cars={car_id: car_state},
        active_car_id=car_id,
    )
    if mod_tier > 0:
        for mod_class in MOD_CLASSES:
            pid = f"t{mod_tier}_{mod_class}_{style}"
            buy_mod_part(profile, spec, pid, catalog=catalog, auto_equip=True)

    return DuelEntrant(
        entrant_id=entrant_id,
        profile=profile,
        car_spec=spec,
        skill_rating=skill_rating,
    )


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = (len(sorted_vals) - 1) * p
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def run_duel_sweep(
    seeds_per_scenario: int = 300,
    csv_dir: Path | None = None,
    track_ids: tuple[str, ...] = tuple(DUEL_TRACKS.keys()),
) -> dict[str, object]:
    """Run Monte Carlo sweep across all track profiles and scenarios; optionally write CSVs."""
    roster = load_roster()
    catalog = load_mod_catalog()

    scenarios = [
        ("t1_mirror_even", "t1_s13", 0, "t1_s13", 0, 1, 0),
        ("t1_mirror_plus1", "t1_s13", 1, "t1_s13", 0, 1, 1),
        ("t1_cross_s13_eg6", "t1_s13", 0, "t1_eg6", 0, 1, 0),
        ("t1_cross_s13_z31", "t1_s13", 0, "t1_z31", 0, 1, 0),
        ("t3_mirror_minus1", "t3_fd3s", 1, "t3_fd3s", 2, 4, -1),
        ("t3_mirror_even", "t3_fd3s", 2, "t3_fd3s", 2, 4, 0),
        ("t3_mirror_plus1", "t3_fd3s", 3, "t3_fd3s", 2, 4, 1),
        ("t3_cross_fd_evo", "t3_fd3s", 2, "t3_evo5", 2, 4, 0),
        ("t3_cross_fd_r33", "t3_fd3s", 2, "t3_r33", 2, 4, 0),
        ("t5_mirror_plus1", "t5_devil_s30", 5, "t5_devil_s30", 4, 8, 1),
        ("t5_cross_s30_pro", "t5_devil_s30", 4, "t5_proto_r", 4, 8, 0),
        ("t5_cross_s30_blk", "t5_devil_s30", 4, "t5_blackbird", 4, 8, 0),
    ]

    summary_rows: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []

    for tr_idx, track_id in enumerate(track_ids):
        cfg = DuelConfig.from_track(track_id)
        for sc_idx, (sc_id, car_a, tier_a, car_b, tier_b, dlvl, mod_gap) in enumerate(scenarios):
            ent_a = build_entrant_with_loadout("challenger", car_a, tier_a, driver_level=dlvl)
            ent_b = build_entrant_with_loadout("rival", car_b, tier_b, driver_level=dlvl)

            durations: list[float] = []
            wins_a = 0
            lap_caps = 0
            wall_hits_total = 0
            contacts_total = 0
            overtakes_total = 0

            for s in range(seeds_per_scenario):
                seed = tr_idx * 1_000_000 + sc_idx * 10_000 + s
                res = run_duel(ent_a, ent_b, seed=seed, config=cfg, catalog=catalog)
                durations.append(res.duration_s)
                if res.winner == "challenger":
                    wins_a += 1
                if res.finish_reason.startswith("lap_cap"):
                    lap_caps += 1
                wall_hits_total += res.challenger_wall_hits + res.rival_wall_hits
                contacts_total += res.contact_events
                overtakes_total += res.overtakes

                trace_rows.append(
                    {
                        "track_id": track_id,
                        "scenario": sc_id,
                        "seed": seed,
                        "loadout_tier_gap": mod_gap,
                        "winner": res.winner,
                        "finish_reason": res.finish_reason,
                        "duration_s": res.duration_s,
                        "laps_leader": res.laps_completed_leader,
                        "final_gap_m": res.final_gap_m,
                        "challenger_stamina_pct": res.challenger_stamina_pct,
                        "rival_stamina_pct": res.rival_stamina_pct,
                        "challenger_specials": res.challenger_specials_used,
                        "rival_specials": res.rival_specials_used,
                        "challenger_wall_hits": res.challenger_wall_hits,
                        "rival_wall_hits": res.rival_wall_hits,
                        "contacts": res.contact_events,
                        "overtakes": res.overtakes,
                    }
                )

            sorted_d = sorted(durations)
            in_window = sum(1 for d in durations if 60.0 <= d <= 180.0)
            summary_rows.append(
                {
                    "track_id": track_id,
                    "scenario": sc_id,
                    "challenger_car": car_a,
                    "challenger_mod_tier": tier_a,
                    "rival_car": car_b,
                    "rival_mod_tier": tier_b,
                    "loadout_tier_gap": mod_gap,
                    "seeds": seeds_per_scenario,
                    "challenger_win_rate": round(wins_a / seeds_per_scenario, 4),
                    "lap_cap_rate": round(lap_caps / seeds_per_scenario, 4),
                    "duration_mean_s": round(sum(durations) / len(durations), 2),
                    "duration_p10_s": round(_percentile(sorted_d, 0.10), 2),
                    "duration_p50_s": round(_percentile(sorted_d, 0.50), 2),
                    "duration_p90_s": round(_percentile(sorted_d, 0.90), 2),
                    "duration_min_s": round(sorted_d[0], 2),
                    "duration_max_s": round(sorted_d[-1], 2),
                    "in_1_to_3min_rate": round(in_window / seeds_per_scenario, 4),
                    "avg_wall_hits_both": round(wall_hits_total / seeds_per_scenario, 2),
                    "avg_contacts": round(contacts_total / seeds_per_scenario, 2),
                    "avg_overtakes": round(overtakes_total / seeds_per_scenario, 2),
                }
            )

    if csv_dir is not None:
        csv_dir.mkdir(parents=True, exist_ok=True)
        with (csv_dir / "duel_sweep_summary.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

        with (csv_dir / "duel_sweep_runs.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(trace_rows[0].keys()))
            writer.writeheader()
            writer.writerows(trace_rows)

    return {"summary": summary_rows, "runs": trace_rows, "roster_count": len(roster)}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run closed-loop Breakneck duel sweep across tracks and export CSVs."
    )
    parser.add_argument("--seeds", type=int, default=300, help="Seeds per track x scenario.")
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("sim_output"),
        help="Output directory for duel sweep CSVs.",
    )
    args = parser.parse_args()

    res = run_duel_sweep(seeds_per_scenario=args.seeds, csv_dir=args.csv_dir)
    print("Track    | Scenario           | Gap | WinRate | LapCap | Mean(s) | P50(s) | P10-P90(s)   | 1-3m")
    for row in res["summary"]:  # type: ignore[attr-defined]
        print(
            f"{row['track_id']:<8} | {row['scenario']:<18} | {row['loadout_tier_gap']:+3d} |  {row['challenger_win_rate']:.3f}  | "
            f" {row['lap_cap_rate']:.3f} |  {row['duration_mean_s']:5.1f}  | {row['duration_p50_s']:5.1f}  | "
            f"{row['duration_p10_s']:5.1f}-{row['duration_p90_s']:5.1f}  | {row['in_1_to_3min_rate']:.2f}"
        )


if __name__ == "__main__":
    main()
