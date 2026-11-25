"""Core progression rules, threshold graph evaluation, and Mastery-gated mod shop."""

from __future__ import annotations

from sim.constants import (
    BASE_RACE_CAR_XP,
    BASE_RACE_CREDITS_LOSS,
    BASE_RACE_CREDITS_WIN,
    BASE_RACE_DRIVER_XP,
    CAR_MASTERY_MAX_LEVEL,
    CAR_MASTERY_XP_THRESHOLDS,
    CLEAN_RACE_CREDITS_BONUS,
    CLEAN_RACE_XP_BONUS,
    LOSS_XP_MULTIPLIER,
    MASTERY_TO_MOD_CEILING,
    MASTERY_TO_SPECIAL_CEILING,
    MASTERY_TO_SPECIAL_FLOOR,
    MOD_CLASSES,
    POWER_PER_MASTERY_LEVEL,
    POWER_PER_SPECIAL_LEVEL,
    RACING_SPIRIT_GAIN_PER_LEVEL,
    RACING_SPIRIT_MANEUVER_BASE_GAIN,
    RACING_SPIRIT_MANEUVER_SUBBRANCH_MAP,
    RACING_SPIRIT_MAX_LEVEL,
    RACING_SPIRIT_METER_MAX,
    RACING_SPIRIT_PASSIVE_BUFFS,
    RACING_SPIRIT_SUBBRANCHES,
    RACING_SPIRIT_XP_THRESHOLDS,
    SPECIAL_PROGRESS_LOSS,
    SPECIAL_PROGRESS_WIN,
    STAMINA_BAR_BASE,
    STAMINA_BAR_PER_STAMINA_LEVEL,
    STAMINA_MAX_LEVEL,
    STAMINA_XP_THRESHOLDS,
    TECHNIQUE_MAX_LEVEL,
    TECHNIQUE_SUBBRANCHES,
    TECHNIQUE_TO_MASTERY_FLOOR,
    TECHNIQUE_XP_THRESHOLDS,
    TIER_CREDITS_STEP_LOSS,
    TIER_CREDITS_STEP_WIN,
    TIER_XP_STEP_CAR,
    TIER_XP_STEP_DRIVER,
    WIN_XP_MULTIPLIER,
)
from sim.models import (
    CarSpec,
    CarState,
    DriverState,
    ModPartSpec,
    PlayerProfile,
    RaceOutcome,
    load_mod_catalog,
    load_roster,
)


def level_from_xp(xp: int, thresholds: tuple[int, ...], max_level: int) -> int:
    """Convert cumulative XP into an integer level in [0, max_level]."""
    lvl = 0
    for idx, req in enumerate(thresholds):
        if xp >= req:
            lvl = idx
        else:
            break
    return min(lvl, max_level)


def lookup_threshold(value: int, table: tuple[tuple[int, int], ...]) -> int:
    """Evaluate a non-1:1 ordered threshold table [(min_in, out), ...]."""
    result = table[0][1]
    for min_in, out_val in table:
        if value >= min_in:
            result = out_val
        else:
            break
    return result


# ---------------------------------------------------------------------------
# Driver Stats & Derived Values
# ---------------------------------------------------------------------------
def technique_level(driver: DriverState, subbranch: str) -> int:
    xp = driver.technique_xp.get(subbranch, 0)
    return level_from_xp(xp, TECHNIQUE_XP_THRESHOLDS, TECHNIQUE_MAX_LEVEL)


def all_technique_levels(driver: DriverState) -> dict[str, int]:
    return {b: technique_level(driver, b) for b in TECHNIQUE_SUBBRANCHES}


def racing_spirit_level(driver: DriverState, subbranch: str) -> int:
    xp = driver.racing_spirit_xp.get(subbranch, 0)
    return level_from_xp(xp, RACING_SPIRIT_XP_THRESHOLDS, RACING_SPIRIT_MAX_LEVEL)


def all_racing_spirit_levels(driver: DriverState) -> dict[str, int]:
    return {b: racing_spirit_level(driver, b) for b in RACING_SPIRIT_SUBBRANCHES}


