# Breakneck Closed-Loop Duel Rules (Draft v0)

**Status:** Draft v0 (locked structure for closed-loop duels; track profiles proposed by Nori and open for Austin; feel/preference items marked **Austin decides** in §7)  
**Source of Truth:** `sim/constants.py` and `sim/duel.py` (all numeric rates, thresholds, clamps, track profiles, and physics parameters live exclusively in `sim/constants.py`; this doc references constant names and never duplicates numbers).  
**Engine Parity:** Enzo mirrors `sim/constants.py` into Godot via `python3 -m sim.export_constants` and validates against both `parity_vectors` and `duel_parity_vectors` in `sim_output/constants_export.json`.

---

## 1. Terminology & Bar Separation

- **Stamina (Locked 2026-11-25):** There is only one Stamina (Austin, 2026-11-25; the GDD's `'SP bar'` wording is being updated to match). The on-screen duel bar is always the same size. The driver-tree Stamina stat (`stamina_level`, capped by `STAMINA_MAX_LEVEL`) raises a driver's Stamina points — the pool `stamina_bar_max = STAMINA_BAR_BASE + STAMINA_BAR_PER_STAMINA_LEVEL * stamina_level`. The UI shows current/max scaled to fill that fixed bar, so a higher stat means more points to drain, not a longer bar. Code keeps identifiers unambiguous (`stamina_level` / `stamina_xp` vs `stamina_bar_max` / `STAMINA_BAR_*`).
- **Racing Spirit:** Refers strictly to the **in-race super meter** (`RACING_SPIRIT_METER_MAX`) and the **Driver branch** (`RACING_SPIRIT_SUBBRANCHES`) that scales meter gain and passives.
- **Specials spend Racing Spirit, never Stamina.** Activating a Special consumes `DUEL_SPECIAL_COST` from `racing_spirit_meter` and never reduces Stamina.

---

## 2. Track Profiles (`DUEL_TRACKS`) & Rolling Start

- **Proposed Closed-Loop Track Profiles (Proposed by Nori — NOT locked by Austin):** Instead of a single default loop, `DUEL_TRACKS` defines three closed-loop profiles (`DUEL_DEFAULT_TRACK_ID` defaults to `"street"`), simulated in deterministic ticks of `DUEL_TICK_DT_S`:
  - **`street` (Tight):** Shorter loop (`loop_length_m`), slower tight-street rolling start (`start_speed_mps`), tighter starting gap (`start_gap_m`), higher lap cap (`max_laps`), frequent corners (`corners_per_lap`, `corner_duty`), and tighter contact exposure (`contact_rate_mult`).
  - **`bayshore` (Fast):** Longest high-speed highway loop (`loop_length_m`), fastest rolling start (`start_speed_mps`), wider starting gap (`start_gap_m`), fewer sweeping corners (`corners_per_lap`, `corner_duty`), and lower wall/contact hazard multipliers (`wall_hit_rate_mult`, `contact_rate_mult`).
  - **`ridge` (Technical):** Medium-length mountain-pass loop (`loop_length_m`), mid-pace rolling start (`start_speed_mps`), highest corner density (`corners_per_lap`, `corner_duty`), and slightly elevated guardrail wall risk (`wall_hit_rate_mult`).
- **Rolling Start & Grace Period:** Both cars enter moving at the track's `start_speed_mps`, with the challenger placed `start_gap_m` behind the rival/defender. Gap-based Stamina drain is suppressed while `elapsed_s < grace_period_s` so the challenger is not drained by the starting gap while accelerating into battle. Wall-hit and contact penalties still apply immediately if triggered.

---

## 3. Stamina Drain Rules

### 3.1 Gap Drain (Trailing Car Only)
- Only the **trailing car** takes gap drain (`leader gap drain = 0`).
- **Dead Zone:** While `abs_gap_m <= DUEL_GAP_DEAD_ZONE_M`, gap drain is `0` so side-by-side and bumper-to-bumper fighting does not bleed Stamina.
- **Ramp & Cap:** Past the track's `grace_period_s` and beyond `DUEL_GAP_DEAD_ZONE_M`, the trailing car drains at (`compute_gap_drain_rate`):
  ```
  rate_per_s = min(
      DUEL_GAP_DRAIN_CAP_PER_S,
      DUEL_GAP_DRAIN_BASE_PER_S + DUEL_GAP_DRAIN_SLOPE_PER_M_S * (abs_gap_m - DUEL_GAP_DEAD_ZONE_M)
  )
  ```
- Flat Stamina/sec units (rather than % of max bar) are used intentionally so leveling `stamina_level` strictly increases survival time.

### 3.2 Wall Hit Drain
- Impacts with normal/lateral speed at or below `DUEL_WALL_MIN_IMPACT_MPS` are treated as light wall brushes (`0` Stamina drain).
- Above `DUEL_WALL_MIN_IMPACT_MPS`, drain scales linearly by `DUEL_WALL_DRAIN_PER_MPS` and clamps at `DUEL_WALL_DRAIN_MAX` (`compute_wall_hit_drain`):
  ```
  clamped = min(DUEL_WALL_DRAIN_MAX, max(0.0, impact_speed_mps - DUEL_WALL_MIN_IMPACT_MPS) * DUEL_WALL_DRAIN_PER_MPS)
  drain   = clamped * (1.0 - wall_stamina_penalty_reduction)
  ```
- **Passive Integration:** `wall_stamina_penalty_reduction` comes directly from `RACING_SPIRIT_PASSIVE_BUFFS["slipstream_nerve"]["wall_stamina_penalty_reduction_per_level"]` via `compute_racing_spirit_passives`.
- Wall hits also scrub forward speed by `DUEL_WALL_SPEED_SCRUB_RATIO` (floored at `DUEL_MIN_SPEED_MPS`).

### 3.3 Car-to-Car Contact Drain
- Proximity contact events trigger within `DUEL_CONTACT_PROXIMITY_M` subject to a `DUEL_CONTACT_COOLDOWN_S` cooldown (scaled per track by `contact_rate_mult`).
- Impacts at or below `DUEL_CONTACT_MIN_IMPACT_MPS` are light paint rubs (`0` drain). Above threshold, base impact drain scales by `DUEL_CONTACT_DRAIN_PER_MPS` and clamps at `DUEL_CONTACT_DRAIN_MAX` (`compute_contact_drain`).
- **Who drains on contact (Asymmetric Shared Split — Recommended Default):**
  - **Initiator / trailing car** (rear-ending or diving from behind) takes `DUEL_CONTACT_INITIATOR_SHARE` of the clamped contact drain.
  - **Defending / leading car** takes `DUEL_CONTACT_DEFENDER_SHARE` of the clamped contact drain.
  - **Dead-heat side-by-side contact** (longitudinal separation within dead-heat tolerance) splits `DUEL_CONTACT_EQUAL_SHARE` to both cars.
  - Both cars take a momentary `DUEL_CONTACT_SPEED_SCRUB_RATIO` speed scrub (floored at `DUEL_MIN_SPEED_MPS`).
  - **Justification:** Punishing only the initiator would let a lead car brake-check or block recklessly without risk; punishing only the defender would invite "ram-to-win" exploits by the player. Asymmetric shared drain makes every bump costly for both cars while keeping rear-end ramming a losing Stamina trade for the attacker.

---

## 4. Lap-Cap Fallback Finish

- Normal win condition is **Stamina KO**: the first car whose Stamina bar reaches `<= 0` loses immediately. (If both hit `<= 0` on the same tick via mutual contact, higher remaining/less-negative Stamina wins, then progress gap, then defender.)
- **Lap-Cap Trigger:** If neither bar empties before the leading car reaches the track's `max_laps` (`distance_m >= max_laps * loop_length_m`), `resolve_lap_cap_winner` decides the winner in strict order:
  1. **Remaining Stamina Percentage (`stamina / stamina_bar_max`)** — if the two bars differ by more than `DUEL_STAMINA_PCT_TIE_EPS`, the higher remaining percentage wins. Using percentage rather than raw remaining points prevents a high-`stamina_level` tank from winning timeouts while trailing in battle execution.
  2. **Track Progress / Gap** — if Stamina percentages are within `DUEL_STAMINA_PCT_TIE_EPS`, the car further ahead along the loop (`progress_m`) wins.
  3. **Defender Tiebreak** — on an exact tie in both metrics, the rival/defender retains the win (the challenger must beat the rival to claim victory).

---

## 5. Spline Gap Measurement & Godot Note for Enzo

### 5.1 Closed-Loop Spline Gap Math (`sim/duel.py`)
- Each car's position along the loop of length `L = loop_length_m` has a wrapped spline offset `offset in [0, L)` and an integer `lap_count >= 0`.
- **Total progress:** `progress = lap_count * L + offset`. Signed duel gap is `progress_gap = progress_a - progress_b`.
- **Seam-Wrapped Offset Delta (`wrapped_spline_delta`):** For single-lap relative comparisons across the `0 / L` start-finish seam (gaps smaller than `L / 2`), `(offset_a - offset_b) % L` is wrapped into `[-L/2, +L/2)` so crossing the finish line never causes a sign flip or `±L` spike.

### 5.2 Godot Implementation Note (`Path3D` / `Curve3D`) — Doc Only
For Enzo in Godot:
1. Obtain the active track's total baked length once at course load: `var loop_length_m: float = path_3d.curve.get_baked_length()`.
2. Each physics tick, project each car's world position onto the spline: `var offset: float = path_3d.curve.get_closest_offset(car.global_position)`.
3. Maintain `lap_count: int` per car across ticks using seam-crossing detection:
   - Compute `var delta: float = offset - prev_offset`.
   - If `delta < -0.5 * loop_length_m`: the car wrapped forward across the start/finish seam -> `lap_count += 1`.
   - Else if `delta > 0.5 * loop_length_m`: the car wrapped backward across the seam -> `lap_count -= 1`.
   - Store `prev_offset = offset`.
4. Compute continuous `progress = lap_count * loop_length_m + offset` and signed gap `progress_a - progress_b`. Validate seam wrap, grace-period gating, drain clamps, and lap-cap fallback across all three tracks in `DUEL_TRACKS` against `duel_parity_vectors` in `sim_output/constants_export.json`.
5. **UI note:** The on-screen Stamina bar is a fixed size; map `stamina / stamina_bar_max` to fill that bar. A higher `stamina_level` increases the point pool, not the bar's on-screen length.

---

## 6. Racing Spirit Meter Fill & Specials During Duels

- **Carryover:** If `initial_spirit_carryover` is supplied from a prior battle, starting meter is seeded by `RACING_SPIRIT_PASSIVE_BUFFS["clean_line"]["racing_spirit_carryover_ratio_per_level"]`, capped at `RACING_SPIRIT_METER_MAX`.
- **In-Duel Fill Sources** (all capped at `RACING_SPIRIT_METER_MAX` and scaled by `(1 + RACING_SPIRIT_GAIN_PER_LEVEL * subbranch_level)` via `RACING_SPIRIT_MANEUVER_SUBBRANCH_MAP` / `compute_racing_spirit_meter_gain`):
  1. **Leading Cleanly:** After the track's `grace_period_s`, the current leader gains `DUEL_RACING_SPIRIT_LEAD_RATE_PER_S` per second (scaled by `clean_line` level) on ticks without a wall hit.
  2. **Slipstream / Close Chase:** While trailing within `DUEL_SLIPSTREAM_MAX_GAP_M`, the chaser accumulates slipstream time and triggers `slipstream_tick` (`RACING_SPIRIT_MANEUVER_BASE_GAIN["slipstream_tick"]`) every `DUEL_SLIPSTREAM_TICK_INTERVAL_S`, plus a drafting speed boost `DUEL_SLIPSTREAM_SPEED_BONUS_MPS`.
  3. **Clean Corners / Drifts:** Completing a corner sector without a wall hit can award `clean_drift` (`RACING_SPIRIT_MANEUVER_BASE_GAIN["clean_drift"]`, mapped to `drift_flow`).
  4. **Near-Misses (Barrier Shaves Only — No Traffic):** Closed-loop near misses are **barrier shaves only** (no traffic on closed loops), awarding `near_miss` (`RACING_SPIRIT_MANEUVER_BASE_GAIN["near_miss"]`, mapped to `slipstream_nerve`) at rate `DUEL_NEAR_MISS_PROB_PER_S`.
  5. **Clean Overtakes:** Taking the lead on a tick with no car-to-car contact awards `clean_overtake` (`RACING_SPIRIT_MANEUVER_BASE_GAIN["clean_overtake"]`, mapped to `clean_line`).
- **Special Activation:** When `racing_spirit_meter >= DUEL_SPECIAL_COST` (and no Special is active), activating a Special spends `DUEL_SPECIAL_COST` from `racing_spirit_meter` (never Stamina) for a speed boost of `DUEL_SPECIAL_BASE_SPEED_BONUS_MPS + DUEL_SPECIAL_SPEED_BONUS_PER_LEVEL_MPS * avg_special_level` lasting `DUEL_SPECIAL_DURATION_S`.

---

## 7. Open Questions & Feel Calls ('Austin decides')

All numeric defaults live exclusively in `sim/constants.py`. Across all three proposed tracks in `DUEL_TRACKS`, the 1000-seed Monte Carlo sweep (`sim/duel.py`, `sim_output/duel_sweep_summary.csv`) shows median duels of 78–140 s (~1.3–2.3 min, inside the 1–3 min target), a 0.67–0.75 win rate for a +1 mod-tier advantage, a 0.47–0.55 win rate for even cross-car matchups, and a lap-cap rate of at most 1.1%.

1. **Track profiles (`DUEL_TRACKS` — proposed by Nori, not locked)** — **Austin decides.**
   - *Recommended default:* Keep the three closed-loop profiles (`street`, `bayshore`, `ridge`) with track-specific `loop_length_m`, `max_laps`, `start_speed_mps`, `start_gap_m`, `grace_period_s`, and corner/wall factors.
   - *Alternatives:* Add/remove tracks or unify rolling-start parameters across tracks.
2. **Do closed-loop tracks have traffic? (`DUEL_NEAR_MISS_PROB_PER_S`)** — **Austin decides.**
   - *Recommended default:* **No traffic on closed loops** — `near_miss` events come from barrier shaves only (`DUEL_NEAR_MISS_PROB_PER_S`), keeping closed-loop duels focused on pure 1v1 line craft while reserving civilian traffic for open-expressway stages.
   - *Alternative:* Light civilian traffic on `bayshore` / `street` closed loops.
3. **Contact drain ownership & asymmetry (`DUEL_CONTACT_INITIATOR_SHARE`, `DUEL_CONTACT_DEFENDER_SHARE`, `DUEL_CONTACT_EQUAL_SHARE`)** — **Austin decides.**
   - *Recommended default:* Asymmetric shared drain (`DUEL_CONTACT_INITIATOR_SHARE` > `DUEL_CONTACT_DEFENDER_SHARE`, with `DUEL_CONTACT_EQUAL_SHARE` on dead-heat side-by-side) so rear-end ramming is a net loss for the attacker while blocking stays risky.
   - *Alternatives:* Equal symmetric split or initiator-only drain.
4. **Target duel length & gap-drain ramp (`DUEL_GAP_DEAD_ZONE_M`, `DUEL_GAP_DRAIN_BASE_PER_S`, `DUEL_GAP_DRAIN_SLOPE_PER_M_S`, `DUEL_GAP_DRAIN_CAP_PER_S`)** — **Austin decides.**
   - *Recommended default:* Target ~1–3 minute median duels using the dead zone, linear ramp, and cap in `sim/constants.py`.
   - *Alternatives:* Shorter arcade blitz (<1 min) or longer endurance Wangan battles (3+ min).
5. **Wall & contact impact thresholds and clamps (`DUEL_WALL_MIN_IMPACT_MPS`, `DUEL_WALL_DRAIN_MAX`, `DUEL_CONTACT_MIN_IMPACT_MPS`, `DUEL_CONTACT_DRAIN_MAX`)** — **Austin decides.**
   - *Recommended default:* Ignore light wall brushes / paint rubs below threshold and clamp hard hits so a single physics spike never one-shots a full Stamina bar.
6. **Lap-cap limit & tiebreaker order (`max_laps` per track, `DUEL_STAMINA_PCT_TIE_EPS`)** — **Austin decides.**
   - *Recommended default:* Per-track `max_laps` in `DUEL_TRACKS`, deciding rare timeouts by remaining Stamina % first, then track gap, then defender.
7. **Special activation trigger & cost (`DUEL_SPECIAL_COST`, `DUEL_SPECIAL_DURATION_S`, `DUEL_SPECIAL_BASE_SPEED_BONUS_MPS`)** — **Austin decides.**
   - *Recommended default:* Partial-bar tactical bursts (`DUEL_SPECIAL_COST` < `RACING_SPIRIT_METER_MAX`) lasting `DUEL_SPECIAL_DURATION_S` (auto-fired at threshold in sim; manual player trigger in game vs. full-bar ultimate).
