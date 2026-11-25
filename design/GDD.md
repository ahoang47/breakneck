# Breakneck — Game Design Document (Locked Core Outline)

> **Status:** Bootstrap Outline (Locked Core Only). Core loop locked 2026-11-25 (Racing Lagoon structure, TXR-style races).
> **Lead:** Dominic (`design/`) | **Final Authority:** Austin Hoang
> **Rule:** Never invent balance numbers, rival names, or unapproved plot here. Numeric formulas live in `sim/` (Silas). Open decisions are tagged `[OPEN]`.

---

## First Playable Target

**Decided 2026-11-25 (Austin):** The first vertical slice is a small overworld stretch that drives into one closed-loop track, one car, and one Stamina duel against a single rival. Work happens on short-lived `feat/*` or `proto/*` branches off `main`, deleted after merge.

- `[OPEN]` Overworld stretch size. (Dominic [layout] · Enzo [engine] · Akira [art])

---

## 1. High Concept & Pillars *(Owner: Dominic)*

- **Title:** *Breakneck*
- **Engine:** Godot 4.6
- **Premise:** Night street racer whose game loop follows Racing Lagoon (free-roam overworld, races on a limited number of closed-loop tracks) and whose races play closer to Tokyo Xtreme Racer / Shutoko Battle (Stamina duels against rivals).
- **Design Guardrails:**
  - Immediate playable hook (first 3 minutes get the player into a Stamina duel on a closed-loop track).
  - Fast retry on loss/restart; zero sluggish transitions.
  - All tuning parameters externalized in `sim/` and hot-reloadable/mirrored in Godot.
- `[OPEN]` What further Ryu Ga Gotoku / Racing Lagoon elements (beyond the locked core loop, visual tone, and RPG-style progression) are in scope for MVP? (e.g., off-car exploration vs menu/PA hubs, encounter presentation). (Dominic; Austin has final say.)

---

## 2. Core Loop *(Owner: Dominic)*

**Locked Core (decided 2026-11-25):**
Breakneck's game loop follows Racing Lagoon. The player free-roams an overworld and races on a limited number of closed-loop tracks. The races themselves play closer to Tokyo Xtreme Racer: head-to-head **Stamina duels**.

Loop, in order:
1. Free-roam the overworld.
2. Enter one of a limited set of closed-loop tracks.
3. Trigger a rival Stamina duel on that track.
4. Run a high-stakes Stamina duel (risk/return maneuvers).
5. Earn progression/payouts; invest in the Driver Tree and Car Trees.
6. Return to the overworld and take on tougher rivals.

The game is **not** one continuous expressway. Cruising and dueling do not share a single unbounded road; roaming and racing are separate spaces.

**To Be Detailed (Do Not Invent Values Yet):**
- `[OPEN]` Overworld size, layout, and what the player can do there besides reaching tracks. (Nori [story/rivals] · Enzo [engine] · Akira [art] · Dominic [layout])
- `[OPEN]` Track count, and how each track is entered from the overworld. (Enzo [engine] · Dominic [layout] · Akira [art])
- `[OPEN]` How rivals are placed or encountered across the overworld and tracks. (Nori [story/rivals])
- `[OPEN]` Balance numbers that fall out of this loop (payouts, travel vs race pacing). (Silas [sim/numbers])

---

## 3. Stamina Duels *(Owners: Dominic [feel/rules] · Silas [sim/math] · Enzo [engine])*

**Locked Core:**
- **TXR-style duels:** Head-to-head duels against rivals on closed-loop tracks using a **Stamina bar** that reads as a health bar.

**To Be Detailed (Do Not Invent Values Yet):**
- Win/loss conditions, Stamina drain triggers (distance gap, lead/chase pressure, clean vs sloppy driving, collisions), and comeback/rubberband rules.
- How a battle is initiated (from the overworld, on the track, or both) and how battles end (Stamina depletion, finish gate, or forfeit).
- `[OPEN]` Exact Stamina drain model: pure distance-gap drain, active attack/defense maneuvers, or hybrid? (Silas [sim/numbers] · Dominic [feel/rules])
- `[OPEN]` How traffic, wall impacts, and cornering mistakes interact with Stamina loss and battle pacing. (Silas [sim/numbers] · Enzo [engine] · Dominic [feel])
- `[OPEN]` Battle length target (average duel duration) and rematch/retry flow. (Silas [sim/numbers] · Dominic [feel])

---

## 4. Driver Tree *(Owners: Silas [math/design/systems/] · Dominic [design/])*

**Locked Core — Three Branches:**
1. **Technique:** Gates which cars the driver can unlock/handle, and **seeds car Mastery**.
2. **Spirit:** Boosts **Spirit gain per maneuver** and holds **passive buffs**.
3. **Stamina:** Raises the car's Stamina points (its pool). There is one Stamina: the duel bar and this stat. The Stamina bar is always the same on-screen size and reads as a health bar. The point pool is normalized to that fixed size; the stat does not make the bar visually bigger.

