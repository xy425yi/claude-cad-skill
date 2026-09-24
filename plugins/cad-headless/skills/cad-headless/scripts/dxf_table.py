# -*- coding: utf-8 -*-
"""Inspect and fill real AutoCAD TABLE objects (ACAD_TABLE) inside an ASCII DXF.

Why this exists: an AutoCAD table stores its content TWICE.
  1. legacy cell records inside the ACAD_TABLE entity   (DXF 2007 representation)
  2. a separate TABLECONTENT object, reached via
       ACAD_TABLE -> xdict -> XRECORD "ACAD_ROUNDTRIP_2008_TABLE_ENTITY" -> TABLECONTENT
AutoCAD reads (2). Editing only (1) silently does nothing. This tool rewrites both,
and purges the table's stale rendered block (*T<n>) so no old geometry can show.

Never round-trip a DXF containing tables through ezdxf: ezdxf's AcadTable
load_table()/export_table() are no-ops and it will drop the table content.

CLI
    python dxf_table.py inspect <file.dxf>
    python dxf_table.py fill <src.dxf> <dst.dxf> --handle <H> --data rows.json [--no-verify]

rows.json
    {
      "col_widths":  [36.0, 26.0, ...],   optional; omit to keep the existing widths
      "bold_rows":   [0],                 optional; row indices rendered with the
                                          table's own bold MTEXT prefix
      "rows": [ ["TAG", "", "DESCRIPTION", ...], ... ]
    }
    Cell strings may contain "\\P" for a hard line break, or leave wrapping to
    wrap_rows() below (which measures the real font).
"""
import argparse, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOLD_RE = re.compile(r"^\{\\f[^;]*;")


# --------------------------------------------------------------------------- io
def load(path):
    raw = open(path, encoding="utf-8", errors="strict").read()
    lines = raw.split("\n")
    nl = "\r\n" if lines and lines[0].endswith("\r") else "\n"
    lines = [l.rstrip("\r") for l in lines]
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) % 2:
        lines.append("")
    pairs = [(lines[i].strip(), lines[i + 1]) for i in range(0, len(lines) - 1, 2)]
    return pairs, nl


def save(path, pairs, nl):
    out = []
    for c, v in pairs:
        out.append(c.rjust(3) if len(c) < 3 else c)
        out.append(v)
    open(path, "w", encoding="utf-8", newline=nl).write(nl.join(out) + nl)


def ent_bounds(pairs):
    return [i for i, (c, _) in enumerate(pairs) if c == "0"]


def find_handle(pairs, handle):
    st = ent_bounds(pairs)
    for si, i in enumerate(st):
        b = st[si + 1] if si + 1 < len(st) else len(pairs)
        if next((v.strip() for c, v in pairs[i:b] if c == "5"), None) == handle:
            return i, b
    raise KeyError(f"handle {handle} not found")


def i16(v): return f"{v:6d}"
def i32(v): return f"{v:9d}"


# ---------------------------------------------------------------------- inspect
def tables(pairs):
    """Yield dicts describing every ACAD_TABLE in the file."""
    st = ent_bounds(pairs)
    for si, i in enumerate(st):
        if pairs[i][1].strip() != "ACAD_TABLE":
            continue
        b = st[si + 1] if si + 1 < len(st) else len(pairs)
        sub = pairs[i:b]
        g = lambda code: [v.strip() for c, v in sub if c == code]
        rows = int(g("91")[0]); cols = int(g("92")[0])
        texts = [v for c, v in sub if c == "302"]
        yield {
            "handle": next(v.strip() for c, v in sub if c == "5"),
            "layer": next((v.strip() for c, v in sub if c == "8"), ""),
            "block": next((v.strip() for c, v in sub if c == "2"), ""),
            "insert": (g("10")[0], g("20")[0]),
            "rows": rows, "cols": cols,
            "row_heights": [float(x) for x in g("141")],
            "col_widths": [float(x) for x in g("142")],
            "text_height": float(g("140")[0]) if g("140") else None,
            "margin": float(g("40")[0]) if g("40") else None,
            "style_handle": next((v.strip() for c, v in sub if c == "342"), None),
            "xdict": next((v.strip() for c, v in sub if c == "360"), None),
            "has_binary_blob": any(c == "310" for c, _ in sub),
            "cells": [texts[r * cols:(r + 1) * cols] for r in range(rows)],
            "span": (i, b),
        }


