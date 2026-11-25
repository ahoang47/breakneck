"""Export sim/constants.py + parity vectors to JSON for Godot mirroring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sim import constants
from sim.duel import (
    compute_contact_drain,
    compute_gap_drain_rate,
    compute_wall_hit_drain,
    progress_gap,
    resolve_lap_cap_winner,
    wrapped_spline_delta,
)
from sim.models import CarState, DriverState, PlayerProfile, load_mod_catalog, load_roster
from sim.rules import (
    buy_mod_part,
    car_effective_power,
    compute_mastery_floor,
    compute_racing_spirit_meter_gain,
    compute_stamina_bar_max,
    effective_car_mastery,
    effective_car_stats,
    mod_tier_ceiling,
    special_level_bounds,
)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def build_parity_vectors() -> list[dict[str, Any]]:
    """Deterministic test vectors for Enzo's Godot parity suite."""
    roster = load_roster()
    mod_catalog = load_mod_catalog()
    vectors: list[dict[str, Any]] = []

    cases = [
        ("fresh_driver_t1", {"chassis_craft": 0, "traction_line": 0, "aero_velocity": 0}, {"drift_flow": 0, "slipstream_nerve": 0, "clean_line": 0}, 0, "t1_s13", 0),
        ("mid_driver_t4_seeded", {"chassis_craft": 1360, "traction_line": 640, "aero_velocity": 240}, {"drift_flow": 360, "slipstream_nerve": 210, "clean_line": 90}, 500, "t4_nsx", 0),
        ("apex_driver_t5_seeded", {"chassis_craft": 2200, "traction_line": 900, "aero_velocity": 900}, {"drift_flow": 750, "slipstream_nerve": 540, "clean_line": 360}, 1190, "t5_devil_s30", 190),
    ]

    maneuvers = {"clean_drift": 2, "near_miss": 1, "clean_overtake": 1}
    for label, tech_xp, racing_spirit_xp, stamina_xp, car_id, car_xp in cases:
        driver = DriverState(
            technique_xp=dict(tech_xp),
            racing_spirit_xp=dict(racing_spirit_xp),
            stamina_xp=stamina_xp,
        )
        spec = roster[car_id]
        car_state = CarState(car_id=car_id, xp=car_xp)
        profile = PlayerProfile(
            driver=driver,
            credits=50000,
            cars={car_id: car_state},
            active_car_id=car_id,
        )

        mastery_floor = compute_mastery_floor(driver, spec)
        eff_mastery = effective_car_mastery(driver, spec, car_state)
        ceiling = mod_tier_ceiling(eff_mastery)
        special_floor, special_ceiling = special_level_bounds(eff_mastery)
        stock_power = round(car_effective_power(profile, spec, catalog=mod_catalog), 4)

        # Also evaluate a full balanced loadout at the car's Mastery shelf ceiling.
        equipped_ids: dict[str, str] = {}
        for mod_class in constants.MOD_CLASSES:
            pid = f"t{ceiling}_{mod_class}_balanced"
            buy_mod_part(profile, spec, pid, catalog=mod_catalog, auto_equip=True)
            equipped_ids[mod_class] = pid
        modded_stats = effective_car_stats(profile, spec, catalog=mod_catalog)
        modded_power = round(car_effective_power(profile, spec, catalog=mod_catalog), 4)

        vectors.append(
            {
                "label": label,
                "inputs": {
                    "technique_xp": tech_xp,
                    "racing_spirit_xp": racing_spirit_xp,
                    "stamina_xp": stamina_xp,
                    "car_id": car_id,
                    "car_xp": car_xp,
                    "maneuvers": maneuvers,
                    "equipped_parts_at_ceiling": equipped_ids,
                },
                "expected": {
                    "mastery_floor": mastery_floor,
                    "effective_mastery": eff_mastery,
                    "mod_ceiling": ceiling,
                    "special_floor": special_floor,
                    "special_ceiling": special_ceiling,
                    "stamina_bar_max": round(compute_stamina_bar_max(driver), 4),
                    "racing_spirit_meter_gain": round(
                        compute_racing_spirit_meter_gain(driver, maneuvers), 4
                    ),
                    "effective_power_stock": stock_power,
                    "effective_power_at_ceiling_balanced": modded_power,
                    "effective_stats_at_ceiling_balanced": {
                        k: round(v, 4) for k, v in modded_stats.items()
                    },
                },
            }
        )
    return vectors




