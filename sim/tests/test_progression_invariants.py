"""Invariant tests for Breakneck progression, Mastery-gated mod shop & balance sim."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure draft-v0 root is importable regardless of cwd.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.constants import (
    CAR_ROSTER,
    MAX_MOD_TIER,
    MOD_CLASSES,
    MOD_TIER_FLOOR,
    RACING_SPIRIT_SUBBRANCHES,
    TECHNIQUE_SUBBRANCHES,
    TECHNIQUE_XP_THRESHOLDS,
)
from sim.export_constants import export_payload
from sim.models import (
    CarState,
    DriverState,
    PlayerProfile,
    RaceOutcome,
    load_mod_catalog,
    load_roster,
)
from sim.rules import (
    apply_race_result,
    buy_mod_part,
    can_unlock_car,
    car_effective_power,
    compute_mastery_floor,
    compute_racing_spirit_meter_gain,
    compute_racing_spirit_passives,
    compute_stamina_bar_max,
    effective_car_mastery,
    effective_car_stats,
    effective_special_levels,
    equip_mod_part,
    mod_tier_ceiling,
    special_level_bounds,
    unequip_mod_class,
)
from sim.simulate import run_simulation


def test_mastery_never_below_technique_floor() -> None:
    roster = load_roster()
    # Driver has Lv 6 chassis_craft, Lv 3 traction_line -> qualifies for t4_nsx.
    driver = DriverState(
        technique_xp={
            "chassis_craft": TECHNIQUE_XP_THRESHOLDS[6],
            "traction_line": TECHNIQUE_XP_THRESHOLDS[3],
            "aero_velocity": 0,
        }
    )
    nsx = roster["t4_nsx"]
    assert can_unlock_car(driver, nsx)

    fresh_nsx = CarState(car_id=nsx.car_id, xp=0)
    expected_floor = compute_mastery_floor(driver, nsx)
    assert expected_floor == 5
    assert effective_car_mastery(driver, nsx, fresh_nsx) >= expected_floor

    # Raising Technique later raises an already-owned car's effective Mastery floor too.
    driver.technique_xp["chassis_craft"] = TECHNIQUE_XP_THRESHOLDS[8]
    new_floor = compute_mastery_floor(driver, nsx)
    assert new_floor == 7
    assert effective_car_mastery(driver, nsx, fresh_nsx) == 7


def test_cannot_buy_or_install_above_mastery_shelf_and_direct_tier_buy() -> None:
    roster = load_roster()
    catalog = load_mod_catalog()
    profile = PlayerProfile(credits=100_000, active_car_id="t1_s13")
    s13 = roster["t1_s13"]
    car = profile.get_or_create_car(s13)

    # Mastery 0 -> shelf ceiling is 1; stock floor is 0.
    assert MOD_TIER_FLOOR == 0
    assert mod_tier_ceiling(effective_car_mastery(profile.driver, s13, car)) == 1

    # Can buy Tier 1, cannot buy Tier 2 above shelf.
    buy_mod_part(profile, s13, "t1_power_balanced", catalog=catalog)
    with pytest.raises(ValueError, match="exceeds Mastery shelf ceiling"):
        buy_mod_part(profile, s13, "t2_power_balanced", catalog=catalog)

    # Even if forced into owned_parts, cannot install above shelf.
    car.owned_parts.add("t2_aero_balanced")
    with pytest.raises(ValueError, match="exceeds Mastery shelf ceiling"):
        equip_mod_part(profile, s13, "t2_aero_balanced", catalog=catalog)

    # Raise Technique so t4_nsx unlocks with Mastery floor 5 -> mod shelf ceiling 3.
    # Rule 4: any unlocked tier can be bought directly with NO lower-tier prerequisite.
    profile.driver.technique_xp["chassis_craft"] = TECHNIQUE_XP_THRESHOLDS[6]
    profile.driver.technique_xp["traction_line"] = TECHNIQUE_XP_THRESHOLDS[3]
    nsx = roster["t4_nsx"]
    nsx_state = profile.get_or_create_car(nsx)
    assert mod_tier_ceiling(effective_car_mastery(profile.driver, nsx, nsx_state)) == 3

    buy_mod_part(profile, nsx, "t3_power_balanced", catalog=catalog)
    assert "t3_power_balanced" in nsx_state.owned_parts
    assert nsx_state.equipped_parts["power"] == "t3_power_balanced"
    # Never had to buy Tier 1 or Tier 2 first.
    assert "t1_power_balanced" not in nsx_state.owned_parts
    assert "t2_power_balanced" not in nsx_state.owned_parts

    # Tier 4 still blocked above shelf 3.
    with pytest.raises(ValueError, match="exceeds Mastery shelf ceiling"):
        buy_mod_part(profile, nsx, "t4_power_balanced", catalog=catalog)


def test_parts_stay_on_their_car_and_wallet_is_shared() -> None:
    roster = load_roster()
    catalog = load_mod_catalog()
    profile = PlayerProfile(active_car_id="t1_s13")
    s13 = roster["t1_s13"]
    eg6 = roster["t1_eg6"]
    profile.get_or_create_car(s13)
    profile.get_or_create_car(eg6)

    # Earn shared credits while driving t1_s13.
    for _ in range(3):
        apply_race_result(
            profile,
            RaceOutcome(won=True, rival_tier=1, maneuvers={"clean_drift": 1}),
            roster=roster,
        )
    earned_wallet = profile.credits
    assert earned_wallet > 0

    # Buy part on s13 using shared wallet; eg6 stays stock and owns nothing.
    p1 = catalog["t1_power_balanced"]
    buy_mod_part(profile, s13, p1.part_id, catalog=catalog)
    assert profile.credits == earned_wallet - p1.price
    assert p1.part_id in profile.cars["t1_s13"].owned_parts
    assert profile.cars["t1_eg6"].owned_parts == set()
    assert all(v is None for v in profile.cars["t1_eg6"].equipped_parts.values())

    # Cannot equip s13's owned part onto eg6.
    with pytest.raises(ValueError, match="does not own"):
        equip_mod_part(profile, eg6, p1.part_id, catalog=catalog)

    # Switch to eg6 and buy its own part from the SAME shared wallet.
    profile.active_car_id = "t1_eg6"
    p2 = catalog["t1_handling_handling"]
    buy_mod_part(profile, eg6, p2.part_id, catalog=catalog)
    assert profile.credits == earned_wallet - p1.price - p2.price
    assert p2.part_id in profile.cars["t1_eg6"].owned_parts
    assert p2.part_id not in profile.cars["t1_s13"].owned_parts


def test_swap_is_free_and_no_refund_and_one_equipped_per_class() -> None:
    roster = load_roster()
    catalog = load_mod_catalog()
    profile = PlayerProfile(credits=10_000, active_car_id="t1_s13")
    s13 = roster["t1_s13"]
    car = profile.get_or_create_car(s13)

    p_boost = catalog["t1_power_top_speed"]
    p_na = catalog["t1_power_handling"]

    buy_mod_part(profile, s13, p_boost.part_id, catalog=catalog)
    assert profile.credits == 10_000 - p_boost.price
    assert car.equipped_parts["power"] == p_boost.part_id

    # Buying a second part in the same class overwrites equipped (one per class) and gives no refund.
    buy_mod_part(profile, s13, p_na.part_id, catalog=catalog)
    expected_credits = 10_000 - p_boost.price - p_na.price
    assert profile.credits == expected_credits
    assert car.equipped_parts["power"] == p_na.part_id
    assert car.owned_parts == {p_boost.part_id, p_na.part_id}

    # Cannot buy an already-owned part again.
    with pytest.raises(ValueError, match="already owned"):
        buy_mod_part(profile, s13, p_boost.part_id, catalog=catalog)

    # Swapping back to p_boost is free and gives zero refund.
    equip_mod_part(profile, s13, p_boost.part_id, catalog=catalog)
    assert profile.credits == expected_credits
    assert car.equipped_parts["power"] == p_boost.part_id

    # Verify stats reflect ONLY the currently equipped part, not both owned parts.
    stats = effective_car_stats(profile, s13, catalog=catalog)
    assert stats["top_speed"] == pytest.approx(s13.top_speed + p_boost.top_speed_delta)
    assert stats["handling"] == pytest.approx(s13.handling + p_boost.handling_delta)

    # Unequipping back to stock is free and gives zero refund, while keeping ownership.
    unequip_mod_class(profile, s13, "power")
    assert profile.credits == expected_credits
    assert car.equipped_parts["power"] is None
    assert car.owned_parts == {p_boost.part_id, p_na.part_id}
    assert car_effective_power(profile, s13, catalog=catalog) == pytest.approx(
        s13.base_stat_average
    )


def test_same_tier_options_are_not_strictly_dominated() -> None:
    catalog = load_mod_catalog()
    for tier in range(1, MAX_MOD_TIER + 1):
        for mod_class in MOD_CLASSES:
            options = [
                p for p in catalog.values() if p.tier == tier and p.mod_class == mod_class
            ]
            assert len(options) >= 2, f"Expected multiple options for tier {tier} {mod_class}"
            for i, a in enumerate(options):
                for j, b in enumerate(options):
                    if i == j:
                        continue
                    a_ge_all = (
                        a.top_speed_delta >= b.top_speed_delta
                        and a.acceleration_delta >= b.acceleration_delta
                        and a.handling_delta >= b.handling_delta
                    )
                    a_gt_any = (
                        a.top_speed_delta > b.top_speed_delta
                        or a.acceleration_delta > b.acceleration_delta
                        or a.handling_delta > b.handling_delta
                    )
                    assert not (a_ge_all and a_gt_any), (
                        f"{a.part_id} strictly dominates {b.part_id}"
                    )

    # Higher tiers must cost more and give higher average stat gain per class.
    for mod_class in MOD_CLASSES:
        for tier in range(1, MAX_MOD_TIER):
            low = catalog[f"t{tier}_{mod_class}_balanced"]
            high = catalog[f"t{tier + 1}_{mod_class}_balanced"]
            assert high.price > low.price
            assert high.stat_average_delta > low.stat_average_delta


def test_xp_and_parts_go_only_to_driven_car() -> None:
    roster = load_roster()
    profile = PlayerProfile(active_car_id="t1_s13")
    for cid in ("t1_s13", "t1_eg6", "t1_z31"):
        profile.get_or_create_car(roster[cid])

    for _ in range(5):
        apply_race_result(
            profile,
            RaceOutcome(won=True, rival_tier=1, maneuvers={"clean_drift": 2}),
            roster=roster,
        )

    assert profile.cars["t1_s13"].xp > 0
    assert profile.cars["t1_s13"].races_driven == 5
    # Mods do not auto-advance on races driven.
    assert profile.cars["t1_s13"].owned_parts == set()
    for parked_id in ("t1_eg6", "t1_z31"):
        parked = profile.cars[parked_id]
        assert parked.xp == 0
        assert parked.races_driven == 0
        assert parked.owned_parts == set()
        assert all(v is None for v in parked.equipped_parts.values())


def test_special_levels_stay_within_mastery_bounds() -> None:
    roster = load_roster()
    driver = DriverState(
        technique_xp={
            "chassis_craft": TECHNIQUE_XP_THRESHOLDS[6],
            "traction_line": TECHNIQUE_XP_THRESHOLDS[3],
            "aero_velocity": 0,
        }
    )
    nsx = roster["t4_nsx"]
    car = CarState(car_id=nsx.car_id, xp=0)
    eff_m = effective_car_mastery(driver, nsx, car)
    special_floor, special_ceiling = special_level_bounds(eff_m)
    specials = effective_special_levels(nsx, car, eff_m)
    assert special_floor > 0
    for lvl in specials.values():
        assert special_floor <= lvl <= special_ceiling


def test_racing_spirit_meter_and_stamina_bar_are_decoupled() -> None:
    base_driver = DriverState()
    maneuvers = {"clean_drift": 2, "near_miss": 1, "clean_overtake": 1}

    base_stamina_bar = compute_stamina_bar_max(base_driver)
    base_meter = compute_racing_spirit_meter_gain(base_driver, maneuvers)

    # Raising stamina_level enlarges the Stamina health bar ONLY, never Racing Spirit meter gain.
    high_stamina = DriverState(stamina_xp=1500)
    assert compute_stamina_bar_max(high_stamina) > base_stamina_bar
    assert compute_racing_spirit_meter_gain(high_stamina, maneuvers) == pytest.approx(
        base_meter
    )

    # Raising Racing Spirit subbranches boosts meter gain & passives ONLY, never the Stamina bar.
    high_racing_spirit = DriverState(
        racing_spirit_xp={b: 1200 for b in RACING_SPIRIT_SUBBRANCHES}
    )
    assert compute_stamina_bar_max(high_racing_spirit) == pytest.approx(base_stamina_bar)
    assert compute_racing_spirit_meter_gain(high_racing_spirit, maneuvers) > base_meter
    passives = compute_racing_spirit_passives(high_racing_spirit)
    assert all(v > 0.0 for v in passives.values())


def test_roster_prerequisites_and_non_1_to_1_gating() -> None:
    assert 12 <= len(CAR_ROSTER) <= 18
    roster = load_roster()
    for spec in roster.values():
        assert spec.primary_subbranch in TECHNIQUE_SUBBRANCHES
        for branch, lvl in spec.tech_reqs.items():
            assert branch in TECHNIQUE_SUBBRANCHES
            assert lvl >= 1
        if spec.tier >= 3:
            # Non-1:1 multi-branch requirement for Tier 3+
            assert len(spec.tech_reqs) >= 2


def test_export_constants_and_sim_smoke(tmp_path: Path) -> None:
    payload = export_payload(include_parity_vectors=True)
    serialized = json.dumps(payload)
    parsed = json.loads(serialized)
    assert "constants" in parsed
    assert "parity_vectors" in parsed
    assert len(parsed["parity_vectors"]) >= 3

    # Export keys must not use retired identifiers or removed auto-advance mod keys.
    const_keys = set(parsed["constants"])
    retired = {k for k in const_keys if k.startswith("SP_") or k.startswith("SPIRIT_")}
    assert not retired
    for removed in ("MOD_PROGRESS_WIN", "MOD_PROGRESS_LOSS", "POWER_PER_MOD_TIER", "MOD_SLOTS", "DEFAULT_MOD_MODE"):
        assert removed not in const_keys

    for expected_key in (
        "MOD_CLASSES",
        "MOD_CATALOG",
        "BASE_RACE_CREDITS_WIN",
        "BASE_RACE_CREDITS_LOSS",
        "STAMINA_BAR_BASE",
        "RACING_SPIRIT_METER_MAX",
    ):
        assert expected_key in const_keys

    expected = parsed["parity_vectors"][0]["expected"]
    assert "stamina_bar_max" in expected
    assert "racing_spirit_meter_gain" in expected
    assert "effective_power_stock" in expected
    assert "effective_power_at_ceiling_balanced" in expected
    assert "sp_bar_max" not in expected
    assert "spirit_gain" not in expected

    res = run_simulation(max_races=80, win_rate=0.65, seed=42, csv_dir=tmp_path)
    assert res["unlocked_count"] == len(CAR_ROSTER)
    assert res["total_parts_bought"] > 0
    assert not any(m.grind_wall_flagged for m in res["milestones"])
    assert not any(e.grind_wall_flagged for e in res["shop_economy"])
    for slump in res["slump_results"]:
        assert slump.races_to_competitive <= slump.baseline_no_floor_races
    assert "final_stamina_bar_max" in res
