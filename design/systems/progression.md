# Breakneck Progression & Balance Systems (Draft v0)

**Status:** Draft v0 (placeholder tuning; some questions remain open — see §4)  
**Source of Truth:** `sim/constants.py` and `sim/rules.py` (all numeric curves, thresholds, shop catalog entries, and roster entries live exclusively in `sim/constants.py`; this doc never duplicates numbers).  
**Engine Parity:** Enzo mirrors `sim/constants.py` into Godot via `python3 -m sim.export_constants` and validates against the exported `parity_vectors`.

---

## 1. Dual-Axis Architecture (Locked 2026-11-25)

Breakneck separates **persistent Driver meta-progression** from **per-Car equipment mastery** so players grow stronger across the campaign without suffering a punitive "new-car slump" whenever they switch rides.

### Axis A — Driver (Persistent Meta)
1. **Technique (`TECHNIQUE_SUBBRANCHES`, capped by `TECHNIQUE_MAX_LEVEL`)**  
   Equipment proficiency across three placeholder drivetrain/handling disciplines. Non-1:1 `tech_reqs` on each `CAR_ROSTER` entry form a prerequisite graph gating which cars can be driven. Technique also seeds each unlocked car's **Mastery floor** via `TECHNIQUE_TO_MASTERY_FLOOR`.
2. **Racing Spirit branch (`RACING_SPIRIT_SUBBRANCHES`, capped by `RACING_SPIRIT_MAX_LEVEL`)**  
   Maneuver-specific subbranches (`RACING_SPIRIT_MANEUVER_SUBBRANCH_MAP`) that scale in-race **Racing Spirit meter** generation (`RACING_SPIRIT_MANEUVER_BASE_GAIN`, `RACING_SPIRIT_GAIN_PER_LEVEL`, capped by `RACING_SPIRIT_METER_MAX`) and hold passive buffs (`RACING_SPIRIT_PASSIVE_BUFFS`). Passive buffs live on the Racing Spirit branch rather than Technique so Technique does not become a mandatory single-stat sink. The branch and the meter share the **Racing Spirit** name; code keeps them unambiguous (`racing_spirit_xp` / `racing_spirit_level` vs `racing_spirit_meter` / `compute_racing_spirit_meter_gain`).
3. **Stamina stat (`stamina_level`, capped by `STAMINA_MAX_LEVEL`)**  
   There is only one Stamina. The driver-tree stat raises a driver's Stamina points (`STAMINA_BAR_BASE` + `STAMINA_BAR_PER_STAMINA_LEVEL` → `stamina_bar_max`). The on-screen duel bar is always the same size; the UI shows current/max scaled to fill it, so a higher stat means more points to drain, not a longer bar. Code keeps identifiers unambiguous (`stamina_level` / `stamina_xp` vs `stamina_bar_max` / `STAMINA_BAR_*`).
4. **Shared Wallet (`PlayerProfile.credits`)**  
   Races pay out credits (`compute_race_credits`, `BASE_RACE_CREDITS_*`, `TIER_CREDITS_STEP_*`, `CLEAN_RACE_CREDITS_BONUS`) into a single shared wallet spent in the per-car mod shop.

### Axis B — Car (Per-Car Mastery & Shop)
1. **Base Stats**  
   Static chassis identity (`top_speed`, `acceleration`, `handling` in `CAR_ROSTER`).
2. **Mastery (`CAR_MASTERY_XP_THRESHOLDS`, capped by `CAR_MASTERY_MAX_LEVEL`)**  
   Ties Driver and Car together: `effective_car_mastery = max(earned_car_mastery, compute_mastery_floor(driver, car_spec))`. Mastery can exceed the floor through driving XP, but never falls below the Technique-seeded floor.
3. **Specials (`MASTERY_TO_SPECIAL_FLOOR`, `MASTERY_TO_SPECIAL_CEILING`)**  
   Car-specific levelable moves spending the in-race **Racing Spirit meter** (`RACING_SPIRIT_METER_MAX`), never the Stamina health bar. Non-1:1 Mastery thresholds determine both the unlocked baseline level (`special_floor`) and trainable cap (`special_ceiling`).
4. **Mastery-Gated Mod Shop (`MOD_CLASSES`, `MOD_CATALOG`, `MASTERY_TO_MOD_CEILING`, `MOD_TIER_FLOOR`)**  
   Mod tiers unlock **linearly** via `MASTERY_TO_MOD_CEILING` (no branching node graph; floor is always stock/`MOD_TIER_FLOOR`). Each unlocked tier is a shop shelf grouped by `MOD_CLASSES` (placeholder class names) with multiple purchasable tradeoff parts (sidegrades) per class per tier. Mods do **not** auto-advance from races; players buy them per car from the shared wallet (`buy_mod_part`).

---

## 2. Non-1:1 Threshold Gating, XP & Credit Flow

