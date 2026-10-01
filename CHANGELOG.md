# Changelog

## 1.3.1 — 2026-10-01

- Added a plugin icon for the directory listing.

## 1.3.0 — 2026-10-01

- The repository root is now the plugin (`.claude-plugin/plugin.json` + `skills/cad-edit/`), so it can be submitted and
  installed without a sub-path. The marketplace (`/plugin marketplace add xy425yi/claude-cad-skill`) is unchanged.

## 1.2.0 — 2026-09-24

- Renamed the plugin and skill from `cad-headless` to **`cad-edit`**. Install with `/plugin install cad-edit@claude-cad-skill`;
  `install.ps1` moves an install under the old name out of the skills folder so it doesn't load twice.

## 1.1.0 — 2026-09-24

- Plotting: the agent asks which plot style (CTB) to use before plotting. New `core.py ctb <dwg>` lists each layout's
  CTB, whether it's installed, and all available CTBs; `plot --ctb <name>` overrides it for one plot without changing
  the drawing; `plot` stops if the layout's CTB file is missing (`--allow-missing-ctb` to override).

## 1.0.0 — 2026-09-24

First public release.

- `cad-headless` skill: read, edit and plot DWG files through AutoCAD's accoreconsole.exe with AutoLISP (full AutoCAD by default, AutoCAD LT supported).
- `dynblock.dll` (.NET, full AutoCAD): dynamic-block states/parameters, table editing, xref paths.
- Drafting standard for interior elevations and enlarged plans; table editing guide; PDF alignment recipe.
- `install.ps1` one-step installer for Claude Code and Codex, with self-test; `INSTALL.md` / `AGENTS.md` for AI agents.
- Claude Code plugin marketplace (`/plugin marketplace add xy425yi/claude-cad-skill`).
