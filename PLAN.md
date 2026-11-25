# Breakneck — Repo Skeleton & Bootstrap Plan

Owner: **Dominic** (Design Lead)
Target Repo: `github.com/ahoang47/breakneck` (currently empty — 0 commits, no branches)

## Planned Folder Skeleton

Instead of pre-creating empty placeholder directories, each owner initializes their folders when their first approved deliverable lands, with a one-line `README.md` (or `.gitkeep`) and `.gdignore` where needed.

| Folder | Owner | One-Line Purpose / `README.md` or `.gitkeep` Note | `.gdignore`? |
|---|---|---|---|
| `/` (root) | Dominic / Enzo | `AGENTS.md`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `PLAN.md`; **Enzo creates `project.godot` (Godot 4.6)** | No |
| `.github/workflows/` | Dominic | CI checks (`ci.yml`: lean-repo guard + Godot 4.6 headless check + future sim/parity) | No |
| `design/` | Dominic | `GDD.md` and top-level design specs (one-line `README.md` if needed) | Yes |
| `design/systems/` | Silas | Systems & progression design specs referencing `sim/` | Yes (inherits `design/.gdignore`) |
| `sim/` | Silas | Python math/progression model, unit tests, balance tools (`README.md` + `.gdignore`) | Yes |
| `art/` | Akira | Art direction specs & export checklists only — no `.blend`/PSD WIPs (`README.md` + `.gdignore`) | Yes |
| `assets/` | Akira | Game-ready exports for Godot (`cars/`, `env/`, `ui/`, `fonts/`, etc.) tracked via Git LFS | No |
| `scenes/` | Enzo | Godot `.tscn` scenes (`README.md` or `.gitkeep` on project init) | No |
| `scripts/` | Enzo | GDScript gameplay, mirrored `sim/` constants, debug/playtest harness | No |
| `shaders/` | Enzo | Godot `.gdshader` files (GT2 / Racing Lagoon PS1-to-PS2 look, no cel shading) | No |
| `story/` | Nori | Rival bios, world canon, dialogue/barks (`README.md` + `.gdignore`) | Yes |
| `audio/` | Aiden | Game-ready `.ogg`/`.wav` SFX & music exports (LFS); no DAW sets/stems | No |
| `plan/` | Penny | Milestones, task tracking, schedules (`README.md` + `.gdignore`) | Yes |
| `marketing/` | Maya | Store copy, screenshots/press text briefs — no raw video/GIF bloat (`README.md` + `.gdignore`) | Yes |

## Bootstrap Sequence (Pending Austin's Go-Ahead)

1. **Austin reviews & approves** this bootstrap draft package (and resolves top open questions).
2. **Dominic commits root scaffold** to `main`: `AGENTS.md`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `PLAN.md`, `.github/workflows/ci.yml`, `design/GDD.md`, and `design/.gdignore`.
3. **Enzo creates the Godot 4.6 project** (`project.godot`, initial `scenes/`, `scripts/`, `shaders/` layout) on a short-lived bootstrap branch or directly after Austin's sign-off, verifying CI headless check goes green.
4. **Silas, Akira, Nori, Aiden, Penny, Maya** initialize their respective folders only as approved work begins.
