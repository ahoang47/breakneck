"""Single source of truth for Breakneck progression & balance constants.

ALL numeric values, curves, threshold tables, shop catalog entries, and roster
entries in this file are PLACEHOLDER draft-v0 numbers pending playtest
validation and Austin's decisions on open design questions.

Enzo's Godot engine layer mirrors this module via `sim/export_constants.py`
into a single Godot globals file and validates parity against exported vectors.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Metadata & Parity Versioning (PLACEHOLDER)
# ---------------------------------------------------------------------------
SIM_SCHEMA_VERSION = "0.2.0-draft"
PLACEHOLDER_META: dict[str, Any] = {
    "status": "PLACEHOLDER",
    "version": SIM_SCHEMA_VERSION,
    "locked_design_date": "2026-11-25",
    "note": (
        "All curves, thresholds, XP rates, shop prices/parts, and roster "
        "entries are placeholder values for first-pass pacing validation."
    ),
}

# ---------------------------------------------------------------------------
# Driver Subbranches & Caps (PLACEHOLDER)
# ---------------------------------------------------------------------------
# Open question for Austin: finalize canonical subbranch names.
TECHNIQUE_SUBBRANCHES: tuple[str, ...] = (
    "chassis_craft",    # PLACEHOLDER: FR/MR oversteer & balance proficiency
    "traction_line",    # PLACEHOLDER: AWD/FF grip & corner-exit proficiency
    "aero_velocity",    # PLACEHOLDER: High-speed stability & drafting proficiency
)

# Open question for Austin: finalize Racing Spirit subbranch names & passive buffs.
RACING_SPIRIT_SUBBRANCHES: tuple[str, ...] = (
    "drift_flow",       # PLACEHOLDER: Clean drift Racing Spirit meter gain + exit stability buff
    "slipstream_nerve", # PLACEHOLDER: Drafting/near-miss Racing Spirit meter gain + scrape mitigation
    "clean_line",       # PLACEHOLDER: Clean overtake Racing Spirit meter gain + meter retention
)

TECHNIQUE_MAX_LEVEL: int = 10           # PLACEHOLDER
RACING_SPIRIT_MAX_LEVEL: int = 10      # PLACEHOLDER
STAMINA_MAX_LEVEL: int = 10             # PLACEHOLDER
CAR_MASTERY_MAX_LEVEL: int = 10         # PLACEHOLDER
MOD_TIER_FLOOR: int = 0                 # LOCKED: stock/unequipped = 0; Mastery is ceiling-only
MAX_MOD_TIER: int = 5                   # PLACEHOLDER
MAX_SPECIAL_LEVEL: int = 5              # PLACEHOLDER

# LOCKED 2026-11-25: mods are unique per car; one equipped part per class;
# owned parts swap freely with no refunds.
# Open question for Austin: finalize canonical mod class names.
MOD_CLASSES: tuple[str, ...] = (
    "power",       # PLACEHOLDER: engine / intake / exhaust / boost
    "drivetrain",  # PLACEHOLDER: gearbox / clutch / differential
    "handling",    # PLACEHOLDER: suspension / chassis brace / tires
    "aero",        # PLACEHOLDER: splitter / diffuser / rear wing
)  # PLACEHOLDER

# ---------------------------------------------------------------------------
# XP Curves (Cumulative XP required to reach index level 0..10) (PLACEHOLDER)
# Smooth sub-2x step increments to keep progression grind-free.
# ---------------------------------------------------------------------------
TECHNIQUE_XP_THRESHOLDS: tuple[int, ...] = (
    0, 160, 410, 580, 760, 1040, 1360, 1740, 2180, 2680, 3240
)  # PLACEHOLDER

RACING_SPIRIT_XP_THRESHOLDS: tuple[int, ...] = (
    0, 90, 210, 360, 540, 750, 990, 1260, 1560, 1900, 2280
)  # PLACEHOLDER

STAMINA_XP_THRESHOLDS: tuple[int, ...] = (
    0, 80, 190, 330, 500, 700, 930, 1190, 1480, 1800, 2150
)  # PLACEHOLDER

CAR_MASTERY_XP_THRESHOLDS: tuple[int, ...] = (
    0, 150, 340, 570, 840, 1150, 1500, 1890, 2320, 2790, 3300
)  # PLACEHOLDER

# ---------------------------------------------------------------------------
# Non-1:1 Threshold Gating Tables (PLACEHOLDER)
# Each table is an ordered sequence of (min_input_level, output_value) pairs.
# ---------------------------------------------------------------------------
# Technique (primary category level) -> Car Mastery Floor
TECHNIQUE_TO_MASTERY_FLOOR: tuple[tuple[int, int], ...] = (
    (0, 0),
    (2, 1),
    (4, 3),
    (6, 5),
    (8, 7),
    (10, 8),
)  # PLACEHOLDER

# Car Mastery -> Highest Unlockable Mod Shop Tier Shelf (hard ceiling, direct buy)
MASTERY_TO_MOD_CEILING: tuple[tuple[int, int], ...] = (
    (0, 1),
    (2, 2),
    (4, 3),
    (7, 4),
    (9, 5),
)  # PLACEHOLDER

# Car Mastery -> Special Level Floor (unlocked baseline level)
MASTERY_TO_SPECIAL_FLOOR: tuple[tuple[int, int], ...] = (
    (0, 0),
    (1, 1),
    (3, 2),
    (5, 3),
    (7, 4),
    (9, 5),
)  # PLACEHOLDER

# Car Mastery -> Special Level Ceiling (max level trainable on that car)
MASTERY_TO_SPECIAL_CEILING: tuple[tuple[int, int], ...] = (
    (0, 1),
    (2, 2),
    (4, 3),
    (6, 4),
    (8, 5),
)  # PLACEHOLDER

# ---------------------------------------------------------------------------
# Stamina Health Bar (sized by stamina_level) & Racing Spirit Meter (PLACEHOLDER)
# ---------------------------------------------------------------------------
# LOCKED 2026-11-25: battle bar is Stamina (a health bar); branch + super meter
# are both Racing Spirit. Names stay unambiguous: stamina_level vs stamina_bar_*.
STAMINA_BAR_BASE: float = 1000.0            # PLACEHOLDER: Stamina health bar base
STAMINA_BAR_PER_STAMINA_LEVEL: float = 120.0  # PLACEHOLDER: +120 bar capacity per stamina_level

RACING_SPIRIT_METER_MAX: float = 100.0      # PLACEHOLDER: In-race Racing Spirit super meter cap
RACING_SPIRIT_GAIN_PER_LEVEL: float = 0.08  # PLACEHOLDER: +8% meter gain per Racing Spirit subbranch level

RACING_SPIRIT_MANEUVER_BASE_GAIN: dict[str, float] = {
    "clean_drift": 12.0,      # PLACEHOLDER
    "slipstream_tick": 5.0,   # PLACEHOLDER
    "near_miss": 8.0,         # PLACEHOLDER
    "clean_overtake": 18.0,   # PLACEHOLDER
}

RACING_SPIRIT_MANEUVER_SUBBRANCH_MAP: dict[str, str] = {
    "clean_drift": "drift_flow",
    "slipstream_tick": "slipstream_nerve",
    "near_miss": "slipstream_nerve",
    "clean_overtake": "clean_line",
}

# Passive buffs live on the Racing Spirit branch (moved off Technique so Technique isn't mandatory).
RACING_SPIRIT_PASSIVE_BUFFS: dict[str, dict[str, float]] = {
    "drift_flow": {"corner_exit_traction_per_level": 0.015},        # PLACEHOLDER
    "slipstream_nerve": {"wall_stamina_penalty_reduction_per_level": 0.03},  # PLACEHOLDER
    "clean_line": {"racing_spirit_carryover_ratio_per_level": 0.025},  # PLACEHOLDER
}

# ---------------------------------------------------------------------------
# Per-Race XP, Shared Wallet Credits & Special Leveling (PLACEHOLDER)
# ---------------------------------------------------------------------------
BASE_RACE_DRIVER_XP: int = 130              # PLACEHOLDER
BASE_RACE_CAR_XP: int = 80                  # PLACEHOLDER
TIER_XP_STEP_DRIVER: int = 22               # PLACEHOLDER: extra Driver XP per rival tier above 1
TIER_XP_STEP_CAR: int = 10                  # PLACEHOLDER: extra Car XP per rival tier above 1
WIN_XP_MULTIPLIER: float = 1.25             # PLACEHOLDER
LOSS_XP_MULTIPLIER: float = 0.70            # PLACEHOLDER
CLEAN_RACE_XP_BONUS: float = 0.10           # PLACEHOLDER: +10% XP for clean driving

# LOCKED 2026-11-25: single shared wallet earned from races; spent on per-car mod shop.
BASE_RACE_CREDITS_WIN: int = 850            # PLACEHOLDER
BASE_RACE_CREDITS_LOSS: int = 320           # PLACEHOLDER
TIER_CREDITS_STEP_WIN: int = 350            # PLACEHOLDER: extra win credits per rival tier above 1
TIER_CREDITS_STEP_LOSS: int = 120           # PLACEHOLDER: extra loss credits per rival tier above 1
CLEAN_RACE_CREDITS_BONUS: float = 0.15      # PLACEHOLDER: +15% credits for clean driving

# Special XP / natural leveling per race within [special_floor, special_ceiling].
SPECIAL_PROGRESS_WIN: float = 0.50          # PLACEHOLDER
SPECIAL_PROGRESS_LOSS: float = 0.25         # PLACEHOLDER

# ---------------------------------------------------------------------------
# Mastery-Gated Mod Shop Catalog (PLACEHOLDER)
# Tier x Class catalog: 5 Tiers x 4 Classes x 3 Tradeoff Options = 60 parts.
# All same-(tier, mod_class) options are strict sidegrades (no strict dominance).
# ---------------------------------------------------------------------------
_TIER_NAMES: dict[int, str] = {
    1: "Street",
    2: "Club",
    3: "Wangan",
    4: "Works",
    5: "Midnight",
}

_TIER_BASE_PRICES: dict[int, int] = {
    1: 1000,   # PLACEHOLDER
    2: 1700,   # PLACEHOLDER
    3: 2500,   # PLACEHOLDER
    4: 3400,   # PLACEHOLDER
    5: 4400,   # PLACEHOLDER
}

_CLASS_PRICE_MULT: dict[str, float] = {
    "power": 1.10,       # PLACEHOLDER
    "drivetrain": 1.00,  # PLACEHOLDER
    "handling": 1.00,    # PLACEHOLDER
    "aero": 0.90,        # PLACEHOLDER
}

# (style_tag, label, top_speed_per_tier, accel_per_tier, handling_per_tier)
_CLASS_ARCHETYPES: dict[str, tuple[tuple[str, str, float, float, float], ...]] = {
    "power": (
        ("top_speed", "High-Boost Turbo", 1.5, 1.0, -0.5),
        ("balanced", "Balanced Power Tune", 0.9, 0.9, 0.2),
        ("handling", "Throttle-Response NA", 0.3, 1.2, 0.5),
    ),
    "drivetrain": (
        ("top_speed", "Long-Ratio Gearset", 1.4, 0.4, 0.2),
        ("balanced", "Close-Ratio Street Box", 0.7, 0.9, 0.4),
        ("handling", "Short-Ratio Sprint LSD", -0.3, 1.6, 0.7),
    ),
    "handling": (
        ("top_speed", "High-Speed Stability Kit", 0.8, 0.4, 0.8),
        ("balanced", "Street Coilover Setup", 0.3, 0.7, 1.0),
        ("handling", "Touge Attack Dampers", -0.4, 0.9, 1.5),
    ),
    "aero": (
        ("top_speed", "Low-Drag Slipstream Kit", 1.6, 0.8, -0.4),
        ("balanced", "Balanced Street Aero", 0.8, 0.6, 0.6),
        ("handling", "High-Downforce Wing Kit", -0.5, 0.9, 1.6),
    ),
}


def _build_mod_catalog() -> tuple[dict[str, Any], ...]:
    entries: list[dict[str, Any]] = []
    for tier in range(1, MAX_MOD_TIER + 1):
        tier_label = _TIER_NAMES[tier]
        base_price = _TIER_BASE_PRICES[tier]
        for mod_class in MOD_CLASSES:
            price = round(base_price * _CLASS_PRICE_MULT[mod_class] / 10.0) * 10
            for style_tag, label, ts_t, ac_t, hd_t in _CLASS_ARCHETYPES[mod_class]:
                entries.append(
                    {
                        "part_id": f"t{tier}_{mod_class}_{style_tag}",
                        "name": f"{tier_label} {label}",
                        "tier": tier,
                        "mod_class": mod_class,
                        "style_tag": style_tag,
                        "price": int(price),
                        "top_speed_delta": round(ts_t * tier, 2),
                        "acceleration_delta": round(ac_t * tier, 2),
                        "handling_delta": round(hd_t * tier, 2),
                    }
                )
    return tuple(entries)


MOD_CATALOG: tuple[dict[str, Any], ...] = _build_mod_catalog()  # PLACEHOLDER

# ---------------------------------------------------------------------------
# Power Rating & Competitiveness Benchmarks (PLACEHOLDER)
# Used by the simulation slump check and rival pacing diagnostics.
# ---------------------------------------------------------------------------
POWER_PER_MASTERY_LEVEL: float = 1.2        # PLACEHOLDER
POWER_PER_SPECIAL_LEVEL: float = 1.0        # PLACEHOLDER
COMPETITIVE_POWER_RATIO: float = 0.98       # PLACEHOLDER: >= 98% of tier benchmark = competitive
GRIND_WALL_RATIO: float = 2.0               # Flag tier delta > 2.0x previous tier delta

TIER_RIVAL_BENCHMARK_POWER: dict[int, float] = {
    1: 67.0,   # PLACEHOLDER
    2: 80.5,   # PLACEHOLDER
    3: 93.0,   # PLACEHOLDER
    4: 106.0,  # PLACEHOLDER
    5: 118.5,  # PLACEHOLDER
}

# ---------------------------------------------------------------------------
# Car Roster: 15 Placeholder Cars across 5 Tiers x 3 Categories (PLACEHOLDER)
# ---------------------------------------------------------------------------
# Each entry is a dict for clean JSON export; wrapped into CarSpec in models.py.
# `tech_reqs` encodes the non-1:1 prerequisite graph: {subbranch: min_level}.
CAR_ROSTER: tuple[dict[str, Any], ...] = (
    # Tier 1 — Starter (3 cars, unlocked at Tech 0)
    {
        "car_id": "t1_s13",
        "name": "89 Kouki S13",
        "tier": 1,
        "primary_subbranch": "chassis_craft",
        "top_speed": 62.0,
        "acceleration": 62.0,
        "handling": 63.0,
        "tech_reqs": {},
        "special_ids": ("apex_flick", "night_clutch"),
    },
    {
        "car_id": "t1_eg6",
        "name": "92 Civic SiR",
        "tier": 1,
        "primary_subbranch": "traction_line",
        "top_speed": 62.0,
        "acceleration": 63.0,
        "handling": 62.0,
        "tech_reqs": {},
        "special_ids": ("vtec_surge", "late_brake"),
    },
    {
        "car_id": "t1_z31",
        "name": "87 Fairlady 300ZX",
        "tier": 1,
        "primary_subbranch": "aero_velocity",
        "top_speed": 63.0,
        "acceleration": 62.0,
        "handling": 62.0,
        "tech_reqs": {},
        "special_ids": ("wangan_pull", "boost_spike"),
    },
    # Tier 2 — Clubman (3 cars, primary Tech >= 2)
    {
        "car_id": "t2_fc3s",
        "name": "90 Savanna RX-7",
        "tier": 2,
        "primary_subbranch": "chassis_craft",
        "top_speed": 72.0,
        "acceleration": 72.0,
        "handling": 73.0,
        "tech_reqs": {"chassis_craft": 2},
        "special_ids": ("rotary_snap", "gutter_hook"),
    },
    {
        "car_id": "t2_gc8",
        "name": "95 Impreza WRX",
        "tier": 2,
        "primary_subbranch": "traction_line",
        "top_speed": 72.0,
        "acceleration": 73.0,
        "handling": 72.0,
        "tech_reqs": {"traction_line": 2},
        "special_ids": ("awd_launch", "chicane_bite"),
    },
    {
        "car_id": "t2_a70",
        "name": "91 Supra Turbo-A",
        "tier": 2,
        "primary_subbranch": "aero_velocity",
        "top_speed": 73.0,
        "acceleration": 72.0,
        "handling": 72.0,
        "tech_reqs": {"aero_velocity": 2},
        "special_ids": ("twin_spool", "draft_sling"),
    },
    # Tier 3 — Expressway (3 cars, non-1:1 multi-branch: primary >= 4, secondary >= 2)
    {
        "car_id": "t3_fd3s",
        "name": "96 RX-7 Type RS",
        "tier": 3,
        "primary_subbranch": "chassis_craft",
        "top_speed": 83.0,
        "acceleration": 83.0,
        "handling": 84.0,
        "tech_reqs": {"chassis_craft": 4, "aero_velocity": 2},
        "special_ids": ("twin_rotary_overdrive", "razor_entry"),
    },
    {
        "car_id": "t3_evo5",
        "name": "98 Lancer Evo V",
        "tier": 3,
        "primary_subbranch": "traction_line",
        "top_speed": 83.0,
        "acceleration": 84.0,
        "handling": 83.0,
        "tech_reqs": {"traction_line": 4, "chassis_craft": 2},
        "special_ids": ("ayc_vector_cut", "turbo_anti_lag"),
    },
    {
        "car_id": "t3_r33",
        "name": "95 Skyline GT-R V-Spec",
        "tier": 3,
        "primary_subbranch": "aero_velocity",
        "top_speed": 84.0,
        "acceleration": 83.0,
        "handling": 83.0,
        "tech_reqs": {"aero_velocity": 4, "traction_line": 2},
        "special_ids": ("attesa_surge", "high_gear_lock"),
    },
    # Tier 4 — Midnight (3 cars, primary >= 6, secondary >= 4)
    {
        "car_id": "t4_nsx",
        "name": "97 NSX Type S",
        "tier": 4,
        "primary_subbranch": "chassis_craft",
        "top_speed": 91.0,
        "acceleration": 91.0,
        "handling": 92.0,
        "tech_reqs": {"chassis_craft": 6, "traction_line": 3},
        "special_ids": ("midship_poise", "vtec_scream"),
    },
    {
        "car_id": "t4_r34",
        "name": "99 Skyline GT-R M-Spec",
        "tier": 4,
        "primary_subbranch": "traction_line",
        "top_speed": 91.0,
        "acceleration": 92.0,
        "handling": 91.0,
        "tech_reqs": {"traction_line": 6, "aero_velocity": 3},
        "special_ids": ("rb26_overboost", "apex_lock"),
    },
    {
        "car_id": "t4_jza80",
        "name": "98 Supra RZ Twin",
        "tier": 4,
        "primary_subbranch": "aero_velocity",
        "top_speed": 92.0,
        "acceleration": 91.0,
        "handling": 91.0,
        "tech_reqs": {"aero_velocity": 6, "chassis_craft": 3},
        "special_ids": ("2jz_blast", "tunnel_flash"),
    },
    # Tier 5 — Wangan Apex (3 cars, primary >= 8, both other subbranches >= 5)
    {
        "car_id": "t5_devil_s30",
        "name": "Midnight S30-Z Custom",
        "tier": 5,
        "primary_subbranch": "chassis_craft",
        "top_speed": 101.0,
        "acceleration": 101.0,
        "handling": 102.0,
        "tech_reqs": {"chassis_craft": 8, "traction_line": 4, "aero_velocity": 4},
        "special_ids": ("devil_line", "limit_break"),
    },
    {
        "car_id": "t5_proto_r",
        "name": "Wangan Spec-R Prototype",
        "tier": 5,
        "primary_subbranch": "traction_line",
        "top_speed": 101.0,
        "acceleration": 102.0,
        "handling": 101.0,
        "tech_reqs": {"traction_line": 8, "chassis_craft": 4, "aero_velocity": 4},
        "special_ids": ("zero_slip_exit", "overtake_pulse"),
    },
    {
        "car_id": "t5_blackbird",
        "name": "934 Turbo Carrera",
        "tier": 5,
        "primary_subbranch": "aero_velocity",
        "top_speed": 102.0,
        "acceleration": 101.0,
        "handling": 101.0,
        "tech_reqs": {"aero_velocity": 8, "chassis_craft": 4, "traction_line": 4},
        "special_ids": ("terminal_draft", "midnight_surge"),
    },
)

# ---------------------------------------------------------------------------
# Closed-Loop Duel Rules, Track Profiles & Balance Constants (Draft v0 / PLACEHOLDER)
# ---------------------------------------------------------------------------
DUEL_TICK_DT_S: float = 0.25                        # PLACEHOLDER: 4 Hz deterministic sim tick
DUEL_STAMINA_PCT_TIE_EPS: float = 1e-4              # Tie tolerance on remaining Stamina % at lap cap

# Track profiles proposed by Nori (NOT locked by Austin).
# Replaces single default loop; each track defines loop geometry, rolling start, and corner/wall factors.
DUEL_DEFAULT_TRACK_ID: str = "street"               # PLACEHOLDER: proposed by Nori
DUEL_TRACKS: dict[str, dict[str, Any]] = {
    "street": {
        "name": "Street (Tight)",
        "proposed_by": "Nori",
        "locked": False,
        "loop_length_m": 3600.0,
        "max_laps": 6,
        "start_speed_mps": 34.0,     # Slower tight-street rolling start (~122 km/h)
        "start_gap_m": 6.0,
        "grace_period_s": 5.0,
        "corners_per_lap": 6,
        "corner_duty": 0.35,
        "wall_hit_rate_mult": 1.00,
        "contact_rate_mult": 1.20,
    },
    "bayshore": {
        "name": "Bayshore (Fast)",
        "proposed_by": "Nori",
        "locked": False,
        "loop_length_m": 6500.0,
        "max_laps": 3,
        "start_speed_mps": 46.0,     # Fast Wangan highway rolling start (~166 km/h)
        "start_gap_m": 8.5,
        "grace_period_s": 5.0,
        "corners_per_lap": 3,
        "corner_duty": 0.27,
        "wall_hit_rate_mult": 0.96,
        "contact_rate_mult": 0.90,
    },
    "ridge": {
        "name": "Ridge (Technical)",
        "proposed_by": "Nori",
        "locked": False,
        "loop_length_m": 4200.0,
        "max_laps": 5,
        "start_speed_mps": 38.0,     # Technical mountain-pass rolling start (~137 km/h)
        "start_gap_m": 8.0,
        "grace_period_s": 5.5,
        "corners_per_lap": 7,
        "corner_duty": 0.38,
        "wall_hit_rate_mult": 1.03,
        "contact_rate_mult": 1.05,
    },
}

# Stamina Drain from Gap (trailing car drains; leader gap drain = 0)
DUEL_GAP_DEAD_ZONE_M: float = 8.0                   # PLACEHOLDER: zero gap drain within 8 m battle zone
DUEL_GAP_DRAIN_BASE_PER_S: float = 18.0             # PLACEHOLDER: Stamina/s drain once past dead zone
DUEL_GAP_DRAIN_SLOPE_PER_M_S: float = 0.36          # PLACEHOLDER: extra Stamina/s per meter past dead zone
DUEL_GAP_DRAIN_CAP_PER_S: float = 72.0              # PLACEHOLDER: max gap Stamina drain per second

# Wall Hit Stamina Drain (impact-scaled, clamped, mitigated by slipstream_nerve passive)
DUEL_WALL_MIN_IMPACT_MPS: float = 2.0               # PLACEHOLDER: light wall brush threshold (0 drain below)
DUEL_WALL_DRAIN_PER_MPS: float = 12.0               # PLACEHOLDER: Stamina drain per m/s above threshold
DUEL_WALL_DRAIN_MAX: float = 145.0                  # PLACEHOLDER: hard clamp per wall hit
DUEL_WALL_SPEED_SCRUB_RATIO: float = 0.16           # PLACEHOLDER: speed scrub fraction on wall hit
DUEL_WALL_HIT_PROB_PER_S: float = 0.012             # PLACEHOLDER: baseline wall-hit hazard rate per second
DUEL_WALL_SAMPLE_IMPACT_MIN_MPS: float = 3.0        # PLACEHOLDER: min sampled lateral wall impact (m/s)
DUEL_WALL_SAMPLE_IMPACT_MAX_MPS: float = 14.0       # PLACEHOLDER: max sampled lateral wall impact (m/s)
DUEL_WALL_CORNER_EXPOSURE_MULT: float = 1.4         # PLACEHOLDER: wall hazard multiplier inside corners
DUEL_WALL_STRAIGHT_EXPOSURE_MULT: float = 0.7       # PLACEHOLDER: wall hazard multiplier on straights

# Car-to-Car Contact Stamina Drain (impact-scaled, clamped; initiator 100%, defender 60%)
DUEL_CONTACT_PROXIMITY_M: float = 5.0               # PLACEHOLDER: longitudinal window for contact events
DUEL_CONTACT_COOLDOWN_S: float = 1.5                # PLACEHOLDER: cooldown between contact events
DUEL_CONTACT_MIN_IMPACT_MPS: float = 1.5            # PLACEHOLDER: light paint-rub threshold (0 drain below)
DUEL_CONTACT_DRAIN_PER_MPS: float = 10.5            # PLACEHOLDER: Stamina drain per m/s above threshold
DUEL_CONTACT_DRAIN_MAX: float = 125.0               # PLACEHOLDER: hard clamp per contact event
DUEL_CONTACT_INITIATOR_SHARE: float = 1.0           # PLACEHOLDER: trailing/ramming car takes 100%
DUEL_CONTACT_DEFENDER_SHARE: float = 0.6            # PLACEHOLDER: defending/lead car takes 60%
DUEL_CONTACT_EQUAL_SHARE: float = 0.8               # PLACEHOLDER: dead-heat side-by-side contact share
DUEL_CONTACT_SPEED_SCRUB_RATIO: float = 0.08        # PLACEHOLDER: speed scrub fraction on contact
DUEL_CONTACT_PROB_PER_S: float = 0.11               # PLACEHOLDER: contact hazard rate when proximate
DUEL_CONTACT_SAMPLE_IMPACT_MIN_MPS: float = 2.0     # PLACEHOLDER: min sampled contact impact (m/s)
DUEL_CONTACT_SAMPLE_IMPACT_MAX_MPS: float = 11.0    # PLACEHOLDER: max sampled contact impact (m/s)

# Racing Spirit In-Duel Fill & Specials (Specials spend Racing Spirit, NEVER Stamina)
DUEL_RACING_SPIRIT_LEAD_RATE_PER_S: float = 2.88     # PLACEHOLDER: base Racing Spirit/s while leading cleanly
DUEL_SLIPSTREAM_MAX_GAP_M: float = 32.0             # PLACEHOLDER: max trailing gap for slipstream & meter tick
DUEL_SLIPSTREAM_TICK_INTERVAL_S: float = 2.0        # PLACEHOLDER: interval between slipstream_tick gains
DUEL_SLIPSTREAM_SPEED_BONUS_MPS: float = 1.24        # PLACEHOLDER: drafting speed bonus while trailing in slipstream
DUEL_SPECIAL_COST: float = 58.0                     # PLACEHOLDER: Racing Spirit meter spent per Special
DUEL_SPECIAL_DURATION_S: float = 4.0                # PLACEHOLDER: duration of Special boost
DUEL_SPECIAL_BASE_SPEED_BONUS_MPS: float = 2.6      # PLACEHOLDER: Special boost (m/s) at level 0
DUEL_SPECIAL_SPEED_BONUS_PER_LEVEL_MPS: float = 0.25 # PLACEHOLDER: extra boost (m/s) per Special level

# Physics / Speed / Skill Noise Mapping (tick-based duel sim)
DUEL_MIN_SPEED_MPS: float = 15.0                    # PLACEHOLDER: floor speed after wall/contact scrubs
DUEL_SPEED_BASE_MPS: float = 51.5                   # PLACEHOLDER: straight speed intercept (m/s)
DUEL_SPEED_PER_STAT_MPS: float = 0.145               # PLACEHOLDER: straight m/s per top_speed stat point
DUEL_CORNER_BASE_MPS: float = 32.1                  # PLACEHOLDER: corner apex speed intercept (m/s)
DUEL_CORNER_PER_HANDLING_MPS: float = 0.056         # PLACEHOLDER: corner apex m/s per handling stat point
DUEL_ACCEL_BASE_MPS2: float = 1.05                   # PLACEHOLDER: base accel rate intercept
DUEL_ACCEL_PER_STAT_MPS2: float = 0.020             # PLACEHOLDER: corner-exit accel rate per acceleration point
DUEL_BRAKE_RATE_MPS2: float = 14.0                  # PLACEHOLDER: corner-entry braking deceleration (m/s^2)
DUEL_SKILL_NOISE_STD_MPS: float = 0.75              # PLACEHOLDER: driver speed noise std dev (m/s)
DUEL_SKILL_NOISE_DECAY: float = 0.90                # PLACEHOLDER: AR(1) persistence per tick
DUEL_CLEAN_DRIFT_PROB_PER_CORNER: float = 0.35      # PLACEHOLDER: chance a clean corner yields clean_drift
# Closed-loop near misses are barrier shaves only (no traffic).
# Open question for Austin: do closed-loop tracks have traffic?
DUEL_NEAR_MISS_PROB_PER_S: float = 0.03             # PLACEHOLDER: barrier-shave near-miss rate (no traffic)
