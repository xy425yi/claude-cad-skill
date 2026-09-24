import sys, fitz, re
# position-matched text diff: signed page vs our plot. Lines are matched by location (±tol in), then compared.
signed, page_no, ours = sys.argv[1], int(sys.argv[2]), sys.argv[3]
tol = float(sys.argv[4]) if len(sys.argv) > 4 else 0.12
A = fitz.open(signed)[page_no - 1]; B = fitz.open(ours)[0]
def lines(p):
    H = p.rect.height; d = {}
    for x0, y0, x1, y1, w, b, l, n in p.get_text("words"): d.setdefault((b, l), []).append((x0, y0, x1, y1, w))
    out = []
    for ws in d.values():
        ws.sort(key=lambda t: t[0]); t = " ".join(w[4] for w in ws)
        out.append({"t": re.sub(r"\s+", " ", t).strip(), "x": min(w[0] for w in ws) / 72, "y": (H - max(w[3] for w in ws)) / 72})
    return out
la, lb = lines(A), lines(B)
used = set(); changed = []; missing = []
for a in la:
    best = None
    for j, b in enumerate(lb):
        if j in used: continue
        if abs(a["x"] - b["x"]) <= tol and abs(a["y"] - b["y"]) <= tol:
            if best is None or (a["t"] == b["t"]): best = j
            if a["t"] == b["t"]: break
    if best is None: missing.append(a); continue
    used.add(best)
    if la and lb[best]["t"] != a["t"]: changed.append((a, lb[best]))
extra = [b for j, b in enumerate(lb) if j not in used]
print(f"signed lines {len(la)} | ours {len(lb)} | same-place-different-text {len(changed)} | in signed but nothing there in ours {len(missing)} | in ours but nothing there in signed {len(extra)}")
print("\n--- SAME PLACE, DIFFERENT TEXT (signed -> ours)")
for a, b in sorted(changed, key=lambda t: (-t[0]['y'], t[0]['x'])): print(f"  ({a['x']:5.2f},{a['y']:5.2f}) {a['t'][:40]!r:44} -> {b['t'][:40]!r}")
print("\n--- IN SIGNED, MISSING IN OURS")
for a in sorted(missing, key=lambda t: (-t['y'], t['x'])): print(f"  ({a['x']:5.2f},{a['y']:5.2f}) {a['t'][:60]!r}")
print("\n--- IN OURS, NOT IN SIGNED")
for b in sorted(extra, key=lambda t: (-t['y'], t['x'])): print(f"  ({b['x']:5.2f},{b['y']:5.2f}) {b['t'][:60]!r}")