**To Be Detailed:**
- Progression currency/XP source, node/rank structure, and how Driver Technique gates car tiers or classes.
- Exact list of maneuvers that generate Spirit and categories of passive buffs in the Spirit branch.
- `[OPEN]` Is Driver progression XP-based (earned per duel/maneuver), cash/rep-based, or branch-specific?
- `[OPEN]` Can Driver Tree points be respec'd, or is growth purely additive?

---

## 5. Per-Car Trees *(Owners: Silas [math/design/systems/] · Dominic [design/] · Enzo [data/garage])*

**Locked Core — Four Pillars per Car:**
1. **Base Stats:** Each car's baseline driving/duel identity.
2. **Specials:** Active abilities fueled by a **separate Spirit meter** (distinct from the Stamina bar).
3. **Mod Tiers:** Staged vehicle upgrade tiers.
4. **Mastery:** Per-car mastery progression, **seeded by Driver Technique**.

**To Be Detailed:**
- How Specials activate during a duel (input, cooldown/cost on the Spirit meter, risk/return tradeoff).
- Mod tier structure (engine/handling/weight/aero or unified tier unlocks) and whether mods alter visuals/audio.
- How Driver Technique's "seed" translates into starting or cap bonuses for a newly acquired car's Mastery.
- `[OPEN]` Scope of car roster for MVP (number of cars/classes) and how Specials differ per car vs per archetype.
- `[OPEN]` Does car Mastery unlock passives, stat multipliers, Specials, or all three?

---

## 6. World, Tracks & Handling Feel *(Owners: Enzo [physics/engine] · Dominic [layout/feel] · Silas [params])*

**Locked Core:**
- **World structure:** A free-roam overworld plus a limited number of closed-loop race tracks (see Core Loop). Not a single continuous expressway.
- **Playtest & Debug Harness:** Debug HUD, reproducible state token, headless sim/run parity.

**To Be Detailed:**
- `[OPEN]` Physics model: arcade-sim grip/drift hybrid, Tokyo Xtreme Racer-style heavy high-speed stability, or Racing Lagoon-style drift-focused? (Enzo [engine] · Dominic [feel] · Silas [params])
- `[OPEN]` Overworld and track layout language, traffic density on each, and whether PA (parking area) or other hubs exist. Size and track count stay unset — see Core Loop. (Enzo [engine] · Dominic [layout] · Akira [art] · Silas [params])

---

## 7. Art & UI Direction *(Owner: Akira [art/, assets/])*

**Locked Core:**
- **Visual Style:** Gran Turismo 2 / Racing Lagoon PS1-to-PS2 look — **strictly NO cel shading**.

**To Be Detailed by Akira:**
- Render pipeline (resolution, vertex snap/affine or PS2-era crispness, texture filtering, lighting/reflections, post-process, HUD typography & color coding).
- `[OPEN]` Target internal render resolution & PS1-vs-PS2 fidelity balance (e.g. PS1 jitter/dither vs cleaner early-PS2/GT2-to-GT3 shading).
- `[OPEN]` UI layout for dual bars (Stamina bar + separate Spirit meter), speedo/tach, and Driver/Car trees.
- `[OPEN]` Art scope for the overworld vs the closed-loop tracks (no size or track count implied). (Akira [art])

---

## 8. Narrative, World & Rivals *(Owner: Nori [story/])*

**Locked Core (structure only):** Rivals and story sit on the Racing Lagoon-style loop (overworld free-roam, races on closed-loop tracks). No plot, roster, or rival names are locked here.

**To Be Detailed by Nori (pending Austin's direction):**
- Rival hierarchy (wanderers, team leaders, bosses), encounter triggers, pre/post-battle barks, and world tone.
- **Decided 2026-11-25:** Breakneck reuses much of Midnight Apex's narrative. Its characters and structure carry over, retooled for Stamina duels, the driver tree and the per-car trees. Nori owns the retool.
- `[OPEN]` Rival roster size and progression structure for vertical slice / MVP. (Nori)
- `[OPEN]` How rivals are encountered in the overworld vs on tracks. (Nori)

---

## 9. Audio & Music *(Owner: Aiden [audio/])*

**To Be Detailed by Aiden:**
- Engine/exhaust notes, turbo/blow-off, collision/scrape impact, UI/Stamina-drain cues, overworld and track ambience, and BGM direction.
- `[OPEN]` Music genre/tempo direction (eurobeat, PS1/PS2 fusion-jazz/techno like Racing Lagoon/GT2, dark synth, or dynamic battle layers).

---

## 10. Production, QA & Release *(Owners: Penny [plan/] · Maya [marketing/])*

- **Penny (`plan/`):** Milestone schedule, vertical-slice scope (see First Playable Target), playtest checklists.
- **Maya (`marketing/`):** Positioning, store/social copy, media capture guidelines (keep heavy renders/MP4s off git).
