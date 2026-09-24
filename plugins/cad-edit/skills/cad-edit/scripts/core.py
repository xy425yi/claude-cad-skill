#!/usr/bin/env python
"""
core.py — drive AutoCAD's headless engine (accoreconsole.exe) to read / edit / plot DWG files
without opening the AutoCAD window and without COM. Full AutoCAD is preferred (it can NETLOAD
dynblock.dll for dynamic blocks and tables); AutoCAD LT 2024+ also ships accoreconsole and works for plain LISP.

    python core.py info      <dwg>                         # layouts, units, entity counts, xrefs
    python core.py survey    <dwg> [--type MULTILEADER|TEXT|MTEXT|INSERT|DIMENSION|ALL] [--layer L] [--out f.txt]
    python core.py run       <dwg> --cmd '(…lisp…)' [--cmd …] [--file cmds.txt] [--save] [--readonly]
    python core.py plot      <dwg> --layout NAME [--out f.pdf] [--all] [--ctb monochrome.ctb]
    python core.py dxf       <dwg> [--out f.dxf]           # DXFOUT (so no one has to SAVEAS by hand)
    python core.py ctb       <dwg>                         # plot style per layout, whether it's installed, what's available
    python core.py exe                                     # which accoreconsole will be used

Every subcommand builds a .scr (CRLF), loads lisp/lib.lsp, runs accoreconsole from a SHORT temp dir,
and prints the filtered console. Exit code 1 if AutoCAD reported an error.
"""
import argparse, os, re, shutil, subprocess, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lisp", "lib.lsp")
WORK = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Temp"), "Temp", "cadcore")   # short path on purpose (AutoCAD chokes past ~260 chars)
MAXPATH = 240
TIMEOUT_OVERRIDE = None

PREFER_LT = False
DYNBLOCK_DLL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dotnet", "dynblock", "bin", "dynblock.dll")

CONFIG = os.path.join(os.path.dirname(HERE), "cadcore.json")   # written by install.ps1: {"accoreconsole": [paths]}

def find_exe():
    env = os.environ.get("ACCORECONSOLE")
    if env and os.path.exists(env):
        return env
    cands = []
    if os.path.exists(CONFIG):
        try:
            import json
            cands += [p for p in json.load(open(CONFIG, encoding="utf-8-sig")).get("accoreconsole", []) if os.path.exists(p)]
        except Exception as e:
            print(f"WARN: could not read {CONFIG}: {e}")
    roots = [r"C:\Program Files\Autodesk", r"C:\Program Files (x86)\Autodesk"]
    roots += [r for r in os.environ.get("CADCORE_SEARCH", "").split(";") if r]   # extra folders, ;-separated
    for root in roots:   # a root may be an Autodesk folder or an AutoCAD install folder itself (same rule as install.ps1)
        cands += glob.glob(os.path.join(root, "accoreconsole.exe")) + glob.glob(os.path.join(root, "*", "accoreconsole.exe"))
    cands = list({os.path.normcase(os.path.abspath(c)): os.path.abspath(c) for c in cands}.values())
    if not cands:
        sys.exit("accoreconsole.exe not found. Re-run install.ps1 with -AutoCAD \"<AutoCAD folder>\", or set ACCORECONSOLE=<path>. Needs AutoCAD / AutoCAD LT 2024+.")
    # prefer full AutoCAD (its console can NETLOAD .NET plugins such as dynblock.dll), newest year first;
    # --lt or env CADCORE_LT=1 flips that (e.g. to keep a full-version trial license untouched)
    lt = PREFER_LT or os.environ.get("CADCORE_LT") == "1"
    def key(p):
        year = int((re.findall(r"(\d{4})", p) or ["0"])[-1])
        is_lt = "LT" in p.upper()
        return ((0 if is_lt else 1) if lt else (1 if is_lt else 0), -year)
    cands.sort(key=key)
    return cands[0]

def win(p):
    """absolute Windows path with forward slashes (what AutoCAD + LISP strings like)."""
    return os.path.abspath(p).replace("\\", "/")

def check_path(p, what):
    if len(os.path.abspath(p)) > MAXPATH:
        sys.exit(f"{what} path is {len(os.path.abspath(p))} chars; AutoCAD fails past ~260. Copy it somewhere short (e.g. {WORK}).")

def build_scr(lines, save=False):
    body = ["SECURELOAD", "0", "FILEDIA 0", "CMDECHO 0", f'(load "{win(LIB)}")']
    body += lines
    if save:
        body.append("QSAVE")
    return "\r\n".join(body) + "\r\n"

