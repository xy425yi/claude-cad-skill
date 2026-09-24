# INSTALL — instructions for the AI agent

**If a user gave you this repository's link and asked you to install it (or just pasted the link), follow these
steps.** The user may not be technical: do the work yourself, explain briefly in their language what you're doing,
and ask before anything that needs their approval.

This works in agents that can run commands on the user's Windows PC — **Claude Code** (CLI, or the Code tab of the
Claude desktop app), **OpenAI Codex**, or similar. If you are a chat assistant without a terminal, tell the user to
open Claude Code or Codex and paste the link there.

**Windows only.** The skill drives `accoreconsole.exe`, AutoCAD's console engine, which Autodesk ships only
with AutoCAD for Windows. On a Mac (AutoCAD for Mac included) or Linux, don't install anything: tell the user
plainly that it needs a Windows PC with AutoCAD 2024+ (a Windows virtual machine with AutoCAD also works).

## Steps

1. **Get the repo** into the user's home folder (not inside their project):
   ```
   git clone https://github.com/xy425yi/claude-cad-skill "$HOME/claude-cad-skill"
   ```
   (`$HOME` works in PowerShell and Git Bash; in cmd.exe use `%USERPROFILE%`.) If it already exists, `git pull` inside it.
   No git? Download `https://github.com/xy425yi/claude-cad-skill/archive/refs/heads/main.zip` and unzip it there.

2. **Read `install.ps1`** (it's short) so you can tell the user what it will do, then run it:
   ```
   powershell -ExecutionPolicy Bypass -File "$HOME/claude-cad-skill/install.ps1"
   ```
   It finds AutoCAD, checks Python, installs `pymupdf numpy ezdxf`, copies the skill into `~/.claude/skills`
   (and `~/.codex/skills` if Codex is installed) and runs a self-test on a throwaway drawing.

3. **Read the result and fix what it reports**, then re-run:
   - **`ONLY AutoCAD LT found`** (a warning, but important) → ask the user: *"Do you also have the full AutoCAD
     installed somewhere, e.g. on another drive?"* If yes, re-run with `-AutoCAD "<that folder>"` (the AutoCAD
     install folder or its parent both work). The installer saves the location — no environment variable needed.
   - *AutoCAD not found* → ask where AutoCAD is installed and re-run with `-AutoCAD "<folder>"`.
     No AutoCAD 2024+ at all → the skill can't work; tell the user.
   - *Python not found* → ask the user, then `winget install -e --id Python.Python.3.12`. The new Python is only
     visible after the **whole app is quit and reopened** — ask the user to do that, then continue from step 2.
   - *self-test failed* → show the user the output; common causes: AutoCAD never started once after install
     (ask them to open and close AutoCAD once), or a license prompt.

4. **Using a different agent** whose skills folder isn't `~/.claude/skills` or `~/.codex/skills`: run
   `install.ps1 -SkillsDir "<that folder>"`, or point your agent at
   `plugins/cad-headless/skills/cad-headless/SKILL.md` as its instructions.

5. **Tell the user** (in their language):
   - installed, and which AutoCAD it will use (the `Engine:` line: full AutoCAD = everything; LT = no dynamic blocks / table API);
   - **start a new session** so the skill loads;
   - try: *"What's in C:\…\A-101.dwg?"* or *"Plot A-101 to PDF"*;
   - close a drawing in AutoCAD before asking to edit it; every edit makes a backup copy first.

## Claude Code plugin (optional, for updates)

Claude Code users can instead type these two commands themselves (agents can't run slash commands):
```
/plugin marketplace add xy425yi/claude-cad-skill
/plugin install cad-headless@claude-cad-skill
```
Don't use both methods — pick one, or the skill loads twice. To update a script install, `git pull` and re-run `install.ps1`.
