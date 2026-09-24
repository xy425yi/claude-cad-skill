# cad-edit installer for Windows (Claude Code, OpenAI Codex, other agents that read SKILL.md folders).
#
# Run it from a cloned or unzipped copy of the repo (read it first - it is short):
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# What it does: finds AutoCAD's accoreconsole.exe, checks Python, installs the Python packages,
# copies the skill into ~/.claude/skills (and ~/.codex/skills if Codex is installed), then runs a self-test.
# It never touches your drawings, needs no admin rights, changes no system settings and sends nothing
# anywhere (the only downloads are three Python packages from PyPI). Re-run it any time to update.

param(
    [string]$AutoCAD = "",            # AutoCAD folder(s) outside C:\Program Files, ;-separated (install folder or its parent)
    [string]$SkillsDir = "",          # install only into this folder (testing / other agents)
    [switch]$SkipPip,                 # don't pip install
    [switch]$SkipTest                 # don't run the self-test
)

$ErrorActionPreference = "Stop"
$Repo = "xy425yi/claude-cad-skill"
$SkillRel = "plugins\cad-edit\skills\cad-edit"
$problems = @()

function Say($msg) { Write-Host $msg }
function Ok($msg) { Write-Host "  [ok]   $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [warn] $msg" -ForegroundColor Yellow }
function Bad($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

Say ""
Say "cad-edit installer"
Say "======================"

# ---------- 1. get the skill files ----------
Say "1. Skill files"
if (-not $PSScriptRoot -or -not (Test-Path (Join-Path $PSScriptRoot "$SkillRel\SKILL.md"))) {
    Bad "run this file from inside the downloaded repo:  powershell -ExecutionPolicy Bypass -File install.ps1"
    Say  "         get the repo with:  git clone https://github.com/$Repo   (or Code > Download ZIP on that page, then unzip)"
    exit 1
}
$src = Join-Path $PSScriptRoot $SkillRel
Ok "using $src"

# ---------- 2. AutoCAD ----------
Say "2. AutoCAD"
$roots = @("C:\Program Files\Autodesk", "C:\Program Files (x86)\Autodesk")
if ($AutoCAD) { $roots += $AutoCAD.Split(";") }
if ($env:CADCORE_SEARCH) { $roots += $env:CADCORE_SEARCH.Split(";") }
$exes = @()
if ($env:ACCORECONSOLE -and (Test-Path $env:ACCORECONSOLE)) { $exes += Get-Item $env:ACCORECONSOLE }
foreach ($r in $roots) {
    if (-not $r) { continue }
    $r = $r.Trim().Trim('"')
    if ($r -like "*accoreconsole.exe") { $r = Split-Path $r }
    if (-not (Test-Path $r)) { Warn "folder not found: $r"; continue }
    # same rule as core.py: <folder>\accoreconsole.exe or <folder>\*\accoreconsole.exe
    $exes += Get-ChildItem -Path (Join-Path $r "accoreconsole.exe") -ErrorAction SilentlyContinue
    $exes += Get-ChildItem -Path (Join-Path $r "*\accoreconsole.exe") -ErrorAction SilentlyContinue
}
$exes = @($exes | Sort-Object FullName -Unique)
$full = @($exes | Where-Object { $_.FullName -notmatch "AutoCAD LT" })
$lt = @($exes | Where-Object { $_.FullName -match "AutoCAD LT" })
foreach ($e in $exes) { Ok $e.FullName }
if ($exes.Count -eq 0) {
    Bad "no accoreconsole.exe found. Install AutoCAD 2024+ (or AutoCAD LT 2024+)."
    Say  "         Installed somewhere else? Re-run with:  -AutoCAD `"D:\Path\To\AutoCAD 2026`""
    $problems += "AutoCAD not found"
} elseif ($full.Count -eq 0) {
    Warn "ONLY AutoCAD LT found: plain edits and plotting work; dynamic blocks and the table API need full AutoCAD."
    Say  "         If full AutoCAD is installed outside C:\Program Files, re-run with:  -AutoCAD `"D:\Path\To\AutoCAD 2026`""
}

# ---------- 3. Python ----------
Say "3. Python"
$py = $null
foreach ($cand in @("python", "py")) {
    try {
        $v = & $cand --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3\.(\d+)") {
            if ([int]$Matches[1] -ge 10) { $py = $cand; Ok "$v ($cand)"; break }
        }
    } catch { }
}
if (-not $py) {
    Bad "Python not found (needs 3.10+)."
    Say  "         Install it with:  winget install -e --id Python.Python.3.12   then fully quit and reopen the app and re-run this installer"
    $problems += "Python missing"
} elseif (-not $SkipPip) {
    & $py -m pip install --user --quiet --disable-pip-version-check pymupdf numpy ezdxf
    if ($LASTEXITCODE -eq 0) { Ok "pymupdf, numpy, ezdxf installed" } else { Warn "pip install failed; run:  $py -m pip install --user pymupdf numpy ezdxf"; $problems += "pip failed" }
}