def run_core(dwg, scr_text, readonly=False, timeout=600, tag="job"):
    timeout = TIMEOUT_OVERRIDE or timeout
    exe = find_exe()
    print("engine:", exe)
    if "LT" in exe.upper() and "NETLOAD" in scr_text:
        print("WARN: --dyn needs full AutoCAD; AutoCAD LT cannot NETLOAD dynblock.dll")
    check_path(dwg, "DWG")
    os.makedirs(WORK, exist_ok=True)
    scr = os.path.join(WORK, f"{tag}_{int(time.time())}.scr")
    with open(scr, "w", encoding="utf-8", newline="") as f:
        f.write(scr_text)
    args = [exe, "/i", win(dwg), "/s", win(scr), "/l", "en-US"]
    if readonly:
        args.append("/readonly")
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    cwd = os.path.dirname(os.path.abspath(dwg)) or WORK
    plog = os.path.join(cwd, "plot.log")
    plog0 = os.path.getsize(plog) if os.path.isfile(plog) else None
    t0 = time.time()
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        so, se = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # kill only the console this call started (and its children), never other AutoCAD processes
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        sweep_side_files(cwd, plog0)
        sys.exit(f"accoreconsole timed out after {timeout}s (killed). Check the script for a prompt that waits for input.")
    sweep_side_files(cwd, plog0)
    out = (so + se).decode("utf-8", "replace").replace("\x00", "")
    return out, time.time() - t0, scr

def sweep_side_files(cwd, plog0):
    """accoreconsole drops ErrorReports/ (crash dumps) and appends to plot.log in the drawing's folder.
    Keep project folders clean: move both into WORK (plot.log: only the lines this run appended)."""
    if os.path.abspath(cwd) == os.path.abspath(WORK):
        return
    src = os.path.join(cwd, "ErrorReports")
    if os.path.isdir(src):
        dst = os.path.join(WORK, "ErrorReports")
        os.makedirs(dst, exist_ok=True)
        for n in os.listdir(src):
            t = os.path.join(dst, n)
            if os.path.exists(t):
                t += "_%d" % int(time.time())
            shutil.move(os.path.join(src, n), t)
        try:
            os.rmdir(src)
        except OSError:
            pass
        print("moved ErrorReports ->", dst)
    plog = os.path.join(cwd, "plot.log")
    if os.path.isfile(plog) and os.path.getsize(plog) != (plog0 or 0):
        with open(plog, "rb") as f:
            f.seek(plog0 or 0)
            new = f.read()
        with open(os.path.join(WORK, "plot.log"), "ab") as f:
            f.write(new)
        if plog0:
            with open(plog, "r+b") as f:
                f.truncate(plog0)
        else:
            os.remove(plog)

NOISE = re.compile(r"^(CoreHeartBeat|Loading AEC|Substituting \[|Regenerating|AutoCAD menu|Redirect stdout|AcCoreConsole:|AutoCAD Core Engine|Execution Path|Current Directory|Version Number|LogFilePath|\*\*\*\* System Variable|\d+ of the monitored|Command: *$|Command: Enter BACKSPACE|Enter new value for (SECURELOAD|FILEDIA|CMDECHO)|C:\\Program Files|Command: \(load |Command: SECURELOAD|Command: FILEDIA|Command: CMDECHO|Command: 0$)")

def show(out, verbose=False):
    bad = False
    for ln in out.splitlines():
        s = ln.strip()
        if not s:
            continue
        if not verbose and NOISE.match(s):
            continue
        if re.search(r"ErrorStatus|Improper drawing name|error:|; error|Unknown command|Invalid|\*Cancel\*|Unable|timed out", s):
            bad = True
        if re.search(r"cannot be found|is unloaded", s):
            s = "WARN xref: " + s          # missing xrefs are a warning, not a failure (copy the xref folder along if it matters)
        print(s)
    return bad

# ---------- subcommands ----------
def cmd_exe(a):
    print(find_exe())

def cmd_info(a):
    out, dt, _ = run_core(a.dwg, build_scr(['(hl-info)']), readonly=True, tag="info")
    bad = show(out, a.verbose); print(f"[{dt:.1f}s]"); sys.exit(1 if bad else 0)

