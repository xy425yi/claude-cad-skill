# Recipe: roll a DWG back to match a signed PDF

Situation: the DWG has moved on since the signed/sealed PDF was issued and has to be brought back to exactly
what was signed. Rare, but the whole pipeline is reusable (took ~1.5 h the first time).

1. **Plot**: `core.py plot dwg --layout X --out ours.pdf` (the layout's own page setup, so the output is genuinely AutoCAD's).
2. **Compare text by position**: `python scripts/pdf_posdiff.py signed.pdf <page> ours.pdf [tol_in=0.12]`
   pairs lines within ±0.12" and compares strings. Three lists: same place / different text, only in signed, only in ours.
   ⚠️ Don't compare by string counts (the Counter part of `pdf_overlay.py` is only a rough look) — counting once flagged 20 legitimate "TYP." as extras.
3. **Overlay**: `python scripts/pdf_overlay.py signed.pdf <page> ours.pdf <outdir>` → `diff.png`
   red = signed only, blue = DWG only, grey = same; hotspot cells listed at the end. Recognise stamps and xref differences yourself.
4. **Locate entities**: `core.py survey dwg --type MULTILEADER` for handles; keynote numbers are in the MLEADER's block attributes (attrs column `TAG=29;`).
   Viewport transform: DXF VIEWPORT 12/22 are DCS; real center = target point 17/27 + 12/22.
5. **Generate edits**: Python reads the survey → edits file (`ml-set-attr` / `del-handle` / `move-handle`, plus a review-box/note each).
6. **Run**: `run --readonly` → `run --save` → re-plot → posdiff again; done when it reports *0 differences*.
7. **Deliver**: pre-edit backup DWG, before/after PDFs, `diff.png`, and a change log (what changed, how many, how to view the review layer).

Needs `pip install pymupdf numpy`.