def content_object(pairs, table):
    """Follow xdict -> XRECORD -> TABLECONTENT. Returns (handle, span) or None."""
    if not table["xdict"]:
        return None
    try:
        a, b = find_handle(pairs, table["xdict"])
    except KeyError:
        return None
    xrec = next((v.strip() for c, v in pairs[a:b] if c == "360"), None)
    if not xrec:
        return None
    try:
        a2, b2 = find_handle(pairs, xrec)
    except KeyError:
        return None
    tc = next((v.strip() for c, v in pairs[a2:b2] if c == "360"), None)
    if not tc:
        return None
    try:
        a3, b3 = find_handle(pairs, tc)
    except KeyError:
        return None
    if pairs[a3][1].strip() != "TABLECONTENT":
        return None
    return tc, (a3, b3)


def cmd_inspect(args):
    pairs, _ = load(args.dxf)
    found = list(tables(pairs))
    print(f"{args.dxf}: {len(found)} ACAD_TABLE entity(ies)\n")
    for t in found:
        co = content_object(pairs, t)
        print(f"handle {t['handle']}  {t['rows']} rows x {t['cols']} cols   layer {t['layer']}")
        print(f"  block {t['block']}  insert {t['insert']}  style {t['style_handle']}")
        print(f"  text height {t['text_height']}  cell margin {t['margin']}")
        print(f"  col widths {[round(w,3) for w in t['col_widths']]}")
        print(f"  inline binary blob (160/310): {t['has_binary_blob']}")
        print(f"  TABLECONTENT object: {co[0] if co else 'NONE'}"
              f"{'  <- authoritative content' if co else ''}")
        for r, row in enumerate(t["cells"][:4]):
            print(f"   R{r}: " + " | ".join(
                (BOLD_RE.sub("<B>", x)[:24].replace("\\P", "/")) for x in row))
        print()


# ------------------------------------------------------------------- text width
def text_measurer(font_file, cap_ratio=0.716):
    """Return len(text) -> drawing units, for a given AutoCAD text height."""
    from PIL import ImageFont
    f = ImageFont.truetype(font_file, 1000)
    cap = cap_ratio * 1000
    return lambda s, h: f.getlength(s) / cap * h


def wrap_rows(rows, col_widths, text_height, margin, font_file, safety=0.96,
              hard_wrap=True):
    """Measure how each cell wraps to its column.

    hard_wrap=True  -> cells are returned with "\\P" line breaks baked in.
    hard_wrap=False -> cells are returned as one unbroken string and AutoCAD does
                       the wrapping itself, so the text reflows when a column is
                       resized later. Line counts are still measured, and are used
                       to set the row height.

    Long codes break after an existing '-' or '/' rather than having a hyphen
    inserted (an inserted hyphen turns a catalogue number into a wrong one).
    Returns (cells, line_counts)."""
    measure = text_measurer(font_file)
    out, counts = [], []
    for row in rows:
        cells, n = [], 1
        for ci, val in enumerate(row):
            if not val or BOLD_RE.match(val):
                cells.append(val); continue
            lim = (col_widths[ci] - 2 * margin) * safety
            lines, cur = [], ""

            def hard(chunk):
                nonlocal cur
                while measure(chunk, text_height) > lim:
                    lo, hi = 1, len(chunk)
                    while lo < hi:
                        mid = (lo + hi + 1) // 2
                        if measure(chunk[:mid], text_height) <= lim: lo = mid
                        else: hi = mid - 1
                    lines.append(chunk[:lo]); chunk = chunk[lo:]
                cur = chunk

            for word in str(val).split():
                cand = word if not cur else cur + " " + word
                if measure(cand, text_height) <= lim:
                    cur = cand; continue
                if cur:
                    lines.append(cur); cur = ""
                if measure(word, text_height) <= lim:
                    cur = word; continue
                for chunk in re.split(r"(?<=[-/])", word):
                    if measure(cur + chunk, text_height) <= lim:
                        cur += chunk
                    else:
                        if cur: lines.append(cur); cur = ""
                        hard(chunk)
            if cur: lines.append(cur)
            lines = lines or [""]
            n = max(n, len(lines))
            cells.append("\\P".join(lines) if hard_wrap else val)
        out.append(cells); counts.append(n)
    return out, counts