def cmd_survey(a):
    outp = win(a.out or os.path.join(WORK, "survey.txt"))
    lines = [f'(hl-survey "{outp}" "{a.type.upper()}" "{a.layer or "*"}")']
    out, dt, _ = run_core(a.dwg, build_scr(lines), readonly=True, tag="survey")
    bad = show(out, a.verbose)
    if os.path.exists(outp):
        n = sum(1 for _ in open(outp, encoding="utf-8", errors="replace"))
        print(f"-> {outp} ({n} rows)  columns: handle|type|layer|space|xmin,ymin,xmax,ymax|name|attrs|text")
        if a.print:
            print(open(outp, encoding="utf-8", errors="replace").read())
    print(f"[{dt:.1f}s]"); sys.exit(1 if bad else 0)

def cmd_run(a):
    lines = list(a.cmd or [])
    if a.file:
        lines += [l.rstrip("\r\n") for l in open(a.file, encoding="utf-8") if l.strip()]
    if not lines:
        sys.exit("nothing to run: give --cmd '(…)' or --file")
    if a.dyn:
        lines.insert(0, f'(command "_.NETLOAD" "{win(DYNBLOCK_DLL)}")')      # dynamic-block helper; full AutoCAD only
    if a.save and a.readonly:
        sys.exit("--save and --readonly contradict")
    if a.save and not a.no_backup:
        bak = a.dwg + f".{time.strftime('%y%m%d_%H%M%S')}.bak.dwg"
        shutil.copy2(a.dwg, bak); print(f"backup -> {bak}")
    out, dt, scr = run_core(a.dwg, build_scr(lines, save=a.save), readonly=a.readonly, tag="run")
    bad = show(out, a.verbose)
    print(f"[{dt:.1f}s] script: {scr}" + ("  SAVED" if a.save and not bad else "  (not saved)" if not a.save else "  SAVE ATTEMPTED — check messages above"))
    sys.exit(1 if bad else 0)

def ctb_info(dwg):
    """{'dir': Plot Styles folder, 'layouts': {layout: style table}, 'available': [files in that folder]}"""
    out, _, _ = run_core(dwg, build_scr(['(hl-ctb-report)']), readonly=True, tag="ctb")
    m = re.search(r"^CTBDIR\|(.*?)\s*$", out, re.M)
    d = m.group(1).strip() if m else ""
    lays = {mm.group(1).strip(): mm.group(2).strip() for mm in re.finditer(r"^CTB\|(.+?)\|(.*?)\s*$", out, re.M)}   # strip(): stray CRs
    avail = sorted(f for f in (os.listdir(d) if d and os.path.isdir(d) else []) if f.lower().endswith((".ctb", ".stb")))
    return {"dir": d, "layouts": lays, "available": avail}

def has_style(name, avail):
    return (not name) or name.lower() == "none" or name.lower() in (x.lower() for x in avail)

def cmd_ctb(a):
    info = ctb_info(a.dwg)
    print("Plot Styles folder:", info["dir"] or "(unknown)")
    missing = False
    for lay, st in info["layouts"].items():
        ok = has_style(st, info["available"])
        missing = missing or not ok
        print(f"  {lay}  ->  {st or '(none)'}" + ("" if ok else "   MISSING on this machine"))
    print("available:", ", ".join(info["available"]) or "(none found)")
    sys.exit(1 if missing else 0)

def cmd_plot(a):
    info = ctb_info(a.dwg)        # one quick read: layout names + their plot styles + what is installed
    if a.all:
        layouts = list(info["layouts"])
        if not layouts:
            sys.exit("no paper-space layouts found")
        print("layouts:", layouts)
    else:
        if not a.layout:
            sys.exit("give --layout NAME or --all (see `info` for names)")
        layouts = [a.layout]
    if a.ctb:
        if not has_style(a.ctb, info["available"]):
            sys.exit(f"plot style '{a.ctb}' is not in {info['dir']}. Available: {', '.join(info['available'])}")
        print(f"plot style for this plot: {a.ctb} (drawing not changed)")
    else:
        miss = [(l, info["layouts"].get(l, "")) for l in layouts if not has_style(info["layouts"].get(l, ""), info["available"])]
        for l, st in miss:
            print(f"MISSING plot style: layout '{l}' uses '{st}', which is not in {info['dir']}")
        if miss and not a.allow_missing_ctb:
            sys.exit("Stopped: line weights / colors would be wrong. Copy the CTB into the Plot Styles folder, "
                     "or pass --ctb <name> (available: " + ", ".join(info["available"]) + "), or --allow-missing-ctb.")
    base = os.path.splitext(os.path.basename(a.dwg))[0]
    outdir = a.outdir or os.path.dirname(os.path.abspath(a.dwg))
    os.makedirs(outdir, exist_ok=True)
    lines = ["BACKGROUNDPLOT 0"] + list(a.pre or [])      # --pre: LISP run before plotting (e.g. freeze revision clouds); never saved
    pdfs = []
    for lay in layouts:
        pdf = a.out if (a.out and len(layouts) == 1) else os.path.join(outdir, f"{base}-{lay}.pdf")
        pdfs.append(pdf)
        if os.path.exists(pdf):
            os.remove(pdf)
        if a.ctb:
            lines.append(f'(hl-set-ctb "{lay}" "{a.ctb}")')
        # page setup "" = the layout's own; device DWG To PDF.pc3; N = don't save page setup; Y = proceed
        lines.append(f'(command "-PLOT" "N" "{lay}" "" "{a.device}" "{win(pdf)}" "N" "Y")')
    out, dt, _ = run_core(a.dwg, build_scr(lines), readonly=True, timeout=1200, tag="plot")
    bad = show(out, a.verbose)
    for pdf in pdfs:
        print(("OK  " if os.path.exists(pdf) else "MISSING ") + pdf)
        bad = bad or not os.path.exists(pdf)
    print(f"[{dt:.1f}s]"); sys.exit(1 if bad else 0)

