# Changelog

## 1.3.5 — 2026-10-01

- Support (GitHub Issues) and privacy (README safety section) links for the directory listing.

## 1.3.4 — 2026-10-01

- Display name "CAD Edit" and a homepage link for the directory listing.

## 1.3.3 — 2026-10-01

- No environment variables anywhere: `core.py` takes the AutoCAD location and LT preference only from `cadcore.json`
  (written by the installer), and the temp folder from the standard library. `ACCORECONSOLE`, `CADCORE_SEARCH` and
  `CADCORE_LT` are gone; use `install.ps1 -AutoCAD <folder>` and `-PreferLT` instead.
- The installer only accepts `accoreconsole.exe` files with a valid Autodesk code signature.

## 1.3.2 — 2026-10-01

- `core.py` no longer copies the whole environment when starting accoreconsole (the child process simply inherits it);
  the installer's help message no longer contains a URL. Nothing in the plugin reads credentials or sends data anywhere.

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