def stamina_level(driver: DriverState) -> int:
    """Driver's vertical Stamina stat (sizes the Stamina health bar)."""
    return level_from_xp(driver.stamina_xp, STAMINA_XP_THRESHOLDS, STAMINA_MAX_LEVEL)


def compute_stamina_bar_max(driver: DriverState) -> float:
    """Stamina health bar capacity depends exclusively on stamina_level."""
    return STAMINA_BAR_BASE + STAMINA_BAR_PER_STAMINA_LEVEL * stamina_level(driver)


def compute_racing_spirit_meter_gain(
    driver: DriverState, maneuvers: dict[str, int]
) -> float:
    """Compute Racing Spirit meter gain from race maneuvers (never touches the Stamina bar)."""
    total = 0.0
    for maneuver, count in maneuvers.items():
        if count <= 0:
            continue
        base = RACING_SPIRIT_MANEUVER_BASE_GAIN.get(maneuver, 0.0)
        branch = RACING_SPIRIT_MANEUVER_SUBBRANCH_MAP.get(maneuver)
        lvl = racing_spirit_level(driver, branch) if branch else 0
        mult = 1.0 + RACING_SPIRIT_GAIN_PER_LEVEL * lvl
        total += base * count * mult
    return min(total, RACING_SPIRIT_METER_MAX)


def compute_racing_spirit_passives(driver: DriverState) -> dict[str, float]:
    """Compute active passive buff totals from Racing Spirit subbranches."""
    passives: dict[str, float] = {}
    for branch, buffs in RACING_SPIRIT_PASSIVE_BUFFS.items():
        lvl = racing_spirit_level(driver, branch)
        for buff_key, per_level in buffs.items():
            passives[buff_key] = per_level * lvl
    return passives


# ---------------------------------------------------------------------------
# Threshold Prerequisite Graph & Mastery Floor Seeding
# ---------------------------------------------------------------------------
def can_unlock_car(driver: DriverState, car_spec: CarSpec) -> bool:
    """Check non-1:1 Technique category+level prerequisites for a car."""
    for subbranch, min_lvl in car_spec.tech_reqs.items():
        if technique_level(driver, subbranch) < min_lvl:
            return False
    return True


def unlocked_cars(
    driver: DriverState, roster: dict[str, CarSpec] | None = None
) -> list[CarSpec]:
    catalog = roster if roster is not None else load_roster()
    return [spec for spec in catalog.values() if can_unlock_car(driver, spec)]


def compute_mastery_floor(driver: DriverState, car_spec: CarSpec) -> int:
    """Seed a car's minimum Mastery from the driver's Technique proficiency."""
    primary_lvl = technique_level(driver, car_spec.primary_subbranch)
    return min(
        lookup_threshold(primary_lvl, TECHNIQUE_TO_MASTERY_FLOOR),
        CAR_MASTERY_MAX_LEVEL,
    )


def earned_car_mastery(car_state: CarState) -> int:
    return level_from_xp(
        car_state.xp, CAR_MASTERY_XP_THRESHOLDS, CAR_MASTERY_MAX_LEVEL
    )


def effective_car_mastery(
    driver: DriverState, car_spec: CarSpec, car_state: CarState
) -> int:
    """Car Mastery is always at least the Technique-seeded floor."""
    floor = compute_mastery_floor(driver, car_spec)
    earned = earned_car_mastery(car_state)
    return min(max(earned, floor), CAR_MASTERY_MAX_LEVEL)


def mod_tier_ceiling(mastery_level: int) -> int:
    """Highest shop shelf tier buyable/installable for this Mastery (hard ceiling)."""
    return lookup_threshold(mastery_level, MASTERY_TO_MOD_CEILING)


def special_level_bounds(mastery_level: int) -> tuple[int, int]:
    """Return (special_floor, special_ceiling) from non-1:1 Mastery thresholds."""
    floor = lookup_threshold(mastery_level, MASTERY_TO_SPECIAL_FLOOR)
    ceiling = lookup_threshold(mastery_level, MASTERY_TO_SPECIAL_CEILING)
    return floor, max(floor, ceiling)