# ---------- 4. copy the skill ----------
Say "4. Install skill"
$targets = @()
if ($SkillsDir) { $targets += $SkillsDir }
else {
    $targets += Join-Path $HOME ".claude\skills"
    if (Test-Path (Join-Path $HOME ".codex")) { $targets += Join-Path $HOME ".codex\skills" }
}
$installed = $null
foreach ($t in $targets) {
    $dst = Join-Path $t "cad-edit"
    $old = Join-Path $t "cad-headless"          # name before 1.2.0
    if (Test-Path (Join-Path $old ".git")) {
        Warn "$old is a git checkout of this skill under its old name (someone develops it there) - not installing cad-edit next to it"
        if (-not $installed) { $installed = $old }
        continue
    }
    if (Test-Path $old) {
        $bakRoot = Join-Path $env:LOCALAPPDATA "cad-edit-backups"
        New-Item -ItemType Directory -Path $bakRoot -Force | Out-Null
        Move-Item $old (Join-Path $bakRoot ("cad-headless-" + (Get-Date -Format "yyMMdd-HHmmss")))
        Say  "         moved the old 'cad-headless' install to $bakRoot (renamed to cad-edit)"
    }
    if (Test-Path (Join-Path $dst ".git")) {
        Warn "$dst is a git checkout (someone develops it there) - left untouched"
        if (-not $installed) { $installed = $dst }
        continue
    }
    if (-not (Test-Path $t)) { New-Item -ItemType Directory -Path $t -Force | Out-Null }
    if (Test-Path $dst) {
        $bakRoot = Join-Path $env:LOCALAPPDATA "cad-edit-backups"
        New-Item -ItemType Directory -Path $bakRoot -Force | Out-Null
        $bak = Join-Path $bakRoot ((Split-Path (Split-Path $t) -Leaf).TrimStart(".") + "-" + (Get-Date -Format "yyMMdd-HHmmss"))
        Move-Item $dst $bak
        Say  "         previous version kept at $bak"
    }
    Copy-Item $src $dst -Recurse
    Get-ChildItem $dst -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    # remember where AutoCAD is, so no environment variable (and no app restart) is needed
    $cfg = @{ accoreconsole = @($exes | ForEach-Object { $_.FullName }) } | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $dst "cadcore.json"), $cfg)
    Ok $dst
    if (-not $installed) { $installed = $dst }
}

# ---------- 5. self-test ----------
$engine = $null
Say "5. Self-test"
if ($SkipTest) {
    Warn "skipped (-SkipTest)"
} elseif (-not $py -or $exes.Count -eq 0) {
    Warn "skipped (fix the problems above first)"
} else {
    $core = Join-Path $installed "scripts\core.py"
    $work = Join-Path $env:LOCALAPPDATA "Temp\cadcore\selftest"
    New-Item -ItemType Directory -Path $work -Force | Out-Null
    $dxf = (Join-Path $work "selftest.dxf").Replace("\", "/")
    & $py -c "import ezdxf; d = ezdxf.new('R2018'); m = d.modelspace(); m.add_line((0, 0), (10, 0)); m.add_text('cad-edit self-test').set_placement((0, 1)); d.saveas('$dxf')"
    $out = & $py $core info $dxf 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0 -and $out -match "LINE") {
        Ok "accoreconsole opened a test drawing and read it back"
        $engine = ([regex]::Match($out, "engine:\s*(.+)")).Groups[1].Value.Trim()
    } else {
        Bad "self-test failed. Output:"
        Say $out
        $problems += "self-test failed"
    }
}

# ---------- summary ----------
Say ""
if ($problems.Count -eq 0) {
    Write-Host "DONE - cad-edit is installed." -ForegroundColor Green
    if ($engine) {
        $kind = if ($engine -match "AutoCAD LT") { "AutoCAD LT (plain edits + plotting; no dynamic blocks / table API)" } else { "full AutoCAD (all features)" }
        Say "Engine: $kind"
        Say "        $engine"
    }
    Say "Start a NEW Claude Code (or Codex) session, open your project folder, and ask, e.g.:"
    Say "  'What's in C:/Projects/A-101.dwg?'"
    Say "  'Plot the A-101 layout of that drawing to PDF.'"
    Say "Tip: close a drawing in AutoCAD before asking the agent to edit it."
    exit 0
} else {
    Write-Host ("NOT FINISHED - " + ($problems -join "; ")) -ForegroundColor Red
    Say "Fix the items marked [FAIL] above and run the installer again."
    exit 1
}