- **Prerequisite Graph:** Higher-tier entries in `CAR_ROSTER` require multi-branch thresholds in `tech_reqs` rather than a 1:1 linear level check.
- **XP & Credit Routing (`apply_race_result`):** Each race awards Driver XP (`BASE_RACE_DRIVER_XP`, `TIER_XP_STEP_DRIVER`, `WIN_XP_MULTIPLIER` / `LOSS_XP_MULTIPLIER`, `CLEAN_RACE_XP_BONUS`) across Technique, Racing Spirit, and Stamina, awards Car XP (`BASE_RACE_CAR_XP`, `TIER_XP_STEP_CAR`) **only to the active car driven**, and pays Credits into the shared `PlayerProfile.credits` wallet. Parked garage cars gain zero passive XP and zero automatic parts.
- **Direct-Tier Shop Purchases:** Any unlocked tier `<= mod_tier_ceiling(effective_car_mastery)` can be bought directly with no lower-tier prerequisite (`buy_mod_part`).
- **Anti-Grind & Anti-Slump Checks (`sim/simulate.py`):**
  - **Technique Grind-Wall Flag:** Flags any tier unlock delta exceeding `GRIND_WALL_RATIO` times the previous tier's delta.
  - **Shop Economy Grind-Wall Flag (`compute_shop_economy`):** Measures races of expected income required to afford a full tier kit across `MOD_CLASSES` and flags any tier jump exceeding `GRIND_WALL_RATIO` times the previous tier.
  - **Slump Check:** Measures races required on a newly unlocked higher-tier car (using purchased balanced loadouts) to reach `COMPETITIVE_POWER_RATIO * TIER_RIVAL_BENCHMARK_POWER[tier]`, compared against a `floor = 0` counterfactual starting with the same entry wallet.

---

## 3. Mod Ownership & Shop Rules (Locked 2026-11-25)

1. **Unique per car:** Purchased parts live in each `CarState.owned_parts` and equipped parts in `CarState.equipped_parts`. There is no shared parts pool across cars; new cars start stock and buy their own parts.
2. **Free swaps, no refunds, no respec:** Owned parts on a car can be swapped or unequipped freely (`equip_mod_part`, `unequip_mod_class`) with zero credit cost and zero currency refund. There is no car mod respec.
3. **One equipped part per class; intra-tier sidegrades:** Each class holds at most one equipped part (`effective_car_stats`). Multiple options per class per tier in `MOD_CATALOG` represent genuine stat tradeoffs (e.g., top speed vs handling/acceleration), never strictly dominated choices.
4. **Shared race-earned wallet:** Credits earned from races go into one shared `PlayerProfile.credits` wallet, which can fund parts on any unlocked car.
5. **Linear Mastery shelf gate, direct purchase:** Mastery sets the hard ceiling on which mod tier can be bought or installed (`MASTERY_TO_MOD_CEILING`), with no lower-tier purchase prerequisites.

---

## 4. Decisions (2026-11-25) & Remaining Open Questions

### Decided
1. **Mods are unique per car.** Austin: keep per-car unique mods to stay in the spirit of a progression tree.
2. **The TXR battle bar is named Stamina, and reads as a health bar.** Austin: the health bar should be named "stamina" (or similar) to indicate it is a health bar. There is only one Stamina (no rename): the driver-tree stat raises Stamina points (`stamina_bar_max`), and the on-screen bar stays a fixed size, filled by current/max. Identifiers distinguish the stat level (`stamina_level`) from the point pool (`stamina_bar_max`, `STAMINA_BAR_*`).
3. **The driver branch and the super meter are both called Racing Spirit.** Austin: "Heat does not work because heat is usually something you avoid in racing." Identifiers distinguish the branch (`racing_spirit_xp`, `racing_spirit_level`, `RACING_SPIRIT_SUBBRANCHES`) from the meter (`racing_spirit_meter`, `RACING_SPIRIT_METER_MAX`, `compute_racing_spirit_meter_gain`). Retired names: SP, SP bar, Spirit (bare), Heat.
4. **Mastery-gated linear mod shop; no car respec.** Austin: *"Mastery indicates what tier of mods you can install. Each tier has different mods relating to power, handling, etc. There are multiple mods per class per tier. You must buy them."* Locked shop rules: (a) owned parts swap freely per car with no refunds (no respec), because tiers unlock linearly as shelves and purchases are permanent per car rather than a refundable point tree; (b) one equipped part per class, with same-tier options as tradeoffs (sidegrades); (c) one shared wallet earned from races; (d) any unlocked tier up to the car's Mastery ceiling can be bought directly with no lower-tier prerequisite.

### Still open
1. **Canonical mod class names (`MOD_CLASSES`)**
   - Current placeholders: `power`, `drivetrain`, `handling`, `aero`.
   - Open for Austin to rename/split/merge classes (e.g., *Power / Handling / Drivetrain / Brakes / Aero* or *Engine / Chassis / Tires / Aero*).
2. **Canonical subbranch names (`TECHNIQUE_SUBBRANCHES`, `RACING_SPIRIT_SUBBRANCHES`)**
   - Current placeholders:
     - Technique: `chassis_craft` (FR/MR balance), `traction_line` (AWD/FF grip), `aero_velocity` (high-speed stability/drafting).
     - Racing Spirit: `drift_flow`, `slipstream_nerve`, `clean_line`.
   - *Options:* Keep drivetrain/discipline flavor (e.g., *Oversteer / Grip / Wangan* or *Street / Touge / Expressway*) vs. mechanical component flavor (*Chassis / Drivetrain / Aero*).
   - *Recommendation:* *Chassis / Traction / Aero* (or *Drift / Grip / Wangan*) for Technique so car prerequisites feel intuitive, and maneuver-evocative names (*Flow / Nerve / Precision*) for Racing Spirit.
3. **Driver respec policy (Technique, Racing Spirit branch, Stamina stat)** *(Car mod respec is closed/rejected.)*
   - *Option A (recommended):* Free garage/PA respec for Driver points, with Technique respec required to retain prerequisites for the currently equipped car (or auto-swap to a valid car).
   - *Option B:* Paid respec item/credits.
   - *Option C:* No respec (permanent commitments).