def row_height(n_lines, text_height, margin):
    """AutoCAD table row height for n lines of text (verified against real files)."""
    return n_lines * text_height * 4.0 / 3.0 + 2 * margin


# ---------------------------------------------------------------------- rebuild
def find_block(seq, name, start=0):
    i = next(k for k in range(start, len(seq))
             if seq[k][0] == "1" and seq[k][1].strip() == name + "_BEGIN")
    depth = 0
    for k in range(i, len(seq)):
        c, v = seq[k]
        if c == "1" and v.strip().endswith("_BEGIN"): depth += 1
        elif c == "309" and v.strip().endswith("_END"):
            depth -= 1
            if depth == 0: return i, k
    raise ValueError(f"unterminated {name}")


def build_acad_table(old, cells, heights, widths, text_height):
    """Rebuild the ACAD_TABLE entity, keeping its header tags but dropping the
    inline 160/310 binary blob (a stale cache that would win over our edit)."""
    nrows, ncols = len(cells), len(widths)
    head, seen = [], set()
    for c, v in old:
        if c in ("160", "310"):
            continue
        if c == "141":                      # first row height -> stop copying header
            break
        head.append((c, v))
    # patch counts
    def setcode(code, val):
        for k, (c, v) in enumerate(head):
            if c == code and "AcDbTable" in [x[1] for x in head[:k]]:
                head[k] = (code, val); return
    tail_start = [k for k, (c, v) in enumerate(head) if c == "100" and v.strip() == "AcDbTable"]
    base = tail_start[0] if tail_start else 0
    for k in range(base, len(head)):
        if head[k][0] == "91": head[k] = ("91", i32(nrows)); break
    for k in range(base, len(head)):
        if head[k][0] == "92": head[k] = ("92", i32(ncols)); break

    t = list(head)
    t += [("141", repr(h)) for h in heights]
    t += [("142", repr(w)) for w in widths]
    for row in cells:
        for txt in row:
            t += [("171", i16(1)), ("172", i16(0)), ("173", i16(0)), ("174", i16(0)),
                  ("175", i16(1)), ("176", i16(1))]
            if txt:
                t += [("91", i32(33)), ("178", i16(0)), ("145", "0.0"), ("170", i16(4)),
                      ("140", repr(text_height)), ("92", i32(0)), ("301", "CELL_VALUE"),
                      ("93", i32(6)), ("90", i32(4)), ("1", txt), ("94", i32(0)),
                      ("300", ""), ("302", txt), ("304", "ACVALUE_END")]
            else:
                t += [("91", i32(1)), ("178", i16(0)), ("145", "0.0"), ("170", i16(4)),
                      ("92", i32(0)), ("301", "CELL_VALUE"), ("93", i32(7)),
                      ("90", i32(0)), ("94", i32(0)), ("300", ""), ("302", ""),
                      ("304", "ACVALUE_END")]
    return t