def effective_special_levels(
    car_spec: CarSpec, car_state: CarState, mastery_level: int
) -> dict[str, int]:
    floor, ceiling = special_level_bounds(mastery_level)
    out: dict[str, int] = {}
    for sid in car_spec.special_ids:
        raw = car_state.special_levels.get(sid, 0)
        out[sid] = max(floor, min(raw, ceiling))
    return out


# ---------------------------------------------------------------------------
# Mastery-Gated Mod Shop (LOCKED 2026-11-25)
# - Owned parts are unique per car and swap freely with no refunds (no respec).
# - One equipped part per class; same-tier options are tradeoffs (sidegrades).
# - Single shared wallet earned from races.
# - Any unlocked tier <= Mastery ceiling can be bought directly (no lower-tier prereq).
# ---------------------------------------------------------------------------
def compute_race_credits(outcome: RaceOutcome) -> int:
    """Credits added to the shared wallet after a single race."""
    tier_offset = max(0, outcome.rival_tier - 1)
    if outcome.won:
        base = BASE_RACE_CREDITS_WIN + TIER_CREDITS_STEP_WIN * tier_offset
    else:
        base = BASE_RACE_CREDITS_LOSS + TIER_CREDITS_STEP_LOSS * tier_offset
    clean_mult = 1.0 + (CLEAN_RACE_CREDITS_BONUS if outcome.clean_race else 0.0)
    return round(base * clean_mult)


def buy_mod_part(
    profile: PlayerProfile,
    car_spec: CarSpec,
    part_id: str,
    catalog: dict[str, ModPartSpec] | None = None,
    auto_equip: bool = True,
) -> CarState:
    """Purchase a mod part from the shared wallet for this specific car.

    Requires car unlock, part.tier <= car's Mastery ceiling, part not already owned
    on this car, and sufficient credits. No lower-tier prerequisite.
    """
    mod_catalog = catalog if catalog is not None else load_mod_catalog()
    if part_id not in mod_catalog:
        raise ValueError(f"Unknown mod part {part_id!r}")
    if not can_unlock_car(profile.driver, car_spec):
        raise ValueError(
            f"Car {car_spec.car_id!r} does not meet Technique prerequisites"
        )

    part = mod_catalog[part_id]
    car_state = profile.get_or_create_car(car_spec)
    eff_mastery = effective_car_mastery(profile.driver, car_spec, car_state)
    ceiling = mod_tier_ceiling(eff_mastery)
    if part.tier > ceiling:
        raise ValueError(
            f"Part {part_id!r} (tier {part.tier}) exceeds Mastery shelf ceiling {ceiling}"
        )
    if part_id in car_state.owned_parts:
        raise ValueError(
            f"Part {part_id!r} is already owned on car {car_spec.car_id!r}"
        )
    if profile.credits < part.price:
        raise ValueError(
            f"Insufficient credits ({profile.credits} < {part.price}) for {part_id!r}"
        )

    profile.credits -= part.price
    car_state.owned_parts.add(part_id)
    if auto_equip:
        car_state.equipped_parts[part.mod_class] = part_id
    return car_state


def equip_mod_part(
    profile: PlayerProfile,
    car_spec: CarSpec,
    part_id: str,
    catalog: dict[str, ModPartSpec] | None = None,
) -> CarState:
    """Freely swap an already-owned part into its class slot on this car (no refund)."""
    mod_catalog = catalog if catalog is not None else load_mod_catalog()
    if part_id not in mod_catalog:
        raise ValueError(f"Unknown mod part {part_id!r}")
    car_state = profile.cars.get(car_spec.car_id)
    if car_state is None or part_id not in car_state.owned_parts:
        raise ValueError(
            f"Car {car_spec.car_id!r} does not own mod part {part_id!r}"
        )

    part = mod_catalog[part_id]
    eff_mastery = effective_car_mastery(profile.driver, car_spec, car_state)
    ceiling = mod_tier_ceiling(eff_mastery)
    if part.tier > ceiling:
        raise ValueError(
            f"Part {part_id!r} (tier {part.tier}) exceeds Mastery shelf ceiling {ceiling}"
        )

    car_state.equipped_parts[part.mod_class] = part_id
    return car_state


