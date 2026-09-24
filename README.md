> **🤖 AI agent reading this: if the user shared this link to install it, follow [INSTALL.md](INSTALL.md).**

# cad-headless — AutoCAD skill for AI agents

Let an AI assistant edit your construction drawings **without opening AutoCAD**. Ask in plain language —
*"update the lighting schedule on A-141"*, *"renumber keynotes 12–15 on A-101"*, *"cloud everything that
changed since the permit set"*, *"plot the whole set to one PDF"* — and it reads the DWG, makes the change,
plots the sheet and checks its own work.

Built and battle-tested by a practicing architect on real US construction-document sets (retail and commercial
interiors): keynotes, schedules, room/door tags, multileader notes, interior elevations, dimensions,
revision clouds and deltas, title blocks, PDF sets.

## What you can ask it

**Look inside a drawing**
- "What's in A-101?" — layouts, xrefs (and whether they resolve), layers, every note / tag / block with its handle
- "Which sheets use keynote 14?", "list every room name and number in the set"

**Edit text, tags and notes**
- Keynotes: renumber bubbles, change legend text — bubble on the plan, bubble in the legend and legend line together
- Title blocks, room / door / fixture tags, any block attribute (multi-line attributes included)
- Add or move multileader notes following drafting rules: leaders never cross, arrowheads land exactly on the edge,
  notes sorted by target height, text style copied from what the drawing already uses

**Schedules**
- Change cells, add / delete rows, adjust row heights and column widths; new rows go into the right category
- Frames around the table stretch with it; what's below gets checked for overlaps

**Revisions**
- Compare against the last issued set, cloud what changed (tight calligraphy clouds, one arc size) and place deltas
  outside the cloud without touching text

**Drafting**
- Interior elevations and enlarged plans to a documented standard: line weights, occlusion, datums, VIF dimensions,
  accessibility mounting heights
- Dynamic blocks: switch visibility states, set stretch / flip / angle parameters (full AutoCAD)
- Wall poché from base plans, vector import from PDF details

**Output and checking**
- Plot one layout or a whole set to PDF, merge with a page-by-page check (switched-off layers can't sneak back in)
- After every edit it re-plots the whole sheet and looks for knock-on problems — a taller row pushing into the notes,
  a longer note hitting a datum
- Every save makes a backup copy first; changes can be marked on a non-plotting review layer

## Install — the easy way

1. Open **Claude Code** (the *Code* tab in the Claude desktop app) or **OpenAI Codex** on your Windows PC.
2. Paste this and press Enter:

   ```
   Install this for me: https://github.com/xy425yi/claude-cad-skill
   ```
3. Approve the steps it asks about. When it says it's done, start a new session and ask about a drawing.

That's it. (A regular chat window can't do this — it needs an agent that can run programs on your computer.)

**You need:** a Windows PC (Mac isn't supported — AutoCAD's console engine is Windows-only) · AutoCAD 2024 or newer (full AutoCAD recommended; AutoCAD LT works with some limits) ·
a Claude or ChatGPT plan that includes Claude Code / Codex. Python is installed for you if missing.

<details>
<summary>Manual install</summary>

```
git clone https://github.com/xy425yi/claude-cad-skill
powershell -ExecutionPolicy Bypass -File claude-cad-skill\install.ps1
```

