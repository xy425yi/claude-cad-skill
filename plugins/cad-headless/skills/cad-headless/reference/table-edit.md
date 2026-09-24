# Editing AutoCAD tables (ACAD_TABLE / schedules)

Two routes. **Use A with full AutoCAD**; B only when all you have is AutoCAD LT.

| | A. dynblock.dll (preferred) | B. DXF surgery (fallback) |
|---|---|---|
| Needs | full AutoCAD (`core.py run --dyn`) | any accoreconsole (`core.py dxf` out, SAVEAS back to DWG) |
| Edits | the DWG itself, through the AutoCAD API — styles, merged cells, row heights handled by AutoCAD | the DXF text; you must keep two copies of the content in sync |
| Risk | low | high: a malformed structure makes AutoCAD discard the drawing |

---

## A. dynblock.dll table functions (`dotnet/dynblock/Tbl.cs`)

Handles are strings; rows/columns count from 0.

```lisp
(tblrows "B096D")              ; number of rows
(tblcols "B096D")              ; number of columns
(tblrowh "B096D" 1)            ; row height
(tblsetrowh "B096D" 1 0.3)     ; set row height, returns the actual value (AutoCAD may grow it)
(tblcolw "B096D" 0 [w])        ; get / set column width
(tblget "B096D" 2 0)           ; cell text
(tblset "B096D" 2 0 "AL.2")    ; set displayed text only (keeps cell style)
(tblsetval "B096D" 2 0 "AL.2") ; set VALUE and text (use for data cells; tblset changes only the display)
(tblinsrow "B096D" 2 1)        ; insert a row at 2, formatting and height inherited from row 1
(tbldelrows "B096D" 4 2)       ; delete 2 rows starting at 4
(tbldelcols "B096D" 4 3)       ; delete 3 columns starting at 4
(tblregen "B096D")             ; rebuild the table graphics — always call after edits, before saving
```

Then the knock-on checks (`graphic-standard.md`, "Schedules — after changing row count"): stretch the frame
block, measure column widths on the plot, move loose symbols with their rows, check the table didn't grow
into what's below.

---

## B. DXF surgery (`scripts/dxf_table.py`, `scripts/table_rowedit.py`)

### The trap: the content is stored twice

```
1) legacy cell records inside the ACAD_TABLE entity     ← DXF 2007 representation
2) a separate TABLECONTENT object                        ← what AutoCAD actually reads
   ACAD_TABLE ─360→ DICTIONARY ─360→ XRECORD (ACAD_ROUNDTRIP_2008_TABLE_ENTITY) ─360→ TABLECONTENT
```

Editing only (1) does nothing — the drawing opens with the old content. Edit both, and:
- drop the entity's inline `160`/`310` binary cache (stale content that wins over your edit);
- replace each cell's `ACAD_ROUNDTRIP_2008_CELL_CHECKSUM` with an empty datamap;
- purge the table's rendered block `*T<n>` (stale graphics).

**Never load and save a DXF with tables through ezdxf**: its `AcadTable.load_table()/export_table()` are no-ops, the
table content is gone after saving. Use ezdxf read-only for auditing (its many `INVALID_OWNER_HANDLE` fixes usually
come from the source file — run it on the source first).

### Tools

```bash
python scripts/dxf_table.py inspect file.dxf              # per table: handle, rows/cols, text height, margins, widths, TABLECONTENT handle, first 4 rows
python scripts/dxf_table.py fill src.dxf dst.dxf --handle B02D7 --data rows.json   # rewrite the whole table
python scripts/dxf_table.py proof dst.dxf --handle B02D7 --out proof.png           # render from the DXF data
python scripts/table_rowedit.py cfg.json                  # change only some rows
```

- Drawings often hold several tables — **identify by content, not order**.
- `fill` rebuilds every cell from the second row as template, so **rotated header text and merged cells are lost** →
  for a few rows use `table_rowedit.py` (config `src/dst/handle/template_row/rows`; text + row height copied from the template row, all other rows untouched).
- `rows.json`: `col_widths` (optional; keep the total if the table stays on the sheet), `bold_rows` (uses the table's own bold prefix),
  `hard_wrap: false` (recommended: whole strings in cells, AutoCAD wraps by column width and re-wraps if widths change later).
- Break long part numbers at existing `-` or `/`; never insert a hyphen (it makes a wrong part number).
- Back to DWG: put the DXF **in the DWG's folder** (relative xrefs; otherwise xref layer overrides are lost),
  open it in accoreconsole (`/i x.dxf`) and `(command "_.SAVEAS" "2018" "x.dwg")`.
- Empty cells can still carry a CELLCONTENT (value type 7, empty string): "has content" must check for a real value string,
  or the `95` count is wrong → "Invalid or incomplete DXF input -- drawing discarded".
- Adding rows: update both `91` row counts (in the ACAD_TABLE header after AcDbTable, and before the first ROW in TABLECONTENT) and the `141` row-height list.

### Size formulas (measured)

```
row height        = lines × text height × 4/3 + 2 × cell margin
usable cell width = column width − 2 × cell margin      (wrap at 96% for safety)
```

AutoCAD grows rows that are too short on load but never shrinks them, so undersizing is safe.

### "It still looks wrong when I open it"

| Symptom | Cause |
|---|---|
| old content | TABLECONTENT not edited, or `*T<n>` not purged |
| empty table | TABLECONTENT BEGIN/END unbalanced, or row count ≠ cell count |
| error / needs recovery | group-code formatting: `70-79`/`170-179` as `%6d`, `90-99` as `%9d` |

---

## Rules for both routes

- **One datum per column beats one big SPECIFICATION column**: columns wrap in parallel, so more columns usually make the table *shorter*
  (21 rows: 8 columns = 1288 units tall vs 18 columns = 595). The cost is width — every column spends `2 × margin` — so ask how wide the table may be.
- **New rows go in the right category section** (CEILING / BASE / FLOORING / WALL …). No matching section → clone a section header row and add one; don't drop it into the nearest section.
- Schedules are for the contractor: internal coordination notes ("VERIFY: BOQ doesn't match sample"), attic stock, lumens/efficacy, order codes stay out. Keep driver type (integral vs remote — remote needs an access location).
- Too long for the sheet: don't implement table breaking yourself — Properties → Table Breaks = Yes.
- After editing, plot the whole sheet: table edges on the frame, no unexpected wrapping, nothing below overlapped.
