"""Playtest pacing, shop economy, and slump-check simulation for Breakneck."""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from pathlib import Path

from sim.constants import (
    BASE_RACE_CAR_XP,
    BASE_RACE_CREDITS_LOSS,
    BASE_RACE_CREDITS_WIN,
    CAR_MASTERY_MAX_LEVEL,
    CAR_MASTERY_XP_THRESHOLDS,
    CLEAN_RACE_CREDITS_BONUS,
    CLEAN_RACE_XP_BONUS,
    COMPETITIVE_POWER_RATIO,
    GRIND_WALL_RATIO,
    LOSS_XP_MULTIPLIER,
    MAX_MOD_TIER,
    MOD_CLASSES,
    POWER_PER_MASTERY_LEVEL,
    POWER_PER_SPECIAL_LEVEL,
    SPECIAL_PROGRESS_LOSS,
    SPECIAL_PROGRESS_WIN,
    TECHNIQUE_SUBBRANCHES,
    TECHNIQUE_XP_THRESHOLDS,
    TIER_CREDITS_STEP_LOSS,
    TIER_CREDITS_STEP_WIN,
    TIER_RIVAL_BENCHMARK_POWER,
    TIER_XP_STEP_CAR,
    WIN_XP_MULTIPLIER,
)
from sim.models import (
    CarSpec,
    CarState,
    ModPartSpec,
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
    compute_race_credits,
    compute_stamina_bar_max,
    effective_car_mastery,
    level_from_xp,
    mod_tier_ceiling,
    special_level_bounds,
    technique_level,
    unlocked_cars,
)


@dataclass
class SlumpEntry:
    car_id: str
    car_name: str
    tier: int
    unlocked_at_race: int
    seeded_mastery_floor: int
    mod_ceiling_at_unlock: int
    start_power: float
    target_power: float
    races_to_competitive: int
    baseline_no_floor_races: int


@dataclass
class TierMilestone:
    tier: int
    races_total: int
    delta_races: int
    delta_ratio_vs_prev: float | None
    grind_wall_flagged: bool
    first_car_id: str


@dataclass
class ShopEconomyEntry:
    tier: int
    full_kit_cost: int
    avg_part_cost: float
    expected_income_per_race: float
    races_for_full_kit: float
    races_per_part: float
    ratio_vs_prev: float | None
    grind_wall_flagged: bool


def _pick_next_tech_target(
    profile: PlayerProfile, roster: dict[str, CarSpec], highest_unlocked_tier: int
) -> str:
    """Advance toward the next unseen tier first, then fill lateral roster unlocks."""
    locked = [spec for spec in roster.values() if not can_unlock_car(profile.driver, spec)]
    if not locked:
        return roster[profile.active_car_id].primary_subbranch

    higher_locked = [spec for spec in locked if spec.tier > highest_unlocked_tier]
    if higher_locked:
        target_tier = min(spec.tier for spec in higher_locked)
        candidates = [spec for spec in higher_locked if spec.tier == target_tier]
    else:
        min_locked_tier = min(spec.tier for spec in locked)
        candidates = [spec for spec in locked if spec.tier == min_locked_tier]

    def car_xp_deficit(spec: CarSpec) -> tuple[int, str]:
        total_def = 0
        best_branch = spec.primary_subbranch
        best_branch_def = -1
        for branch, req_lvl in spec.tech_reqs.items():
            cur_xp = profile.driver.technique_xp.get(branch, 0)
            req_xp = TECHNIQUE_XP_THRESHOLDS[req_lvl]
            gap = max(0, req_xp - cur_xp)
            total_def += gap
            if gap > best_branch_def:
                best_branch_def = gap
                best_branch = branch
        return total_def, best_branch

    best_car = min(candidates, key=lambda s: car_xp_deficit(s)[0])
    _, target_branch = car_xp_deficit(best_car)
    return target_branch