def unequip_mod_class(
    profile: PlayerProfile,
    car_spec: CarSpec,
    mod_class: str,
) -> CarState:
    """Clear the equipped part in `mod_class` back to stock (free, no refund)."""
    if mod_class not in MOD_CLASSES:
        raise ValueError(f"Unknown mod class {mod_class!r}")
    car_state = profile.get_or_create_car(car_spec)
    car_state.equipped_parts[mod_class] = None
    return car_state


def effective_car_stats(
    profile: PlayerProfile,
    car_spec: CarSpec,
    catalog: dict[str, ModPartSpec] | None = None,
) -> dict[str, float]:
    """Compute effective (top_speed, acceleration, handling, stat_average) with equipped mods."""
    mod_catalog = catalog if catalog is not None else load_mod_catalog()
    car_state = profile.cars.get(car_spec.car_id)
    ts = car_spec.top_speed
    ac = car_spec.acceleration
    hd = car_spec.handling

    if car_state is not None:
        mastery = effective_car_mastery(profile.driver, car_spec, car_state)
        ceiling = mod_tier_ceiling(mastery)
        for mod_class in MOD_CLASSES:
            part_id = car_state.equipped_parts.get(mod_class)
            if part_id is None:
                continue
            if part_id not in car_state.owned_parts:
                continue
            part = mod_catalog.get(part_id)
            if part is None or part.mod_class != mod_class or part.tier > ceiling:
                continue
            ts += part.top_speed_delta
            ac += part.acceleration_delta
            hd += part.handling_delta

    return {
        "top_speed": ts,
        "acceleration": ac,
        "handling": hd,
        "stat_average": (ts + ac + hd) / 3.0,
    }


# ---------------------------------------------------------------------------
# Effective Power & Race Application
# ---------------------------------------------------------------------------
def car_effective_power(
    profile: PlayerProfile,
    car_spec: CarSpec,
    catalog: dict[str, ModPartSpec] | None = None,
) -> float:
    car_state = profile.cars.get(car_spec.car_id) or CarState(
        car_id=car_spec.car_id,
        special_levels={sid: 0 for sid in car_spec.special_ids},
    )
    mastery = effective_car_mastery(profile.driver, car_spec, car_state)
    stats = effective_car_stats(profile, car_spec, catalog=catalog)
    specials = effective_special_levels(car_spec, car_state, mastery)

    avg_spec = sum(specials.values()) / len(specials) if specials else 0.0
    return (
        stats["stat_average"]
        + mastery * POWER_PER_MASTERY_LEVEL
        + avg_spec * POWER_PER_SPECIAL_LEVEL
    )


def _allocate_xp(
    buckets: dict[str, int],
    amount: int,
    target: str | None,
    valid_keys: tuple[str, ...],
) -> None:
    if amount <= 0:
        return
    if target is not None:
        if target not in valid_keys:
            raise ValueError(f"Invalid subbranch {target!r}")
        buckets[target] = buckets.get(target, 0) + amount
        return
    # Even split with deterministic remainder to first branches.
    base, rem = divmod(amount, len(valid_keys))
    for idx, key in enumerate(valid_keys):
        buckets[key] = buckets.get(key, 0) + base + (1 if idx < rem else 0)


