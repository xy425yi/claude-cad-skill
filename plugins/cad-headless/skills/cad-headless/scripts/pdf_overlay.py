import sys, fitz, re, json
from collections import Counter
signed, page_no, ours, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
A = fitz.open(signed)[page_no - 1]
B = fitz.open(ours)[0]
print("signed page", A.rect.width / 72, "x", A.rect.height / 72, "| dwg plot", B.rect.width / 72, "x", B.rect.height / 72)

def words(p):
    # group words into lines by block/line ids, keep centre position in inches (y up)
    H = p.rect.height
    lines = {}
    for x0, y0, x1, y1, w, b, l, n in p.get_text("words"):
        lines.setdefault((b, l), []).append((x0, y0, x1, y1, w))
    out = []
    for k, ws in lines.items():
        ws.sort(key=lambda t: t[0])
        txt = " ".join(w[4] for w in ws)
        x0 = min(w[0] for w in ws); x1 = max(w[2] for w in ws); y0 = min(w[1] for w in ws); y1 = max(w[3] for w in ws)
        out.append({"t": txt, "x": round(x0 / 72, 2), "y": round((H - y1) / 72, 2), "w": round((x1 - x0) / 72, 2)})
    return out

def norm(s): return re.sub(r"\s+", " ", s).strip().upper()

la, lb = words(A), words(B)
ca, cb = Counter(norm(l["t"]) for l in la), Counter(norm(l["t"]) for l in lb)
only_signed = [l for l in la if ca[norm(l["t"])] > cb[norm(l["t"])]]
only_dwg = [l for l in lb if cb[norm(l["t"])] > ca[norm(l["t"])]]
# collapse duplicates of the same string
def collapse(lst):
    seen = {}
    for l in lst:
        k = norm(l["t"]); seen.setdefault(k, {"t": l["t"], "n": 0, "at": []}); seen[k]["n"] += 1
        if len(seen[k]["at"]) < 3: seen[k]["at"].append((l["x"], l["y"]))
    return sorted(seen.values(), key=lambda d: (-d["n"], d["t"]))
os_, od = collapse(only_signed), collapse(only_dwg)
print(f"\nTEXT lines: signed {len(la)}, dwg {len(lb)} | only in SIGNED: {len(os_)} distinct | only in DWG: {len(od)} distinct")
print("\n--- only in the SIGNED PDF (missing/different in the DWG) ---")
for d in os_[:60]: print(f"  x{d['n']} {d['t'][:90]!r} at {d['at'][0]}")
print("\n--- only in the DWG (not in the signed PDF) ---")
for d in od[:60]: print(f"  x{d['n']} {d['t'][:90]!r} at {d['at'][0]}")
# moved text: same string, same count, position shift > 0.15 in
moved = []
for k in set(ca) & set(cb):
    if ca[k] == 1 and cb[k] == 1:
        a = next(l for l in la if norm(l["t"]) == k); b = next(l for l in lb if norm(l["t"]) == k)
        if abs(a["x"] - b["x"]) > 0.15 or abs(a["y"] - b["y"]) > 0.15: moved.append((k, (a["x"], a["y"]), (b["x"], b["y"])))
print(f"\n--- same text, moved > 0.15in: {len(moved)} ---")
for m in sorted(moved)[:25]: print(f"  {m[0][:60]!r} signed {m[1]} → dwg {m[2]}")

# raster diff
dpi = 40
pa = A.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY); pb = B.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
import numpy as np
ia = np.frombuffer(pa.samples, dtype=np.uint8).reshape(pa.height, pa.width)
ib = np.frombuffer(pb.samples, dtype=np.uint8).reshape(pb.height, pb.width)
h, w = min(ia.shape[0], ib.shape[0]), min(ia.shape[1], ib.shape[1]); ia, ib = ia[:h, :w], ib[:h, :w]
da = ia < 128; db = ib < 128
onlyA = da & ~db; onlyB = db & ~da
print(f"\nRASTER @{dpi}dpi: ink signed {da.sum()} px, dwg {db.sum()} px | only-signed {onlyA.sum()} | only-dwg {onlyB.sum()}")
rgb = np.stack([np.full((h, w), 255, np.uint8)] * 3, axis=-1)
both = da & db
rgb[both] = (150, 150, 150)
rgb[onlyA] = (220, 30, 30)    # red = in signed only (missing in dwg)
rgb[onlyB] = (30, 90, 220)    # blue = in dwg only (new in dwg)
pix = fitz.Pixmap(fitz.csRGB, w, h, rgb.tobytes(), False); pix.save(out + "/diff.png")
# hotspots: grid cells with most difference
cell = int(dpi * 2)   # 2-inch cells
hot = []
for gy in range(0, h, cell):
    for gx in range(0, w, cell):
        n = int(onlyA[gy:gy + cell, gx:gx + cell].sum() + onlyB[gy:gy + cell, gx:gx + cell].sum())
        if n > 40: hot.append((n, round(gx / dpi, 1), round((h - gy) / dpi, 1)))
hot.sort(reverse=True)
print("hotspots (diff px, x in, y in from bottom):", hot[:12])