def _buy_best_affordable_balanced(
    profile: PlayerProfile,
    car_spec: CarSpec,
    mod_catalog: dict[str, ModPartSpec],
) -> list[str]:
    """Simple shop AI: buy highest-unlocked-shelf balanced parts directly for active car.

    Prioritizes empty classes first, then upgrades lower-tier equipped classes
    directly to the car's current Mastery ceiling (skipping intermediate tiers).
    """
    car_state = profile.get_or_create_car(car_spec)
    ceiling = mod_tier_ceiling(effective_car_mastery(profile.driver, car_spec, car_state))
    purchased: list[str] = []

    while True:
        candidates: list[tuple[int, int, ModPartSpec]] = []
        for idx, mod_class in enumerate(MOD_CLASSES):
            eq_id = car_state.equipped_parts.get(mod_class)
            cur_tier = mod_catalog[eq_id].tier if (eq_id and eq_id in mod_catalog) else 0
            if cur_tier >= ceiling:
                continue
            target_part_id = f"t{ceiling}_{mod_class}_balanced"
            part = mod_catalog.get(target_part_id)
            if part is None or part.part_id in car_state.owned_parts:
                continue
            if profile.credits >= part.price:
                # Prefer empty slots (cur_tier == 0) before upgrading already-fitted slots.
                candidates.append((0 if cur_tier == 0 else 1, idx, part))
        if not candidates:
            break
        candidates.sort(key=lambda item: (item[0], item[2].price, item[1]))
        chosen = candidates[0][2]
        buy_mod_part(profile, car_spec, chosen.part_id, catalog=mod_catalog, auto_equip=True)
        purchased.append(chosen.part_id)

    return purchased


def _measure_no_floor_slump(
    spec: CarSpec,
    starting_credits: int,
    mod_catalog: dict[str, ModPartSpec],
    win_rate: float,
    seed: int,
    win_seq: list[bool] | None = None,
    clean_seq: list[bool] | None = None,
) -> int:
    """Counterfactual: how many races to competitive if Mastery floor were 0.

    Starts with the same entry wallet `starting_credits`, but Mastery starts at 0
    (shelf ceiling 1, special floor 0) and only grows via Car XP on this car.
    """
    rng = random.Random(seed)
    target_power = COMPETITIVE_POWER_RATIO * TIER_RIVAL_BENCHMARK_POWER[spec.tier]

    car_xp = 0
    credits = starting_credits
    owned: set[str] = set()
    equipped: dict[str, str | None] = {c: None for c in MOD_CLASSES}
    special_lvl = 0
    special_prog = 0.0

    def buy_no_floor(ceiling: int) -> None:
        nonlocal credits
        while True:
            candidates: list[tuple[int, int, ModPartSpec]] = []
            for idx, mod_class in enumerate(MOD_CLASSES):
                eq_id = equipped.get(mod_class)
                cur_tier = mod_catalog[eq_id].tier if eq_id else 0
                if cur_tier >= ceiling:
                    continue
                part = mod_catalog.get(f"t{ceiling}_{mod_class}_balanced")
                if part is None or part.part_id in owned:
                    continue
                if credits >= part.price:
                    candidates.append((0 if cur_tier == 0 else 1, idx, part))
            if not candidates:
                break
            candidates.sort(key=lambda item: (item[0], item[2].price, item[1]))
            chosen = candidates[0][2]
            credits -= chosen.price
            owned.add(chosen.part_id)
            equipped[chosen.mod_class] = chosen.part_id

    for races in range(0, 60):
        mastery = level_from_xp(car_xp, CAR_MASTERY_XP_THRESHOLDS, CAR_MASTERY_MAX_LEVEL)
        ceiling = mod_tier_ceiling(mastery)
        buy_no_floor(ceiling)

        ts, ac, hd = spec.top_speed, spec.acceleration, spec.handling
        for pid in equipped.values():
            if pid is not None:
                p = mod_catalog[pid]
                ts += p.top_speed_delta
                ac += p.acceleration_delta
                hd += p.handling_delta
        stat_avg = (ts + ac + hd) / 3.0
        power = (
            stat_avg
            + mastery * POWER_PER_MASTERY_LEVEL
            + special_lvl * POWER_PER_SPECIAL_LEVEL
        )
        if power >= target_power:
            return races

        won = win_seq[races] if (win_seq is not None and races < len(win_seq)) else (rng.random() < win_rate)
        clean = clean_seq[races] if (clean_seq is not None and races < len(clean_seq)) else (rng.random() < 0.80)
        mult = (WIN_XP_MULTIPLIER if won else LOSS_XP_MULTIPLIER) + (
            CLEAN_RACE_XP_BONUS if clean else 0.0
        )
        car_xp += round((BASE_RACE_CAR_XP + TIER_XP_STEP_CAR * (spec.tier - 1)) * mult)
        credits += compute_race_credits(
            RaceOutcome(won=won, rival_tier=spec.tier, clean_race=clean)
        )
        new_mastery = level_from_xp(car_xp, CAR_MASTERY_XP_THRESHOLDS, CAR_MASTERY_MAX_LEVEL)
        special_floor, special_ceiling = special_level_bounds(new_mastery)
        special_lvl = max(special_lvl, special_floor)
        if special_lvl < special_ceiling:
            special_prog += SPECIAL_PROGRESS_WIN if won else SPECIAL_PROGRESS_LOSS
            while special_prog >= 1.0 and special_lvl < special_ceiling:
                special_lvl += 1
                special_prog -= 1.0
            if special_lvl >= special_ceiling:
                special_prog = 0.0
        else:
            special_prog = 0.0
    return 60