def build_tablecontent(old, cells, heights, widths):
    """Rebuild the TABLECONTENT object by cloning its own column / row / cell
    templates.  Per-cell ACAD_ROUNDTRIP_2008_CELL_CHECKSUM entries are replaced
    with an empty datamap so no stale checksum survives."""
    col_at = [i for i, (c, v) in enumerate(old) if c == "300" and v.strip() == "COLUMN"]
    row_at = [i for i, (c, v) in enumerate(old) if c == "301" and v.strip() == "ROW"]
    last_end = max(i for i, (c, v) in enumerate(old)
                   if c == "309" and v.strip() == "TABLEROW_END")
    prefix, coltpl = list(old[:col_at[0]]), old[col_at[0]:col_at[1]]
    # the last 90 in the prefix is the column count (AcDbLinkedTableData)
    for k in range(len(prefix) - 1, -1, -1):
        if prefix[k][0] == "90":
            prefix[k] = ("90", i32(len(widths))); break
    rowtpl = old[row_at[1]:row_at[2]] if len(row_at) > 2 else old[row_at[0]:row_at[1]]
    trailer = old[last_end + 1:]

    def make_col(w):
        o = list(coltpl)
        i, j = find_block(o, "TABLECOLUMN")
        for k in range(i, j + 1):
            if o[k][0] == "40":
                o[k] = ("40", repr(w)); break
        return o

    cell_at = [k for k, (c, v) in enumerate(rowtpl) if c == "300" and v.strip() == "CELL"]
    rowend = next(k for k, (c, v) in enumerate(rowtpl)
                  if c == "309" and v.strip() == "LINKEDTABLEDATAROW_END")
    rhead = list(rowtpl[:cell_at[0]])
    for k, (c, v) in enumerate(rhead):          # cells-per-row count
        if c == "90":
            rhead[k] = ("90", i32(len(widths))); break
    rcells = [rowtpl[cell_at[m]:(cell_at[m + 1] if m + 1 < len(cell_at) else rowend)]
              for m in range(len(cell_at))]
    rtail = rowtpl[rowend:]
    MARK = ("_BEGIN", "_END")
    def has_content(cl):
        # a text cell carries a real string as the VALUE inside CELLCONTENT; empty cells in some
        # tables still carry a CELLCONTENT block (value type 7, empty string) - treat those as empty
        try:
            i, j = find_block(cl, "CELLCONTENT")
        except (StopIteration, ValueError):
            return False
        return any(c == "1" and v.strip() and not v.strip().endswith(MARK) for c, v in cl[i:j + 1])
    text_tpl = next((c for c in rcells if has_content(c)), None)
    empty_tpl = next((c for c in rcells if not has_content(c)), None)
    if text_tpl is None:
        raise RuntimeError("template row has no text cell - pick another template row")
    if empty_tpl is None:                       # synthesise by stripping the content
        i, j = find_block(text_tpl, "CELLCONTENT")
        k = next(k for k, (c, v) in enumerate(text_tpl)
                 if c == "302" and v.strip() == "CONTENT")
        empty_tpl = text_tpl[:k] + text_tpl[j + 1:]

    def kill_checksum(cell):
        try:
            i, j = find_block(cell, "DATAMAP")
        except (StopIteration, ValueError):
            return cell
        return cell[:i] + [("1", "DATAMAP_BEGIN"), ("90", i32(0)),
                           ("309", "DATAMAP_END")] + cell[j + 1:]

    def make_cell(txt):
        if not txt:
            return kill_checksum(list(empty_tpl))
        cell = kill_checksum(list(text_tpl))
        i, j = find_block(cell, "CELLCONTENT")
        for k in range(i, j + 1):
            c, v = cell[k]
            if c == "1" and v.strip() == "CELLCONTENT_BEGIN":
                continue
            if c in ("1", "302") and v.strip() not in ("", "VALUE"):
                cell[k] = (c, txt)
        return cell

    out = list(prefix)
    for w in widths:
        out += make_col(w)
    out.append(("91", i32(len(cells))))
    for row, h in zip(cells, heights):
        o = list(rhead)
        for txt in row:
            o += make_cell(txt)
        tail = list(rtail)
        i, j = find_block(tail, "TABLEROW")
        for k in range(i, j + 1):
            if tail[k][0] == "40":
                tail[k] = ("40", repr(h)); break
        out += o + tail
    return out + trailer