def cmd_dxf(a):
    outp = a.out or os.path.splitext(a.dwg)[0] + ".dxf"
    if os.path.exists(outp):
        os.remove(outp)
    lines = [f'(command "_.DXFOUT" "{win(outp)}" "16")']
    out, dt, _ = run_core(a.dwg, build_scr(lines), readonly=True, timeout=900, tag="dxf")
    bad = show(out, a.verbose)
    print(("OK  " if os.path.exists(outp) else "MISSING ") + outp); print(f"[{dt:.1f}s]")
    sys.exit(1 if bad or not os.path.exists(outp) else 0)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="sub", required=True)
    sub.add_parser("exe").set_defaults(fn=cmd_exe)
    def common(p):
        p.add_argument("--full", action="store_true", help="use full AutoCAD's accoreconsole (the default; kept for old scripts)")
        p.add_argument("--lt", action="store_true", help="prefer AutoCAD LT's accoreconsole (plain LISP only; no --dyn)")
        p.add_argument("--dyn", action="store_true", help="NETLOAD dotnet/dynblock/bin/dynblock.dll first (full AutoCAD only): (dynget h) (dynallowed h prop) (dynset h prop val)")
        p.add_argument("dwg"); p.add_argument("-v", "--verbose", action="store_true", help="show AutoCAD's full console")
        p.add_argument("--timeout", type=int, help="seconds before accoreconsole is killed (default 600, plot/dxf longer)")
    p = sub.add_parser("info"); common(p); p.set_defaults(fn=cmd_info)
    p = sub.add_parser("survey"); common(p)
    p.add_argument("--type", default="ALL"); p.add_argument("--layer"); p.add_argument("--out"); p.add_argument("--print", action="store_true")
    p.set_defaults(fn=cmd_survey)
    p = sub.add_parser("run"); common(p)
    p.add_argument("--cmd", action="append", help="one LISP expression or command line; repeatable")
    p.add_argument("--file", help="text file, one script line per row")
    p.add_argument("--save", action="store_true", help="QSAVE at the end (makes a timestamped backup copy first)")
    p.add_argument("--no-backup", action="store_true"); p.add_argument("--readonly", action="store_true")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("plot"); common(p)
    p.add_argument("--layout"); p.add_argument("--all", action="store_true"); p.add_argument("--out"); p.add_argument("--outdir")
    p.add_argument("--device", default="DWG To PDF.pc3")
    p.add_argument("--pre", action="append", help="LISP line(s) executed before -PLOT, e.g. (command \"_.-LAYER\" \"_F\" \"A-ANNO-REVS-*\" \"\"); repeatable; nothing is saved")
    p.add_argument("--ctb", help="plot style table for this plot only (e.g. monochrome.ctb); the drawing is not changed")
    p.add_argument("--allow-missing-ctb", action="store_true", help="plot even if the layout's plot style file is missing on this machine")
    p.set_defaults(fn=cmd_plot)
    p = sub.add_parser("ctb"); common(p); p.set_defaults(fn=cmd_ctb)
    p = sub.add_parser("dxf"); common(p); p.add_argument("--out"); p.set_defaults(fn=cmd_dxf)
    a = ap.parse_args()
    global TIMEOUT_OVERRIDE
    TIMEOUT_OVERRIDE = getattr(a, "timeout", None)
    global PREFER_LT
    if getattr(a, "lt", False) and not getattr(a, "dyn", False):
        PREFER_LT = True
    a.fn(a)

if __name__ == "__main__":
    main()
