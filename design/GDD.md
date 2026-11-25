# Breakneck — Game Design Document (Locked Core Outline)

> **Status:** Bootstrap Outline (Locked Core Only)
> **Lead:** Dominic (`design/`) | **Final Authority:** Austin Hoang
> **Rule:** Never invent balance numbers, rival names, or unapproved plot here. Numeric formulas live in `sim/` (Silas). Open decisions are tagged `[OPEN]`.

---

## First Playable Target (decided 2026-11-25)

The first vertical slice is one night-expressway segment, one car, and one SP duel against a single rival. Work happens on short-lived `feat/*` or `proto/*` branches off `main`, deleted after merge.

---

## 1. High Concept & Pillars *(Owner: Dominic)*

- **Title:** *Breakneck*
- **Engine:** Godot 4.6
- **Premise:** Tokyo Xtreme Racer / Shutoko Battle-style night-expressway street racer featuring SP-bar duels against rivals.
- **Core Loop:** Cruise night expressway → trigger rival SP battle → high-stakes expressway duel (risk/return maneuvers) → earn progression/payouts → invest in Driver Tree & Car Tree → challenge tougher rivals.
- **Design Guardrails:**
  - Immediate playable hook (first 3 minutes get the player straight onto the expressway and into an SP duel).
  - Fast retry on loss/restart; zero sluggish transitions.
  - All tuning parameters externalized in `sim/` and hot-reloadable/mirrored in Godot.
- `[OPEN]` What Ryu Ga Gotoku / Racing Lagoon elements (if any beyond visual tone and RPG-style progression) are in scope for MVP? (e.g., off-car exploration vs menu/PA hubs, encounter presentation).

---

## 2. SP Battles *(Owners: Dominic [feel/rules] · Silas [sim/math] · Enzo [engine])*

**Locked Core:**
- **TXR-style SP Battles:** Head-to-head duels against rivals on the night expressway using an **SP bar** (Spirit/Stamina Points duel health, sized by Driver Stamina).

**To Be Detailed (Do Not Invent Values Yet):**
- Win/loss conditions, SP drain triggers (distance gap, lead/chase pressure, clean vs sloppy driving, collisions), and comeback/rubberband rules.
- How battle initiation works on the expressway (e.g., headlight flash / proximity trigger) and how battles end (SP depletion, finish gate, or forfeit).
- `[OPEN]` Exact SP drain model: pure distance-gap drain, active attack/defense maneuvers, or hybrid?
- `[OPEN]` How traffic, wall impacts, and cornering mistakes interact with SP loss and battle pacing.
- `[OPEN]` Battle length target (average duel duration in seconds/km) and rematch/retry flow.

---

## 3. Driver Tree *(Owners: Silas [math/design/systems/] · Dominic [design/])*

**Locked Core — Three Branches:**
1. **Technique:** Gates which cars the driver can unlock/handle, and **seeds car Mastery**.
2. **Spirit:** Boosts **Spirit gain per maneuver** and holds **passive buffs**.
3. **Stamina:** **Sizes the SP bar**.

**To Be Detailed:**
- Progression currency/XP source, node/rank structure, and how Driver Technique gates car tiers or classes.
- Exact list of maneuvers that generate Spirit and categories of passive buffs in the Spirit branch.
- `[OPEN]` Is Driver progression XP-based (earned per duel/maneuver), cash/rep-based, or branch-specific?
- `[OPEN]` Can Driver Tree points be respec'd, or is growth purely additive?

---

## 4. Per-Car Trees *(Owners: Silas [math/design/systems/] · Dominic [design/] · Enzo [data/garage])*

**Locked Core — Four Pillars per Car:**
1. **Base Stats:** Each car's baseline driving/duel identity.
2. **Specials:** Active abilities fueled by a **separate Spirit meter** (distinct from the SP battle bar).
3. **Mod Tiers:** Staged vehicle upgrade tiers.
4. **Mastery:** Per-car mastery progression, **seeded by Driver Technique**.

**To Be Detailed:**
- How Specials activate during a duel (input, cooldown/cost on the Spirit meter, risk/return tradeoff).
- Mod tier structure (engine/handling/weight/aero or unified tier unlocks) and whether mods alter visuals/audio.
- How Driver Technique's "seed" translates into starting or cap bonuses for a newly acquired car's Mastery.
- `[OPEN]` Scope of car roster for MVP (number of cars/classes) and how Specials differ per car vs per archetype.
- `[OPEN]` Does car Mastery unlock passives, stat multipliers, Specials, or all three?

---

## 5. Expressway & Handling Feel *(Owners: Enzo [physics/engine] · Dominic [layout/feel] · Silas [params])*

- **Setting:** Night expressway loop/network (Shutoko-inspired).
- **Playtest & Debug Harness:** Debug HUD, reproducible state token, headless sim/run parity.
- `[OPEN]` Physics model: arcade-sim grip/drift hybrid, Tokyo Xtreme Racer-style heavy high-speed stability, or Racing Lagoon-style drift-focused?
- `[OPEN]` Expressway scope for MVP: one loop/segment vs multi-district expressway, traffic density, PA (parking area) hubs.

---

## 6. Art & UI Direction *(Owner: Akira [art/, assets/])*

**Locked Core:**
- **Visual Style:** Gran Turismo 2 / Racing Lagoon PS1-to-PS2 look — **strictly NO cel shading**.

**To Be Detailed by Akira:**
- Render pipeline (resolution, vertex snap/affine or PS2-era crispness, texture filtering, lighting/reflections, post-process, HUD typography & color coding).
- `[OPEN]` Target internal render resolution & PS1-vs-PS2 fidelity balance (e.g. PS1 jitter/dither vs cleaner early-PS2/GT2-to-GT3 shading).
- `[OPEN]` UI layout for dual bars (SP battle bar + separate Spirit meter), speedo/tach, and Driver/Car trees.

---

## 7. Narrative, World & Rivals *(Owner: Nori [story/])*

**To Be Detailed by Nori (pending Austin's direction):**
- Rival hierarchy (wanderers, team leaders, bosses), encounter triggers, pre/post-battle barks, and world tone.
- `[OPEN]` Tone & narrative structure: grounded street-racer mystery (TXR) vs surreal/melodramatic street RPG (Racing Lagoon) vs RGG-style side stories?
- `[OPEN]` Rival roster size and progression structure for vertical slice / MVP.

---

## 8. Audio & Music *(Owner: Aiden [audio/])*

**To Be Detailed by Aiden:**
- Engine/exhaust notes, turbo/blow-off, collision/scrape impact, UI/SP-drain cues, night expressway ambience, and BGM direction.
- `[OPEN]` Music genre/tempo direction (eurobeat, PS1/PS2 fusion-jazz/techno like Racing Lagoon/GT2, dark synth, or dynamic battle layers).

---

## 9. Production, QA & Release *(Owners: Penny [plan/] · Maya [marketing/])*

- **Penny (`plan/`):** Milestone schedule, vertical-slice scope, playtest checklists.
- **Maya (`marketing/`):** Positioning, store/social copy, media capture guidelines (keep heavy renders/MP4s off git).