def build_duel_parity_vectors() -> list[dict[str, Any]]:
    """Deterministic closed-loop duel parity vectors across Street, Bayshore, and Ridge."""
    vectors: list[dict[str, Any]] = []

    # 1. Spline-gap seam wrapping & multi-lap progress across all three track lengths
    for track_id in ("street", "bayshore", "ridge"):
        tr = constants.DUEL_TRACKS[track_id]
        loop_len = float(tr["loop_length_m"])
        grace_s = float(tr["grace_period_s"])
        vectors.append(
            {
                "category": "track_spline_gap_and_grace",
                "label": f"{track_id}_seam_wrap_and_grace",
                "inputs": {
                    "track_id": track_id,
                    "laps_a": 1,
                    "offset_a": 22.5,
                    "laps_b": 0,
                    "offset_b": loop_len - 15.0,
                    "loop_length_m": loop_len,
                    "grace_period_s": grace_s,
                    "elapsed_during_grace_s": round(grace_s - 0.5, 4),
                    "elapsed_after_grace_s": round(grace_s + 5.0, 4),
                    "test_gap_m": 45.0,
                },
                "expected": {
                    "wrapped_spline_delta": round(
                        wrapped_spline_delta(22.5, loop_len - 15.0, loop_len), 4
                    ),
                    "progress_gap": round(
                        progress_gap(1, 22.5, 0, loop_len - 15.0, loop_len), 4
                    ),
                    "gap_drain_during_grace": round(
                        compute_gap_drain_rate(45.0, grace_s - 0.5, grace_period_s=grace_s), 4
                    ),
                    "gap_drain_after_grace": round(
                        compute_gap_drain_rate(45.0, grace_s + 5.0, grace_period_s=grace_s), 4
                    ),
                },
            }
        )

    # 2. Multi-lap lead + reverse seam wrap
    bay_len = float(constants.DUEL_TRACKS["bayshore"]["loop_length_m"])
    vectors.append(
        {
            "category": "spline_gap",
            "label": "bayshore_multi_lap_and_reverse_wrap",
            "inputs": {
                "laps_a": 2,
                "offset_a": 100.0,
                "laps_b": 1,
                "offset_b": bay_len - 100.0,
                "loop_length_m": bay_len,
            },
            "expected": {
                "wrapped_spline_delta": round(
                    wrapped_spline_delta(100.0, bay_len - 100.0, bay_len), 4
                ),
                "progress_gap": round(
                    progress_gap(2, 100.0, 1, bay_len - 100.0, bay_len), 4
                ),
            },
        }
    )

    # 3. Dead zone, cap, wall clamp + passive, and asymmetric contact clamp
    drain_cases = [
        ("dead_zone_zero", 7.5, 12.0, 10.0, 0.15, 8.0, True),
        ("mid_battle_clamp", 50.0, 25.0, 35.0, 0.0, 25.0, False),
        ("cap_and_side_contact", 300.0, 60.0, 8.0, 0.30, 8.0, None),
    ]
    street_grace = float(constants.DUEL_TRACKS["street"]["grace_period_s"])
    for label, gap_m, elapsed_s, wall_imp, wall_red, contact_imp, init_a in drain_cases:
        da, db = compute_contact_drain(contact_imp, init_a)
        vectors.append(
            {
                "category": "stamina_drain",
                "label": label,
                "inputs": {
                    "gap_m": gap_m,
                    "elapsed_s": elapsed_s,
                    "grace_period_s": street_grace,
                    "wall_impact_mps": wall_imp,
                    "wall_penalty_reduction": wall_red,
                    "contact_impact_mps": contact_imp,
                    "initiator_is_a": init_a,
                },
                "expected": {
                    "gap_drain_rate_per_s": round(
                        compute_gap_drain_rate(gap_m, elapsed_s, grace_period_s=street_grace), 4
                    ),
                    "wall_hit_drain": round(compute_wall_hit_drain(wall_imp, wall_red), 4),
                    "contact_drain_a": round(da, 4),
                    "contact_drain_b": round(db, 4),
                },
            }
        )

    # 4. Lap-cap fallback winner
    lap_cases = [
        ("stamina_pct_decides", 800.0, 1000.0, 1100.0, 1600.0, 25005.0, 25020.0),
        ("pct_tie_gap_decides", 900.0, 1000.0, 1440.0, 1600.0, 25012.0, 25005.0),
    ]
    for label, sa, samax, sb, sbmax, pa, pb in lap_cases:
        w, reason = resolve_lap_cap_winner(sa, samax, sb, sbmax, pa, pb)
        vectors.append(
            {
                "category": "lap_cap_fallback",
                "label": label,
                "inputs": {
                    "stamina_a": sa,
                    "stamina_a_max": samax,
                    "stamina_b": sb,
                    "stamina_b_max": sbmax,
                    "progress_a": pa,
                    "progress_b": pb,
                },
                "expected": {"winner_slot": w, "finish_reason": reason},
            }
        )

    return vectors

def export_payload(include_parity_vectors: bool = True) -> dict[str, Any]:
    exported_constants: dict[str, Any] = {}
    for name in sorted(dir(constants)):
        if name.startswith("_") or name == "Any":
            continue
        if name.isupper():
            exported_constants[name] = _to_jsonable(getattr(constants, name))

    payload: dict[str, Any] = {"constants": exported_constants}
    if include_parity_vectors:
        payload["parity_vectors"] = build_parity_vectors()
        payload["duel_parity_vectors"] = build_duel_parity_vectors()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export sim/constants.py and parity vectors as JSON."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output JSON path (prints to stdout when omitted).",
    )
    parser.add_argument(
        "--no-vectors",
        action="store_true",
        help="Omit parity test vectors and export only constants.",
    )
    args = parser.parse_args()

    text = json.dumps(
        export_payload(include_parity_vectors=not args.no_vectors),
        indent=2,
        sort_keys=True,
    )
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
