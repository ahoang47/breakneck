"""Tests for Breakneck closed-loop duel rules, spline-gap math, and tick sim."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.constants import (
    DUEL_CONTACT_DEFENDER_SHARE,
    DUEL_CONTACT_DRAIN_MAX,
    DUEL_CONTACT_EQUAL_SHARE,
    DUEL_CONTACT_INITIATOR_SHARE,
    DUEL_CONTACT_MIN_IMPACT_MPS,
    DUEL_GAP_DEAD_ZONE_M,
    DUEL_GAP_DRAIN_CAP_PER_S,
    DUEL_DEFAULT_TRACK_ID,
    DUEL_TRACKS,
    DUEL_WALL_DRAIN_MAX,
    DUEL_WALL_MIN_IMPACT_MPS,
)
from sim.duel import (
    DuelConfig,
    build_entrant_with_loadout,
    compute_contact_drain,
    compute_gap_drain_rate,
    compute_wall_hit_drain,
    progress_gap,
    resolve_lap_cap_winner,
    run_duel,
    run_duel_sweep,
    wrapped_spline_delta,
)
from sim.export_constants import export_payload


def test_duel_always_terminates_and_is_deterministic() -> None:
    a = build_entrant_with_loadout("challenger", "t3_fd3s", mod_tier=2, driver_level=10)
    b = build_entrant_with_loadout("rival", "t3_evo5", mod_tier=2, driver_level=10)

    for seed in range(25):
        res = run_duel(a, b, seed=seed)
        assert res.ticks > 0
        assert res.duration_s > 0.0
        assert res.winner in ("challenger", "rival")
        assert res.loser != res.winner
        assert res.finish_reason in (
            "stamina_ko",
            "lap_cap_stamina_pct",
            "lap_cap_gap",
            "lap_cap_defender_tie",
            "double_ko_fallback",
        )

    r1 = run_duel(a, b, seed=1234)
    r2 = run_duel(a, b, seed=1234)
    assert r1 == r2


def test_trailing_car_drains_and_leader_does_not_from_gap() -> None:
    # Rule-level checks
    grace = DUEL_TRACKS[DUEL_DEFAULT_TRACK_ID]["grace_period_s"]
    assert compute_gap_drain_rate(100.0, grace - 0.1, grace_period_s=grace) == 0.0
    assert compute_gap_drain_rate(DUEL_GAP_DEAD_ZONE_M, 20.0) == 0.0
    assert compute_gap_drain_rate(DUEL_GAP_DEAD_ZONE_M + 20.0, 20.0) > 0.0
    assert compute_gap_drain_rate(10_000.0, 20.0) == pytest.approx(DUEL_GAP_DRAIN_CAP_PER_S)

    # Integration check: dominant T5 challenger blows past T1 stock rival cleanly.
    # Even if challenger uses Specials, Stamina is untouched when leading cleanly.
    t5 = build_entrant_with_loadout("challenger", "t5_devil_s30", mod_tier=5, driver_level=8)
    t1 = build_entrant_with_loadout("rival", "t1_eg6", mod_tier=0, driver_level=1)

    clean_seed = None
    for s in range(50):
        res = run_duel(t5, t1, seed=s)
        if res.challenger_wall_hits == 0 and res.contact_events == 0 and res.challenger_specials_used >= 1:
            clean_seed = res
            break

    assert clean_seed is not None, "Expected at least one clean T5 vs T1 blow-by seed"
    assert clean_seed.winner == "challenger"
    assert clean_seed.finish_reason == "stamina_ko"
    assert clean_seed.rival_stamina_remaining == 0.0
    # Challenger started 12m behind (within grace period, so 0 gap drain) then led cleanly;
    # firing Specials spent Racing Spirit only, leaving Stamina at 100%.
    assert clean_seed.challenger_stamina_remaining == pytest.approx(clean_seed.challenger_stamina_max)


def test_spline_gap_wraps_correctly_across_lap_line() -> None:
    L = 5000.0
    # Leader A at 22.5 m (lap 1), Trailer B at 4985.0 m (lap 0) -> A leads by +37.5 m
    assert wrapped_spline_delta(22.5, 4985.0, L) == pytest.approx(37.5)
    assert progress_gap(1, 22.5, 0, 4985.0, L) == pytest.approx(37.5)

    # Reverse perspective: B trails A by -37.5 m across the seam
    assert wrapped_spline_delta(4985.0, 22.5, L) == pytest.approx(-37.5)
    assert progress_gap(0, 4985.0, 1, 22.5, L) == pytest.approx(-37.5)

    # Exact seam boundary
    assert wrapped_spline_delta(0.0, 4999.0, L) == pytest.approx(1.0)
    assert wrapped_spline_delta(4999.0, 0.0, L) == pytest.approx(-1.0)

    # Multi-lap lead (> L/2) tracked via lap counts
    assert progress_gap(2, 100.0, 1, 4900.0, L) == pytest.approx(200.0)


def test_lap_cap_fallback_picks_right_winner() -> None:
    # Higher Stamina % wins even with smaller absolute bar & slightly behind
    w, reason = resolve_lap_cap_winner(
        stamina_a=800.0,
        stamina_a_max=1000.0,  # 80%
        stamina_b=1100.0,
        stamina_b_max=1600.0,  # 68.75%
        progress_a=25005.0,
        progress_b=25020.0,
    )
    assert w == "a"
    assert reason == "lap_cap_stamina_pct"

    # Tied Stamina % falls back to track gap
    w, reason = resolve_lap_cap_winner(
        stamina_a=900.0,
        stamina_a_max=1000.0,  # 90%
        stamina_b=1440.0,
        stamina_b_max=1600.0,  # 90%
        progress_a=25012.0,
        progress_b=25005.0,
    )
    assert w == "a"
    assert reason == "lap_cap_gap"

    # Tied Stamina % and tied progress -> defender ("b") retains
    w, reason = resolve_lap_cap_winner(1000.0, 1000.0, 1000.0, 1000.0, 25000.0, 25000.0)
    assert w == "b"
    assert reason == "lap_cap_defender_tie"

    # Force a short 1-lap cap in run_duel where neither bar can empty in time
    a = build_entrant_with_loadout("challenger", "t3_fd3s", mod_tier=2, driver_level=5)
    b = build_entrant_with_loadout("rival", "t3_fd3s", mod_tier=2, driver_level=5)
    short_cfg = DuelConfig(loop_length_m=1500.0, max_laps=1)
    res = run_duel(a, b, seed=7, config=short_cfg)
    assert res.finish_reason.startswith("lap_cap")


def test_better_loadout_raises_win_rate_over_many_seeds() -> None:
    rival = build_entrant_with_loadout("rival", "t3_fd3s", mod_tier=2, driver_level=4)
    worse = build_entrant_with_loadout("challenger", "t3_fd3s", mod_tier=1, driver_level=4)
    even = build_entrant_with_loadout("challenger", "t3_fd3s", mod_tier=2, driver_level=4)
    better = build_entrant_with_loadout("challenger", "t3_fd3s", mod_tier=3, driver_level=4)

    n_seeds = 120
    win_worse = sum(run_duel(worse, rival, seed=i).winner == "challenger" for i in range(n_seeds)) / n_seeds
    win_even = sum(run_duel(even, rival, seed=i).winner == "challenger" for i in range(n_seeds)) / n_seeds
    win_better = sum(run_duel(better, rival, seed=i).winner == "challenger" for i in range(n_seeds)) / n_seeds

    assert win_worse < win_even < win_better
    assert 0.60 <= win_better <= 0.80


def test_contact_and_wall_drains_are_clamped() -> None:
    assert compute_wall_hit_drain(DUEL_WALL_MIN_IMPACT_MPS) == 0.0
    assert compute_wall_hit_drain(0.5) == 0.0
    assert compute_wall_hit_drain(1e6) == pytest.approx(DUEL_WALL_DRAIN_MAX)
    assert compute_wall_hit_drain(1e6, wall_penalty_reduction=0.30) == pytest.approx(
        DUEL_WALL_DRAIN_MAX * 0.70
    )

    assert compute_contact_drain(DUEL_CONTACT_MIN_IMPACT_MPS, True) == (0.0, 0.0)
    da, db = compute_contact_drain(1e6, True)
    assert da == pytest.approx(DUEL_CONTACT_DRAIN_MAX * DUEL_CONTACT_INITIATOR_SHARE)
    assert db == pytest.approx(DUEL_CONTACT_DRAIN_MAX * DUEL_CONTACT_DEFENDER_SHARE)
    da_eq, db_eq = compute_contact_drain(1e6, None)
    assert da_eq == pytest.approx(DUEL_CONTACT_DRAIN_MAX * DUEL_CONTACT_EQUAL_SHARE)
    assert db_eq == pytest.approx(DUEL_CONTACT_DRAIN_MAX * DUEL_CONTACT_EQUAL_SHARE)


def test_duel_export_parity_and_sweep_smoke(tmp_path: Path) -> None:
    payload = json.loads(json.dumps(export_payload(include_parity_vectors=True)))
    const_keys = set(payload["constants"])
    assert "DUEL_GAP_DEAD_ZONE_M" in const_keys
    assert "DUEL_WALL_DRAIN_MAX" in const_keys
    assert "DUEL_CONTACT_DRAIN_MAX" in const_keys
    assert "DUEL_TRACKS" in const_keys
    assert set(payload["constants"]["DUEL_TRACKS"]) == {"street", "bayshore", "ridge"}
    assert not {k for k in const_keys if k.startswith("SP_") or k.startswith("SPIRIT_")}

    duel_vectors = payload.get("duel_parity_vectors", [])
    assert len(duel_vectors) >= 6

    sweep = run_duel_sweep(seeds_per_scenario=20, csv_dir=tmp_path)
    assert (tmp_path / "duel_sweep_summary.csv").exists()
    assert (tmp_path / "duel_sweep_runs.csv").exists()
    assert len(sweep["summary"]) == 3 * 12


def test_win_rate_bands_across_tracks() -> None:
    """Check +1-tier and even cross-car win-rate bands on each proposed track.

    The 1000-seed sweep in sim_output/duel_sweep_summary.csv landed a one-tier
    lead in 0.67-0.75 and even cross-car matchups in 0.47-0.55. This test uses
    fewer seeds (N=300 per case, six representative cases, one +1-tier and one
    even cross-car on each of street / bayshore / ridge) so the suite stays
    well under ~20 s. The asserted bands are widened to 0.62-0.78 and
    0.42-0.58 to absorb binomial sampling noise (SE ≈ 0.03 at N=300).
    """
    n_seeds = 300
    # (track_id, kind, challenger_car, challenger_tier, rival_car, rival_tier, driver_level)
    cases = (
        ("street", "plus1", "t1_s13", 1, "t1_s13", 0, 1),
        ("street", "even", "t5_devil_s30", 4, "t5_proto_r", 4, 8),
        ("bayshore", "plus1", "t3_fd3s", 3, "t3_fd3s", 2, 4),
        ("bayshore", "even", "t3_fd3s", 2, "t3_evo5", 2, 4),
        ("ridge", "plus1", "t5_devil_s30", 5, "t5_devil_s30", 4, 8),
        ("ridge", "even", "t5_devil_s30", 4, "t5_proto_r", 4, 8),
    )

    for track_id, kind, car_a, tier_a, car_b, tier_b, dlvl in cases:
        challenger = build_entrant_with_loadout(
            "challenger", car_a, mod_tier=tier_a, driver_level=dlvl
        )
        rival = build_entrant_with_loadout(
            "rival", car_b, mod_tier=tier_b, driver_level=dlvl
        )
        cfg = DuelConfig.from_track(track_id)
        wins = sum(
            run_duel(challenger, rival, seed=i, config=cfg).winner == "challenger"
            for i in range(n_seeds)
        )
        win_rate = wins / n_seeds
        if kind == "plus1":
            assert 0.62 <= win_rate <= 0.78, (
                f"{track_id} {car_a} t{tier_a} vs {car_b} t{tier_b}: "
                f"one-tier lead win rate {win_rate:.3f} outside 0.62-0.78"
            )
        else:
            assert 0.42 <= win_rate <= 0.58, (
                f"{track_id} {car_a} t{tier_a} vs {car_b} t{tier_b}: "
                f"even cross-car win rate {win_rate:.3f} outside 0.42-0.58"
            )