def apply_race_result(
    profile: PlayerProfile,
    outcome: RaceOutcome,
    roster: dict[str, CarSpec] | None = None,
) -> dict[str, float | int | str]:
    """Apply XP, shared wallet credits, Mastery floor enforcement, and Specials for one race.

    Invariant: Car XP goes ONLY to the active car driven; mods do not auto-advance
    and must be purchased per car in the Mastery-gated shop.
    """
    catalog = roster if roster is not None else load_roster()

    car_spec = catalog[profile.active_car_id]
    if not can_unlock_car(profile.driver, car_spec):
        raise ValueError(
            f"Active car {car_spec.car_id!r} does not meet Technique prerequisites"
        )

    car_state = profile.get_or_create_car(car_spec)

    # 1. Compute Driver XP, Car XP (only for active car), and shared wallet Credits.
    outcome_mult = WIN_XP_MULTIPLIER if outcome.won else LOSS_XP_MULTIPLIER
    clean_bonus = CLEAN_RACE_XP_BONUS if outcome.clean_race else 0.0
    total_mult = outcome_mult + clean_bonus

    raw_driver_xp = BASE_RACE_DRIVER_XP + TIER_XP_STEP_DRIVER * max(
        0, outcome.rival_tier - 1
    )
    raw_car_xp = BASE_RACE_CAR_XP + TIER_XP_STEP_CAR * max(0, outcome.rival_tier - 1)

    driver_xp_gain = round(raw_driver_xp * total_mult)
    car_xp_gain = round(raw_car_xp * total_mult)
    credits_earned = compute_race_credits(outcome)
    profile.credits += credits_earned

    # 2. Racing Spirit meter gain in this race (separate from the Stamina health bar).
    racing_spirit_meter_gained = compute_racing_spirit_meter_gain(
        profile.driver, outcome.maneuvers
    )

    # 3. Allocate Driver XP across Technique / Racing Spirit branch / Stamina stat.
    share_sum = (
        outcome.technique_share
        + outcome.racing_spirit_share
        + outcome.stamina_share
    )
    if share_sum <= 0:
        raise ValueError("XP allocation shares must sum to > 0")
    tech_xp = round(driver_xp_gain * (outcome.technique_share / share_sum))
    racing_spirit_xp = round(
        driver_xp_gain * (outcome.racing_spirit_share / share_sum)
    )
    stamina_xp = driver_xp_gain - tech_xp - racing_spirit_xp

    tech_target = outcome.technique_target or car_spec.primary_subbranch
    _allocate_xp(
        profile.driver.technique_xp, tech_xp, tech_target, TECHNIQUE_SUBBRANCHES
    )
    _allocate_xp(
        profile.driver.racing_spirit_xp,
        racing_spirit_xp,
        outcome.racing_spirit_target,
        RACING_SPIRIT_SUBBRANCHES,
    )
    profile.driver.stamina_xp += stamina_xp
    profile.driver.total_races += 1
    if outcome.won:
        profile.driver.total_wins += 1

    # 4. Award Car XP ONLY to active car.
    car_state.xp += car_xp_gain
    car_state.races_driven += 1
    if outcome.won:
        car_state.wins += 1

    # 5. Recompute Mastery (respecting Technique floor) & advance Specials.
    # Mods never auto-advance; Mastery unlocks higher shop shelves for purchase.
    eff_mastery = effective_car_mastery(profile.driver, car_spec, car_state)
    mod_ceiling = mod_tier_ceiling(eff_mastery)

    special_floor, special_ceiling = special_level_bounds(eff_mastery)
    special_delta = SPECIAL_PROGRESS_WIN if outcome.won else SPECIAL_PROGRESS_LOSS
    for sid in car_spec.special_ids:
        cur = max(special_floor, car_state.special_levels.get(sid, 0))
        if cur < special_ceiling:
            prog = car_state.special_progress.get(sid, 0.0) + special_delta
            while prog >= 1.0 and cur < special_ceiling:
                cur += 1
                prog -= 1.0
            car_state.special_progress[sid] = prog if cur < special_ceiling else 0.0
        else:
            car_state.special_progress[sid] = 0.0
        car_state.special_levels[sid] = min(cur, special_ceiling)

    return {
        "driver_xp_gain": driver_xp_gain,
        "car_xp_gain": car_xp_gain,
        "credits_earned": credits_earned,
        "wallet_credits": profile.credits,
        "racing_spirit_meter_gained": racing_spirit_meter_gained,
        "effective_mastery": eff_mastery,
        "mod_ceiling": mod_ceiling,
        "stamina_bar_max": compute_stamina_bar_max(profile.driver),
    }
