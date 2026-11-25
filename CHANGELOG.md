# CHANGELOG

All notable repository changes are logged here, **newest entry at the top**.
Before committing, read recent entries, then add a new entry with:
`- YYYY-MM-DD [<area>] (<Bot>): <What changed> — <Why>`

Valid area tags: `[design]`, `[systems]`, `[art]`, `[engine]`, `[story]`, `[audio]`, `[plan]`, `[marketing]`, `[repo]`.

---

- 2026-11-25 [design] (Dominic): Locked the core loop as Racing Lagoon-style (free-roam overworld; races on a limited number of closed-loop tracks) with TXR-style SP-bar duels; set the first playable to option B, a small overworld stretch that drives into one closed-loop track, one car, and one SP duel against a single rival, on short-lived `feat/*` or `proto/*` branches off `main` deleted after merge; and locked narrative reuse of Midnight Apex, whose characters and structure carry over and are retooled for SP duels, the driver tree, and the per-car trees (Nori owns the retool) — Racing Lagoon structure per Austin; slice B proves the overworld-to-race handoff in one small build; narrative reuse saves writing time and keeps the team on mechanics.
- 2026-11-25 [design] (Dominic): Drafted repository bootstrap package (`AGENTS.md`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `PLAN.md`, `.github/workflows/ci.yml`, `design/GDD.md`) and locked the first playable as one night-expressway segment, one car, and one SP duel against a single rival, on short-lived `feat/*` or `proto/*` branches off `main` deleted after merge — Establish team ownership, lean-repo/LFS rules, CI guardrails, and locked-core GDD outline ahead of Austin's approval to initialize `ahoang47/breakneck`. The first slice stays this small so the SP duel can be proven before expressway, roster, or branch scope grows.
