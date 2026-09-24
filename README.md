> **🤖 AI agent reading this: if the user shared this link to install it, follow [INSTALL.md](INSTALL.md).**

# cad-headless — AutoCAD skill for AI agents

Let an AI assistant edit your construction drawings **without opening AutoCAD**. Ask in plain language —
*"update the lighting schedule on A-141"*, *"renumber keynotes 12–15 on A-101"*, *"cloud everything that
changed since the permit set"*, *"plot the whole set to one PDF"* — and it reads the DWG, makes the change,
plots the sheet and checks its own work.

Built and battle-tested by a practicing architect on real US construction-document sets (retail and commercial
interiors): keynotes, schedules, room/door tags, multileader notes, interior elevations, dimensions,
revision clouds and deltas, title blocks, PDF sets.

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

Every AutoCAD install ships `accoreconsole.exe`, AutoCAD's engine without a user interface. The skill gives the
agent a small Python driver and an AutoLISP library to run scripts through it: each job opens the DWG in a
separate process, edits, saves and exits in a few seconds. Your AutoCAD window isn't touched.

On top of the mechanics, the skill carries drafting rules learned from review rounds — leaders never cross,
arrowheads land on edges, copy the drawing's own text styles, tight revision clouds, check what a change pushed
out of place — so the output reads like the rest of your set.

## How is this different from an AutoCAD MCP server?

MCP servers remote-control an AutoCAD window that has to be open and idle, and mostly expose drawing primitives
("draw a line, add a layer"). This skill runs AutoCAD's console engine in the background — no window, your AutoCAD
stays free — and is aimed at **production CD work on existing sheets**: keynotes, schedules, tags, notes and
leaders, revision clouds, plotting and checking sets, with an architect's review rules built in.

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