def purge_block(pairs, name):
    st = ent_bounds(pairs)
    for si, i in enumerate(st):
        if pairs[i][1].strip() != "BLOCK":
            continue
        b = st[si + 1] if si + 1 < len(st) else len(pairs)
        if next((v.strip() for c, v in pairs[i:b] if c == "2"), None) != name:
            continue
        for sj in range(si + 1, len(st)):
            if pairs[st[sj]][1].strip() == "ENDBLK":
                return pairs[:b] + pairs[st[sj]:], st[sj] - b
    return pairs, 0


# ------------------------------------------------------------------------- fill
def cmd_fill(args):
    spec = json.load(open(args.data, encoding="utf-8"))
    pairs, nl = load(args.src)
    tabs = {t["handle"]: t for t in tables(pairs)}
    if args.handle not in tabs:
        sys.exit(f"handle {args.handle} not in {list(tabs)}")
    t = tabs[args.handle]

    widths = spec.get("col_widths") or t["col_widths"]
    th = spec.get("text_height") or t["text_height"]
    margin = spec.get("margin") or t["margin"]
    if len(widths) != t["cols"]:
        print(f"column count changing: {t['cols']} -> {len(widths)}")
    for ri, r in enumerate(spec["rows"]):
        if len(r) != len(widths):
            sys.exit(f"row {ri} has {len(r)} cells, expected {len(widths)}")

    bold_prefix = None
    for row in t["cells"]:
        for x in row:
            m = BOLD_RE.match(x)
            if m:
                bold_prefix = m.group(0); break
        if bold_prefix: break
    rows = [list(r) for r in spec["rows"]]
    for ri in spec.get("bold_rows", []):
        if bold_prefix:
            rows[ri] = [bold_prefix + x + "}" if x else x for x in rows[ri]]

    cells, counts = wrap_rows(rows, widths, th, margin,
                              spec.get("font", "C:/Windows/Fonts/arialn.ttf"),
                              hard_wrap=spec.get("hard_wrap", True))
    heights = [row_height(n, th, margin) for n in counts]
    print(f"wrapping: {'baked in (\\P)' if spec.get('hard_wrap', True) else 'left to AutoCAD - text reflows on column resize'}")

    co = content_object(pairs, t)
    new_tab = build_acad_table(pairs[t["span"][0]:t["span"][1]], cells, heights, widths, th)
    splices = [(t["span"][0], t["span"][1], new_tab)]
    if co:
        ca, cb = co[1]
        splices.append((ca, cb, build_tablecontent(pairs[ca:cb], cells, heights, widths)))
        print(f"TABLECONTENT {co[0]}: {cb-ca} -> {len(splices[-1][2])} pairs")
    else:
        print("no TABLECONTENT object - legacy records only")
    for a, b, new in sorted(splices, key=lambda x: -x[0]):
        pairs = pairs[:a] + new + pairs[b:]

    if t["block"].startswith("*T"):
        pairs, n = purge_block(pairs, t["block"])
        print(f"purged {n} pairs of stale geometry from block {t['block']}")

    save(args.dst, pairs, nl)
    print(f"ACAD_TABLE {t['handle']}: {t['rows']} -> {len(cells)} rows, "
          f"table height {sum(heights):.1f} units")
    print("written:", args.dst, os.path.getsize(args.dst), "bytes")
    if not args.no_verify:
        verify(args.dst, args.handle, cells, heights, widths)


