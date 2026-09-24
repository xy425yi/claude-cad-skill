"""Replace / fill individual rows of an ACAD_TABLE in an ASCII DXF, e.g. insert a sheet into a drawing index
by shifting the rows below it down and filling a spare empty row.  Row-level surgery only - header row
(rotated text, merged cells) and every other row keep their original records.  Both table
representations (legacy ACAD_TABLE cells + TABLECONTENT object) are edited; the inline 160/310
cache is dropped and the rendered *T block purged, as dxf_table.py does.

    python table_rowedit.py cfg.json
    cfg.json: {"src": "in.dxf", "dst": "out.dxf", "handle": "B02D7",
               "template_row": 3,                        # optional: copy formatting + row height from this row
               "rows": {"15": ["A-400", "SECTIONS"], "16": ["A-500", "ELEVATIONS"]}}   # full cell list per row
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxf_table as dt

import json
CFG = json.load(open(sys.argv[1]))          # {src, dst, handle, template_row, rows: {row: [full cell list]}}
SRC, DST, HANDLE = CFG['src'], CFG['dst'], CFG['handle']
NEW = {int(k): v for k, v in CFG['rows'].items()}
TPL = CFG.get('template_row')
DOT = '{\\H1.0833x;●}'

pairs, nl = dt.load(SRC)
t = next(x for x in dt.tables(pairs) if x['handle'] == HANDLE)
ncols = t['cols']

# ---------- legacy ACAD_TABLE: split into header / per-cell records ----------
a, b = t['span']; ent = pairs[a:b]
first141 = next(i for i, (c, v) in enumerate(ent) if c == '141')
cell_starts = [i for i, (c, v) in enumerate(ent) if c == '171']          # every cell record starts with 171
tail_start = next((i for i, (c, v) in enumerate(ent) if i > cell_starts[-1] and c in ('1001',)), len(ent))
head = [(c, v) for (c, v) in ent[:cell_starts[0]] if c not in ('160', '310')]
recs = [ent[s:(cell_starts[k + 1] if k + 1 < len(cell_starts) else tail_start)] for k, s in enumerate(cell_starts)]
tail = ent[tail_start:]
assert len(recs) == t['rows'] * ncols, (len(recs), t['rows'] * ncols)
rows = [recs[r * ncols:(r + 1) * ncols] for r in range(t['rows'])]

def set_text(rec, txt):
    return [(c, txt if c in ('1', '302') else v) for (c, v) in rec]

def legacy_row(src_row, texts):
    return [set_text(rec, texts[ci]) if texts[ci] else list(rec) for ci, rec in enumerate(src_row)]

for r, texts in NEW.items():
    tpl = rows[TPL] if TPL is not None else rows[r]
    rows[r] = legacy_row(tpl, texts)
if TPL is not None:                                  # row height (legacy 141 list) follows the template row
    h141 = [i for i, (c, v) in enumerate(head) if c == '141']
    for r in NEW: head[h141[r]] = head[h141[TPL]]
new_ent = head + [rec_pair for row in rows for rec in row for rec_pair in rec] + tail
pairs = pairs[:a] + new_ent + pairs[b:]

# ---------- TABLECONTENT object ----------
t = next(x for x in dt.tables(pairs) if x['handle'] == HANDLE)
co = dt.content_object(pairs, t); ca, cb = co[1]; tc = pairs[ca:cb]
row_at = [i for i, (c, v) in enumerate(tc) if c == '301' and v.strip() == 'ROW']
last_end = max(i for i, (c, v) in enumerate(tc) if c == '309' and v.strip() == 'TABLEROW_END')
blocks = [tc[row_at[k]:(row_at[k + 1] if k + 1 < len(row_at) else last_end + 1)] for k in range(len(row_at))]
assert len(blocks) == t['rows'], (len(blocks), t['rows'])

def kill_checksum(block):
    out = list(block); i = 0
    while True:
        try:
            s, e = dt.find_block(out, 'DATAMAP')
        except (StopIteration, ValueError):
            return out
        # replace every DATAMAP with an empty one (stale checksums would win over the edit)
        if [x for x in out[s:e + 1] if x[0] == '90' and x[1].strip() == '0'] and e - s <= 2:
            break
        out = out[:s] + [('1', 'DATAMAP_BEGIN'), ('90', dt.i32(0)), ('309', 'DATAMAP_END')] + out[e + 1:]
    return out

def content_row(src_block, texts):
    cells = [k for k, (c, v) in enumerate(src_block) if c == '300' and v.strip() == 'CELL']
    out = list(src_block); texts = {ci: tx for ci, tx in enumerate(texts) if tx}
    for ci, k in enumerate(cells):
        if ci not in texts: continue
        kend = cells[ci + 1] if ci + 1 < len(cells) else len(out)
        for j in range(k, kend):
            c, v = out[j]
            if c in ('1', '302') and v.strip() and not v.strip().endswith(('_BEGIN', '_END')) and v.strip() not in ('CELL', 'CONTENT', 'CELLCONTENT', 'DATAMAP'):
                out[j] = (c, texts[ci]); break            # the first real string in the cell = the value
    return kill_checksum(out)

for r, texts in NEW.items():
    tplb = blocks[TPL] if TPL is not None else blocks[r]
    blocks[r] = content_row(tplb, texts)
    print('row', r, 'TABLEROW height codes:', [v for c, v in blocks[r] if c == '40'][-2:])
new_tc = tc[:row_at[0]] + [p for blk in blocks for p in blk] + tc[last_end + 1:]
pairs = pairs[:ca] + new_tc + pairs[cb:]

if t['block'].startswith('*T'):
    pairs, n = dt.purge_block(pairs, t['block']); print('purged', n, 'pairs of', t['block'])
dt.save(DST, pairs, nl)
t2 = next(x for x in dt.tables(dt.load(DST)[0]) if x['handle'] == HANDLE)
for r in NEW: print(r, t2['cells'][r])