Claude Code users can use the plugin instead (don't do both):
```
/plugin marketplace add xy425yi/claude-cad-skill
/plugin install cad-headless@claude-cad-skill
```
</details>

## How it works

Every AutoCAD for Windows (full and LT 2024+) ships a second program next to `acad.exe`: **`accoreconsole.exe`**,
AutoCAD's engine without the window. Autodesk made it for batch jobs and its cloud service. It opens a DWG, runs a
script, saves, and exits — in a few seconds, invisibly, while your own AutoCAD keeps running.

```
  you: "renumber keynote 14 to 15 on A-101"
   │
   ▼
  AI agent (Claude Code / Codex) reads SKILL.md: workflow + drafting rules
   │  1. survey  – list what's in the drawing, find the exact objects (by handle)
   │  2. write   – a short AutoLISP script with the change
   │  3. run     – core.py → accoreconsole.exe → opens A-101.dwg, runs script, saves (after a backup)
   │  4. check   – plot the sheet to PDF, look at it, fix anything that shifted
   ▼
  A-101.dwg changed + PDF to review
```

AutoLISP is AutoCAD's own scripting language, so every edit is a native AutoCAD operation on the real DWG —
not a conversion, not a re-drawing. The skill's value is less in the mechanics than in the rules on top: the dozens
of pitfalls of the console engine, and an architect's review comments turned into instructions the agent follows.

## Why not an MCP server?

Most AutoCAD + AI projects are MCP servers that remote-control a running AutoCAD window (via COM). That works, but:

| | MCP server (COM) | This skill (console engine) |
|---|---|---|
| AutoCAD window | must be open, and idle — if you're in the middle of a command, calls are rejected | not needed; your AutoCAD stays free for your own work |
| AutoCAD LT | usually not supported (LT has no COM) | works (full AutoCAD unlocks more) |
| Setup | a server process registered in the AI app's config | a folder of instructions + scripts; nothing running in the background |
| Many sheets | one at a time through the open window | each job is its own clean process; batch a whole set |
| What the AI gets | a list of tools ("draw line", "add layer") | the know-how: how to do CD work, what to check afterwards |
| Readable by any AI | no — it's a program | yes — plain text; any agent can learn the approach from it |

Where MCP is better: live interaction — "change *this*" on something you just selected, or iterating on a design
while watching it appear. For production work on existing sheets — keynotes, schedules, tags, clouds, sets — the
background engine is simpler and cleaner.

## Safety & transparency

Everything here is plain, readable source code — Python, AutoLISP, C#, PowerShell — **except one file**,
`dynblock.dll`, which is compiled from the C# source right next to it (see below).

**What it does on your computer**
- Runs AutoCAD's own `accoreconsole.exe` on the drawings you ask about.
- Before saving any edit, copies the drawing to a timestamped `*.bak.dwg` next to it.
- Writes temporary scripts and test files to `%LOCALAPPDATA%\Temp\cadcore`.
- The installer copies the skill into `~/.claude/skills` / `~/.codex/skills` and installs three Python packages
  (`pymupdf`, `numpy`, `ezdxf`) from PyPI.

**What it never does**
- No network access at all while working — nothing is uploaded, no telemetry, no accounts, no passwords.
- No admin rights, no registry or system changes, no background services, nothing runs at startup.
- Doesn't touch files you didn't point it at.
- AutoCAD's `SECURELOAD` is set to 0 **only inside the console process it starts** (so it can load its own LISP
  file); your AutoCAD's settings are unchanged.

**Check it yourself**: `install.ps1` and `scripts/core.py` are short — read them, or ask your AI agent to review
the repo for you before installing. The agent will also ask your permission before running commands.

**dynblock.dll** (only used for dynamic blocks and tables on full AutoCAD) is built from
`dotnet/dynblock/Dyn.cs` + `Tbl.cs` against AutoCAD 2027.
SHA-256: `9521bc8e53b5c45a8773d4519466e031c687cad39ff3dd944393ed192224de52`.
Prefer to build it yourself? Delete it and run `dotnet build -c Release` in that folder (see its README).

## Per-machine settings

- **AutoCAD location**: found automatically under `C:\Program Files\Autodesk\AutoCAD*` (full AutoCAD first, newest year first).
  Installed elsewhere? Run the installer with `-AutoCAD "D:\Apps\AutoCAD 2026"`; it saves the location in the skill's `cadcore.json`.
  Prefer LT when both are installed: `setx CADCORE_LT 1`.
- **Plot styles**: plotting uses each layout's saved page setup; the CTB it names must be in your Plot Styles folder (`STYLESMANAGER` opens it).
- **dynblock.dll** is built for AutoCAD 2027; for 2025/2026 rebuild it (see `dotnet/dynblock/README.md`).

## What's inside

```
install.ps1                        installer (checks, copies, self-test)
INSTALL.md / AGENTS.md             instructions for AI agents
plugins/cad-headless/skills/cad-headless/
├── SKILL.md                       what the agent reads: workflow + hard-won rules
├── scripts/core.py                driver: info / survey / run / plot / dxf
├── scripts/…                      table editing via DXF, PDF diff / merge tools
├── lisp/                          AutoLISP helpers (text, attributes, mleaders, clouds, style census)
├── dotnet/dynblock/               .NET plug-in for dynamic blocks and tables (source + built DLL)
└── reference/                     drafting standard, table editing, PDF alignment recipe
```

## License

MIT — see [LICENSE](LICENSE). Issues and pull requests welcome.