def compute_shop_economy(
    mod_catalog: dict[str, ModPartSpec],
    win_rate: float,
    clean_rate: float = 0.80,
) -> list[ShopEconomyEntry]:
    """Evaluate races of income needed per tier and flag any shop grind wall."""
    entries: list[ShopEconomyEntry] = []
    prev_races: float | None = None
    for tier in range(1, MAX_MOD_TIER + 1):
        balanced_parts = [
            mod_catalog[f"t{tier}_{mod_class}_balanced"] for mod_class in MOD_CLASSES
        ]
        full_kit_cost = sum(p.price for p in balanced_parts)
        avg_part_cost = full_kit_cost / len(MOD_CLASSES)

        win_payout = BASE_RACE_CREDITS_WIN + TIER_CREDITS_STEP_WIN * (tier - 1)
        loss_payout = BASE_RACE_CREDITS_LOSS + TIER_CREDITS_STEP_LOSS * (tier - 1)
        expected_base = win_rate * win_payout + (1.0 - win_rate) * loss_payout
        expected_income = expected_base * (1.0 + clean_rate * CLEAN_RACE_CREDITS_BONUS)

        races_full = full_kit_cost / expected_income
        races_part = avg_part_cost / expected_income
        ratio = (races_full / prev_races) if (prev_races is not None and prev_races > 0) else None
        flagged = ratio is not None and ratio > GRIND_WALL_RATIO

        entries.append(
            ShopEconomyEntry(
                tier=tier,
                full_kit_cost=full_kit_cost,
                avg_part_cost=avg_part_cost,
                expected_income_per_race=expected_income,
                races_for_full_kit=races_full,
                races_per_part=races_part,
                ratio_vs_prev=ratio,
                grind_wall_flagged=flagged,
            )
        )
        prev_races = races_full
    return entries