def verify(path, handle, cells, heights, widths):
    pairs, _ = load(path)
    ok = True
    lines_even = True
    print("\n--- verify ---")
    t = next(t for t in tables(pairs) if t["handle"] == handle)
    co = content_object(pairs, t)
    if co:
        tc = pairs[co[1][0]:co[1][1]]
        d = 0
        for c, v in tc:
            s = v.strip()
            if c == "1" and s.endswith("_BEGIN"): d += 1
            elif c == "309" and s.endswith("_END"): d -= 1
        print(f"TABLECONTENT nesting balanced: {d == 0}")
        ok &= d == 0
        nrow = sum(1 for c, v in tc if c == "301" and v.strip() == "ROW")
        print(f"TABLECONTENT rows: {nrow} (expected {len(cells)})")
        ok &= nrow == len(cells)
    flat = [x for row in cells for x in row]
    print(f"legacy cells: {t['rows']*t['cols']} (expected {len(flat)}) "
          f"| text matches: {[x for r in t['cells'] for x in r] == flat}")
    ok &= [x for r in t["cells"] for x in r] == flat
    print(f"row heights match: "
          f"{[round(x,6) for x in t['row_heights']] == [round(x,6) for x in heights]}")
    print(f"col widths match: "
          f"{[round(x,6) for x in t['col_widths']] == [round(x,6) for x in widths]}")
    try:
        import ezdxf
        doc = ezdxf.readfile(path); au = doc.audit()
        print(f"ezdxf: {len(au.errors)} errors, {len(au.fixes)} fixes "
              f"(compare with the SOURCE file - pre-existing fixes are normal)")
    except Exception as e:
        print("ezdxf load FAILED:", e); ok = False
    print("RESULT:", "OK" if ok else "*** PROBLEM ***")
    return ok



# ------------------------------------------------------------------------ proof
def cmd_proof(args):
    """Render the table straight out of the DXF to a PNG. There is no other way
    to see the result without AutoCAD - always do this before handing the file over."""
    from PIL import Image, ImageDraw, ImageFont
    pairs, _ = load(args.dxf)
    t = next(x for x in tables(pairs) if x["handle"] == args.handle)
    th, margin = t["text_height"], t["margin"]
    line_h = th * 4.0 / 3.0
    W, H = t["col_widths"], t["row_heights"]
    px = args.scale
    img = Image.new("RGB", (int(sum(W) * px) + 20, int(sum(H) * px) + 20), (26, 26, 26))
    d = ImageDraw.Draw(img)
    xs = [10.0]
    for w in W:
        xs.append(xs[-1] + w * px)
    reg = ImageFont.truetype(args.font, max(6, int(th * px)))
    bold_file = args.font.replace(".ttf", "b.ttf")
    bold = ImageFont.truetype(bold_file if os.path.exists(bold_file) else args.font,
                              max(6, int(th * px)))
    # cells stored without "\P" are wrapped by AutoCAD at display time -
    # simulate that here, otherwise the proof would show one long line.
    stripped = [[BOLD_RE.sub("", c)[:-1] if BOLD_RE.match(c) else c for c in row]
                for row in t["cells"]]
    sim, _ = wrap_rows(stripped, W, th, margin, args.font)
    y = 10.0
    for ri, row in enumerate(t["cells"]):
        d.line([10, y, xs[-1], y], fill=(0, 176, 80))
        for ci, cell in enumerate(row):
            is_bold = bool(BOLD_RE.match(cell))
            txt = sim[ri][ci]
            ty = y + margin * px
            for ln in txt.split("\\P"):
                d.text((xs[ci] + margin * px, ty), ln,
                       font=bold if is_bold else reg,
                       fill=(0, 200, 215) if is_bold else (232, 232, 232))
                ty += line_h * px
        y += H[ri] * px
    d.line([10, y, xs[-1], y], fill=(0, 176, 80))
    for xv in xs:
        d.line([xv, 10, xv, y], fill=(0, 176, 80))
    img.save(args.out)
    print(f"{args.out}  {img.size[0]}x{img.size[1]}px  "
          f"({t['rows']} rows, {sum(H):.1f} drawing units tall)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("inspect"); a.add_argument("dxf"); a.set_defaults(fn=cmd_inspect)
    b = sp.add_parser("fill")
    b.add_argument("src"); b.add_argument("dst")
    b.add_argument("--handle", required=True)
    b.add_argument("--data", required=True)
    b.add_argument("--no-verify", action="store_true")
    b.set_defaults(fn=cmd_fill)
    c = sp.add_parser("proof")
    c.add_argument("dxf"); c.add_argument("--handle", required=True)
    c.add_argument("--out", default="table_proof.png")
    c.add_argument("--scale", type=float, default=3.2)
    c.add_argument("--font", default="C:/Windows/Fonts/arialn.ttf")
    c.set_defaults(fn=cmd_proof)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
