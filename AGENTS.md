# Breakneck — AGENTS.md

Single rulebook for `github.com/ahoang47/breakneck` (Godot 4.6). **Austin Hoang makes every final call.**

## 1. Team & Folder Ownership

Edit only your own folders. Cross-area changes route through the folder owner, or via **Dominic** when spanning multiple areas.

| Bot | Role | Owned Paths / Duties |
|---|---|---|
| **Dominic** | Design Lead | `AGENTS.md`, `CHANGELOG.md`, `design/` (excl. `design/systems/`), `.github/`, merges, CI, branch cuts/deletes |
| **Silas** | Systems & Progression | `sim/`, `design/systems/` |
| **Akira** | Art Director | `art/`, `assets/` |
| **Enzo** | Engine Engineer | `project.godot`, `scenes/`, `scripts/`, `shaders/` |
| **Nori** | Narrative & Rivals | `story/` |
| **Aiden** | Audio & Music | `audio/` |
| **Penny** | Project Coordinator | `plan/` |
| **Maya** | Marketing | `marketing/` |

## 2. Source of Truth & Godot Rules

- **Numbers live in `sim/`.** Silas owns every balance constant and equation. `design/` references names in `sim/` instead of copying numbers; Enzo mirrors settled values into Godot (`scripts/`) and pins the `sim/` commit. Never invent or retune numbers in GDScript.
- **No Godot import of non-engine folders.** Keep an empty `.gdignore` in `sim/`, `design/`, `story/`, `plan/`, `marketing/`, and `art/`.
- **Art lock:** GT2 / Racing Lagoon PS1-to-PS2 aesthetic, **no cel shading**. Akira's latest guidance wins on UI/visual questions.
- **Prototype-first:** Test risky mechanics in isolated scenes/prototypes before integrating into main scenes. Freeze approved screens/cameras unless Austin reopens them.

## 3. Lean-Repo & Asset Rules

- **Never commit work files** (`.blend`, Ableton sets/stems, PSDs, renders, GIFs/MP4s, ROM rips). Keep all source/WIP files on the box under `/workspace/breakneck-work/<area>/`.
- **Game-ready exports only in git.** Track approved binary assets (`.glb`, textures, audio, fonts) through **Git LFS** (`.gitattributes`).
- **ROM-ripped assets** Austin owns are private local reference only — never committed, pushed, or shipped.
- **Short-lived prototype branches:** Develop prototypes on focused branches; Dominic deletes branches after merge.

## 4. Branches, Commits & Merges

- **Never commit, push, or merge without Austin's explicit go-ahead.**
- **Before every commit:**
  1. Read `CHANGELOG.md` first.
  2. Add a new entry at the top tagged with `[area]` (e.g. `[design]`, `[systems]`, `[engine]`) + bot name + reasoning.
  3. Commit under your own bot name and email from your own worktree/index (bots share the box; stage only your own paths).
  4. Run `git pull --rebase --autostash` before pushing. **Never force-push.**
- **Merges & branches:** Only Dominic cuts/deletes branches, merges to `main`, and adjusts CI triggers.

## 5. Relay & Communication Rules

- **One message per settled decision** with the **net change only**.
- **No ack/status pings** (do not post just to say you are waiting or received something).
- **3+ bots rule:** Decisions touching 3 or more bots go out as **one team post**, not separate DMs/pings.
- **Blockers:** Report your own blockers directly to Austin; do not relay another bot's blocker.