def run_simulation(
    max_races: int = 80,
    win_rate: float = 0.65,
    seed: int = 42,
    csv_dir: Path | None = None,
) -> dict[str, object]:
    rng = random.Random(seed)
    roster = load_roster()
    mod_catalog = load_mod_catalog()
    profile = PlayerProfile(active_car_id="t1_s13")
    profile.get_or_create_car(roster["t1_s13"])

    tier_first_unlock: dict[int, tuple[int, str]] = {1: (0, "t1_s13")}
    seen_unlocked: set[str] = {s.car_id for s in unlocked_cars(profile.driver, roster)}
    full_roster_race: int | None = (
        0 if len(seen_unlocked) == len(roster) else None
    )

    pending_slump: dict[str, dict[str, object]] = {}
    slump_results: dict[str, SlumpEntry] = {}
    trace_rows: list[dict[str, object]] = []
    total_parts_bought = 0

    for race_num in range(1, max_races + 1):
        active_spec = roster[profile.active_car_id]
        tech_target = _pick_next_tech_target(profile, roster, max(tier_first_unlock.keys()))
        won = rng.random() < win_rate
        clean_race = rng.random() < 0.80
        maneuvers = {
            "clean_drift": 2 if active_spec.primary_subbranch == "chassis_craft" else 1,
            "slipstream_tick": 2 if active_spec.primary_subbranch == "aero_velocity" else 1,
            "near_miss": 1,
            "clean_overtake": 1 if won else 0,
        }

        res = apply_race_result(
            profile,
            RaceOutcome(
                won=won,
                rival_tier=active_spec.tier,
                clean_race=clean_race,
                maneuvers=maneuvers,
                technique_target=tech_target,
            ),
            roster=roster,
        )

        # Shop visit after race on current active car.
        bought_now = _buy_best_affordable_balanced(profile, active_spec, mod_catalog)
        total_parts_bought += len(bought_now)

        # Update slump tracking for the currently driven newly-unlocked car.
        if active_spec.car_id in pending_slump and active_spec.car_id not in slump_results:
            info = pending_slump[active_spec.car_id]
            info["races_on_car"] = int(info["races_on_car"]) + 1
            info["win_seq"].append(won)
            info["clean_seq"].append(clean_race)
            cur_power = car_effective_power(profile, active_spec, catalog=mod_catalog)
            target_power = float(info["target_power"])
            if cur_power >= target_power:
                slump_results[active_spec.car_id] = SlumpEntry(
                    car_id=active_spec.car_id,
                    car_name=active_spec.name,
                    tier=active_spec.tier,
                    unlocked_at_race=int(info["unlocked_at_race"]),
                    seeded_mastery_floor=int(info["seeded_mastery_floor"]),
                    mod_ceiling_at_unlock=int(info["mod_ceiling_at_unlock"]),
                    start_power=float(info["start_power"]),
                    target_power=target_power,
                    races_to_competitive=int(info["races_on_car"]),
                    baseline_no_floor_races=_measure_no_floor_slump(
                        active_spec,
                        int(info["entry_credits"]),
                        mod_catalog,
                        win_rate,
                        seed + active_spec.tier,
                        list(info["win_seq"]),
                        list(info["clean_seq"]),
                    ),
                )

        # Check newly unlocked cars.
        now_unlocked = unlocked_cars(profile.driver, roster)
        newly_unlocked = [
            spec for spec in now_unlocked if spec.car_id not in seen_unlocked
        ]
        for spec in newly_unlocked:
            seen_unlocked.add(spec.car_id)
            if spec.tier not in tier_first_unlock:
                tier_first_unlock[spec.tier] = (race_num, spec.car_id)

        if full_roster_race is None and len(seen_unlocked) == len(roster):
            full_roster_race = race_num

        # Player switches to highest newly unlocked tier car when available, then shops.
        higher_unlocked = [
            spec for spec in newly_unlocked if spec.tier > active_spec.tier
        ]
        if higher_unlocked:
            chosen = max(higher_unlocked, key=lambda s: (s.tier, s.base_stat_average))
            entry_credits = profile.credits
            profile.active_car_id = chosen.car_id
            car_st = profile.get_or_create_car(chosen)
            seeded_floor = compute_mastery_floor(profile.driver, chosen)
            eff_m = effective_car_mastery(profile.driver, chosen, car_st)
            bought_on_switch = _buy_best_affordable_balanced(profile, chosen, mod_catalog)
            total_parts_bought += len(bought_on_switch)

            start_pow = car_effective_power(profile, chosen, catalog=mod_catalog)
            target_pow = COMPETITIVE_POWER_RATIO * TIER_RIVAL_BENCHMARK_POWER[chosen.tier]
            if start_pow >= target_pow:
                slump_results[chosen.car_id] = SlumpEntry(
                    car_id=chosen.car_id,
                    car_name=chosen.name,
                    tier=chosen.tier,
                    unlocked_at_race=race_num,
                    seeded_mastery_floor=seeded_floor,
                    mod_ceiling_at_unlock=mod_tier_ceiling(eff_m),
                    start_power=start_pow,
                    target_power=target_pow,
                    races_to_competitive=0,
                    baseline_no_floor_races=_measure_no_floor_slump(
                        chosen, entry_credits, mod_catalog, win_rate, seed + chosen.tier
                    ),
                )
            else:
                pending_slump[chosen.car_id] = {
                    "unlocked_at_race": race_num,
                    "seeded_mastery_floor": seeded_floor,
                    "mod_ceiling_at_unlock": mod_tier_ceiling(eff_m),
                    "start_power": start_pow,
                    "target_power": target_pow,
                    "races_on_car": 0,
                    "win_seq": [],
                    "clean_seq": [],
                    "entry_credits": entry_credits,
                }

        cur_spec = roster[profile.active_car_id]
        cur_state = profile.cars[cur_spec.car_id]
        eq_summary = "|".join(
            f"{c}:{cur_state.equipped_parts.get(c) or 'stock'}" for c in MOD_CLASSES
        )
        trace_rows.append(
            {
                "race": race_num,
                "won": int(won),
                "active_car": profile.active_car_id,
                "active_tier": cur_spec.tier,
                "credits_earned": res["credits_earned"],
                "wallet_credits": profile.credits,
                "owned_parts_on_car": len(cur_state.owned_parts),
                "equipped_parts": eq_summary,
                "tech_levels": "|".join(
                    f"{b}:{technique_level(profile.driver, b)}"
                    for b in TECHNIQUE_SUBBRANCHES
                ),
                "unlocked_count": len(seen_unlocked),
                "effective_mastery": res["effective_mastery"],
                "mod_ceiling": res["mod_ceiling"],
                "stamina_bar_max": round(float(res["stamina_bar_max"]), 1),
                "racing_spirit_meter_gained": round(float(res["racing_spirit_meter_gained"]), 1),
                "car_power": round(car_effective_power(profile, cur_spec, catalog=mod_catalog), 2),
            }
        )

    # Build tier milestones & grind-wall checks.
    milestones: list[TierMilestone] = []
    prev_races = 0
    prev_delta: int | None = None
    for tier in sorted(TIER_RIVAL_BENCHMARK_POWER.keys()):
        if tier in tier_first_unlock:
            total_r, cid = tier_first_unlock[tier]
            delta = total_r - prev_races
            ratio = (
                (delta / prev_delta)
                if (prev_delta is not None and prev_delta > 0)
                else None
            )
            flagged = ratio is not None and ratio > GRIND_WALL_RATIO
            milestones.append(
                TierMilestone(
                    tier=tier,
                    races_total=total_r,
                    delta_races=delta,
                    delta_ratio_vs_prev=ratio,
                    grind_wall_flagged=flagged,
                    first_car_id=cid,
                )
            )
            prev_races = total_r
            if tier >= 2:
                prev_delta = delta

    shop_economy = compute_shop_economy(mod_catalog, win_rate=win_rate, clean_rate=0.80)

    if csv_dir is not None:
        csv_dir.mkdir(parents=True, exist_ok=True)
        with (csv_dir / "tier_pacing.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "tier",
                    "races_total",
                    "delta_races",
                    "delta_ratio_vs_prev",
                    "grind_wall_flagged",
                    "first_car_id",
                ]
            )
            for m in milestones:
                w.writerow(
                    [
                        m.tier,
                        m.races_total,
                        m.delta_races,
                        f"{m.delta_ratio_vs_prev:.2f}" if m.delta_ratio_vs_prev is not None else "",
                        int(m.grind_wall_flagged),
                        m.first_car_id,
                    ]
                )

        with (csv_dir / "shop_economy.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "tier",
                    "full_kit_cost",
                    "avg_part_cost",
                    "expected_income_per_race",
                    "races_for_full_kit",
                    "races_per_part",
                    "ratio_vs_prev",
                    "grind_wall_flagged",
                ]
            )
            for e in shop_economy:
                w.writerow(
                    [
                        e.tier,
                        e.full_kit_cost,
                        f"{e.avg_part_cost:.1f}",
                        f"{e.expected_income_per_race:.1f}",
                        f"{e.races_for_full_kit:.2f}",
                        f"{e.races_per_part:.2f}",
                        f"{e.ratio_vs_prev:.2f}" if e.ratio_vs_prev is not None else "",
                        int(e.grind_wall_flagged),
                    ]
                )

        with (csv_dir / "slump_check.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "car_id",
                    "car_name",
                    "tier",
                    "unlocked_at_race",
                    "seeded_mastery_floor",
                    "mod_ceiling_at_unlock",
                    "start_power",
                    "target_power",
                    "races_to_competitive",
                    "baseline_no_floor_races",
                ]
            )
            for s in sorted(slump_results.values(), key=lambda x: x.tier):
                w.writerow(
                    [
                        s.car_id,
                        s.car_name,
                        s.tier,
                        s.unlocked_at_race,
                        s.seeded_mastery_floor,
                        s.mod_ceiling_at_unlock,
                        f"{s.start_power:.2f}",
                        f"{s.target_power:.2f}",
                        s.races_to_competitive,
                        s.baseline_no_floor_races,
                    ]
                )

        with (csv_dir / "race_trace.csv").open("w", newline="", encoding="utf-8") as f:
            fieldnames = list(trace_rows[0].keys()) if trace_rows else []
            dw = csv.DictWriter(f, fieldnames=fieldnames)
            dw.writeheader()
            dw.writerows(trace_rows)

    return {
        "max_races": max_races,
        "win_rate": win_rate,
        "milestones": milestones,
        "shop_economy": shop_economy,
        "slump_results": sorted(slump_results.values(), key=lambda x: x.tier),
        "full_roster_race": full_roster_race,
        "unlocked_count": len(seen_unlocked),
        "roster_size": len(roster),
        "final_credits": profile.credits,
        "total_parts_bought": total_parts_bought,
        "final_stamina_bar_max": compute_stamina_bar_max(profile.driver),
        "final_tech_levels": {
            b: technique_level(profile.driver, b) for b in TECHNIQUE_SUBBRANCHES
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Breakneck progression simulation.")
    parser.add_argument("--races", type=int, default=80, help="Number of races to simulate.")
    parser.add_argument("--win-rate", type=float, default=0.65, help="Assumed win probability.")
    parser.add_argument("--seed", type=int, default=42, help="PRNG seed.")
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("sim_output"),
        help="Directory to write CSV outputs.",
    )
    args = parser.parse_args()

    res = run_simulation(
        max_races=args.races,
        win_rate=args.win_rate,
        seed=args.seed,
        csv_dir=args.csv_dir,
    )

    print(
        f"Breakneck Progression Sim (races={res['max_races']}, "
        f"win_rate={res['win_rate']:.0%}, mods=per-car Mastery-gated shop)"
    )
    print("\n== Technique Tier Pacing & Grind-Wall Check ==")
    print("Tier | Races | Delta | Ratio vs Prev | Grind Wall | First Car")
    for m in res["milestones"]:  # type: ignore[attr-defined]
        ratio_str = f"{m.delta_ratio_vs_prev:.2f}x" if m.delta_ratio_vs_prev is not None else "  -  "
        flag_str = "YES (>2x)" if m.grind_wall_flagged else "no"
        print(
            f"  {m.tier}  |  {m.races_total:3d}  |  {m.delta_races:3d}  |     {ratio_str}     |    {flag_str:<9} | {m.first_car_id}"
        )

    print("\n== Shop Economy & Income Grind-Wall Check ==")
    print("Tier | FullKit | Income/Race | Races/Kit | Races/Part | Ratio vs Prev | Grind Wall")
    for e in res["shop_economy"]:  # type: ignore[attr-defined]
        ratio_str = f"{e.ratio_vs_prev:.2f}x" if e.ratio_vs_prev is not None else "  -  "
        flag_str = "YES (>2x)" if e.grind_wall_flagged else "no"
        print(
            f"  {e.tier}  | {e.full_kit_cost:7d} |   {e.expected_income_per_race:7.1f}   |   {e.races_for_full_kit:5.2f}   |   {e.races_per_part:5.2f}    |     {ratio_str}     | {flag_str}"
        )

    print("\n== New-Car Slump Check (Newly Unlocked Cars, Purchased Loadouts) ==")
    print("Tier | Car          | Unlock Race | Floor | ModCeil | Start->Target | RacesToComp | NoFloorBaseline")
    for s in res["slump_results"]:  # type: ignore[attr-defined]
        print(
            f"  {s.tier}  | {s.car_id:<12} |     {s.unlocked_at_race:3d}     |   {s.seeded_mastery_floor:2d}  |    {s.mod_ceiling_at_unlock}    | "
            f"{s.start_power:5.1f}->{s.target_power:5.1f} |     {s.races_to_competitive:2d}      |       {s.baseline_no_floor_races:2d}"
        )

    print("\n== Roster & Final Driver Summary ==")
    print(
        f"Full roster ({res['unlocked_count']}/{res['roster_size']} cars) unlocked at race: "
        f"{res['full_roster_race']}"
    )
    print(f"Total mod parts bought: {res['total_parts_bought']}, Final wallet credits: {res['final_credits']}")
    print(f"Final Technique levels: {res['final_tech_levels']}")
    print(f"Final Stamina Bar Max: {res['final_stamina_bar_max']:.0f}")
    print(f"CSVs written to: {args.csv_dir}")


if __name__ == "__main__":
    main()
