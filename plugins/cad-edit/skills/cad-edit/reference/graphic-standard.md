# Drafting standard — interior elevations & enlarged plans

Rules distilled from an architect's review of AI-drafted interior elevations (fitting rooms, restrooms) on
US construction documents. **Read before drawing a new elevation; go through the checklist at the end
when done.** Numbers are model inches at 1:24 (1/2" = 1'-0") unless noted — scale them for other scales.
Where the office's drawings do something differently, **the drawings win**: copy what's already there.

## 1. Structure: block + loose annotation

- Each elevation is a block (`elevationN`), origin = bottom-left (floor line y=0, left wall face x=0). The block holds **geometry only** — no text, dims, datums or tags.
- Optionally place a second copy outside the viewport next to a plan copy of that wall (xref insert + XCLIP to the room, rotated to the wall direction) to line things up.
- Annotation (mleaders, dims, datums, room tags) lives loose in model space and is **cloned from existing ones** (`_.COPY` then change text/attributes) — never entmake a new style.

## 2. Layers & line weights (inside the block)

Typical elevation layer set (use the office's names):

| Role | Weight | Used for |
|---|---|---|
| Outline | heaviest | outer profile only: floor line, ceiling line, the two wall corners |
| Object | medium | object outlines: openings, casework, fixtures, pier corners, mirror frames |
| Surface | fine | tile joints, casings, mirror surface, finish lines |
| Hidden | hidden linetype | things not visible: a pocket door's open position, a recess to be removed. **Write the linetype explicitly** (group 6); don't rely on the layer |
| Mask | wipeout | occlusion |

Rule: **the further out and the more "solid", the heavier; the further in and the more decorative, the lighter.** Don't put two nearly identical weights side by side — the hierarchy stops reading.

## 3. Occlusion

What is in front hides what is behind: the rear line **breaks** where it's covered.
- A pier corner line stops where the lavatory is in front of it.
- Tile joints stop at the casing, they don't run through it.
- Unsure what's in front? Check the plan: nearer to the viewer is in front.
- Hidden lines mean "exists but concealed", not "behind" — things hidden behind other objects are simply not drawn.

## 4. Datum (level) tags

- Clone the drawing's datum block; multi-line ATTRIBs → change every code-1 pair.
- **Every elevation has** FINISHED FLOOR `0'-0" A.F.F.` and B.O. CEILING (add `(VIF)` if field-measured); add T.O. WAINSCOT etc. where finishes change.
- **Alignment**: all datums in one column of elevations share the same x, a fixed distance in from the grid cell's right frame line. Derive each elevation's x0 from it (e.g. elevation right edge 4" left of the datum).
- The datum line runs from the elevation's right edge to the tag, text above the line, right-aligned.

## 5. Notes (mleaders)

- Clone an existing note mleader; change text with `ml-set-text`; line breaks `\P` built with `(chr 92)`.
- **One column to the right of the elevation**, text left-aligned on one x (e.g. elevation right edge + 12").
- **Sort top-to-bottom by arrowhead height** — higher targets higher — so leaders never cross.
- A note names only what the arrow touches ("WALL" not "WALL AND CEILING" when it points at the wall).
- ≤ 3 lines per note (prefer ≤ 2); tighten wording ("VERIFY W/") instead of widening. A blank line between notes.
- **Horizontal leaders whenever possible**: the dogleg sits at the first text line's mid-height, so put the note's base y at the target's height. With an edge as target (wall, tile line, door leaf, mirror edge) that almost always works.
- If it can't be horizontal, make it **clearly angled (≥ 15°)**: `by = target_y − tan15° × (dogleg_x − target_x)`. Almost-horizontal is the ugliest.
- The leader meets the landing at an **obtuse** angle — the arrow heads away from the text.
- Notes don't overlap each other or the datum text band (roughly datum level ± 4" at 1:24). Estimate line count by measuring the font (e.g. PIL `getlength`) against the note width.
- Leaders don't cross other notes' text, room tags, or dimension text; crossing a door leaf is OK but avoid pulls and slide arrows.
- Don't repeat the same information on two elevations.
- **Arrowhead exactly on the edge, zero gap**: compute from geometry (circle `tip = c + r·unit(landing − c)`; segment: project onto the line; add the xref insertion offset if the target is in an xref). Check at ≥ 200 dpi.

## 6. Tags

- Door tags in elevations: clone an existing one, centered on the leaf, a bit high, clear of pulls/arrows/leaders; numbers must match the door schedule.
- Room tags in elevations: same height across a row, centered on the elevation. Ask first — some offices don't put room tags in elevations when the plan already has them.
- Names/numbers must match the plans; survey all room-number/name attributes across the set when one changes.
- A room tag placed outside a small room gets a leader back into it: text-less mleader, dot arrowhead, no dogleg, entering the room perpendicular from the tag's edge, dot in empty floor area. Clone an existing one and fix its context scale if cloning from a different-scale drawing.

## 7. Dimensions

**Dimension what the contractor builds. Fixtures (plumbing, hardware, mirrors) get location and mounting height only, never their own size** — the manufacturer sets that. Lavatory: counter height and centerline, not bowl width; mirror size goes in the note; toilet: centerline to wall + seat height.
- Location dims as one continuous string below the elevation (wall → WC centerline → lav centerline). **Pick the dimension points on the fixture itself** so the extension line visibly belongs to it.
- WC centerline to side wall: ADA 16"–18" (2010 ADA 604.2), IPC minimum 15" (405.3.1).
- **Keep all annotation ≥ 1/2" (paper) from frames and grid lines.** If there's no room, move inward, don't squeeze outward.
- Vertical dims go in a clear vertical corridor that no horizontal leader passes through. If there's none, move a note to another elevation.
- **Existing conditions: either no dimension or dimension with (VIF).** New items: design dims, no VIF.
  `(setvar "DIMPOST" " (VIF)\X")` before DIMLINEAR, reset after (keeps alternate units stacked correctly); build `\X` with `(chr 92)`.
- **Always dimension accessibility mounting heights, even in non-accessible rooms**: flush valve, seat height, TP holder height + distance, counter height, mirror bottom, grab bars. Put them outside left or tight beside the fixture, not where right-side leaders pass.
- Clone the drawing's dim style (annotative → set `CANNOSCALE` first), on the dimension layer. Extension lines never run across the whole elevation (write a height in the note instead). Dim text never sits on geometry — move the dim line, not the text.

## 8. Hatching

- **Copy existing hatches**: same material → same pattern/scale/layer as elsewhere on the sheet. Read an existing hatch's pattern lines with ezdxf and entmake them unchanged (DXF 45/46 offsets are world vectors, dashes already scaled).
- Boundaries go around objects in front (lavatory, faucet) — hatch never runs through fixtures.
- Tile wainscot and GWB: no hatch, just the boundary lines.

## 9. Fixtures

- Reuse the office's fixture blocks (elevation + plan), extracted as bare geometry — don't -INSERT whole DWGs (unit scaling).
- Center a faucet on its **insertion point** (= bowl center), not its bounding box (spouts are asymmetric).
- Fixture blocks that are dynamic (visibility states hiding side views): reading the definition with ezdxf returns hidden segments too — compare with a plot and keep only the visible ones.
- New mirror: vertical rectangle centered on the lav, bottom at tile top or per accessibility height.
- **Pocket doors shown closed**: leaf = opening line, pull + slide arrow toward the pocket; open position as a hidden-line rectangle with a note. Casing as one continuous U profile, not three rectangles (corners show little boxes).

## 10. Plans

- On finish plans / RCPs furniture, fixtures and casework show **grey hidden** — do it via the host drawing's overrides on the xref layers (color + HIDDEN linetype). Newly added furniture layers need the same override; overrides are per sheet, so check the other sheets.
- New fixtures solid; to-be-removed dashed on demo layers; replacing in place: old dashed on demo, new solid on new.

## 11. After every edit — knock-on check

Any change can push something else out of place. **Re-plot the whole sheet, not just the cell you edited.** Typical cases:
- A longer spec makes a schedule row taller, the table grows down into the key notes below → move the notes (and shrink their frame) rather than overflow the border.
- Room tags switched from 1 to 3 lines each grew taller → check every one for overlaps with walls, stairs, equipment.
- A table gained a row → is there still space below?

Method: plot → crop 200–300 dpi images around every changed object into a contact sheet → look at each → look at the whole sheet once more. **Things that grew: look below and right. Things that moved: look around the new spot.**

## 12. Checklist before delivering

1. Outline layer only on each elevation's outer profile.
2. Occluded lines broken; hidden lines have an explicit linetype.
3. Datums aligned per column; every elevation has floor + ceiling.
4. Notes in one column, sorted by target height, ≤ 3 lines, no overlaps, clear of datum text, arrows on edges.
5. No crossing leaders; nothing through tags, dims or other notes.
6. Room tags (if any) same height per row, centered.
7. No extension line across an elevation.
8. Existing dims carry (VIF); accessibility heights present; **no fixture sizes dimensioned**; faucets centered; masonry hatched.
9. Sets with revision clouds: go through §13.
10. Plot, crop per cell at 150 dpi and check 1–9 yourself; fix and re-check before showing anyone. Show only the final round.

## 13. Revision clouds & deltas

**Baseline**
- Compare against the **last issued, signed/sealed** set — not your own later plots; they differ.
- New sheets: cloud the whole sheet. Existing sheets: cloud only changes. Title-block issue rows aren't clouded.
- Text: word-level diff with PyMuPDF (a re-rendered signed PDF makes pixel diffs noisy). Graphics: overlay old = red, new = blue.
- **Unchanged content that only moved (pushed down by something above) is not clouded; unchanged text that gained a strike-through is.**

**Style**
- A dedicated cloud layer, not matched by any freeze wildcard in your plot `--pre`.
- Calligraphy LWPOLYLINE: every arc bulge 0.520567, start width 0, end width = 0.1 × chord (matches REVCLOUD style Calligraphy).
- **All arcs in the set are the same size** (e.g. 0.25" chord on paper): each side gets the whole number of arcs closest to that chord — short sides too.
- Closed polygon CCW + positive bulge = arcs bulge outward.

**Tight clouds**
- Cloud edge = actual extents of the changed content (text + keynote symbols + graphics, measured on a plot with the cloud layer frozen) plus ~0.02". Don't run out to the column width.
- Whole table changed: the edge sits on the table frame. Whole plan changed: hug the outermost content (dims, labels, street names count).
- Single-line keynotes (~0.16" leading): hug that line; arcs bulge into the gaps, not onto the next line. If you can't cut between lines, include the whole note.
- Whole-sheet clouds: arcs bulging outward can be clipped by the PDF plot area — put chords on the border / title-block line with arcs outward only if they stay inside the plot clip; otherwise pull inside.

**Delta**
- **Outside the cloud**, preferably top-right, close (~0.04") but not touching the cloud, any text or any line.
- Search: obstacles = all content + each cloud's interior + its outer arc band; try top-right, then bottom-right, top-left, bottom-left. For whole-sheet clouds use empty space in the title-block column.
- Insert in paper space at scale 1; in the console `(command "_.PSPACE")` before `-INSERT`.

**Check**: crop each delta into a contact sheet — outside, top-right, not touching; then the whole sheet — no cloud on text, arcs uniform.

## 14. Everything on the sheet is explained

Anything a reader could wonder "what is that?" about gets a note: what it is + where the spec is,
e.g. "UNDER-SHELF TASK LIGHT (TL), TYP.; SEE LIGHTING SCHEDULE ON A-141".
- Symbols showing through from other disciplines/xrefs whose tag layer is off on this sheet especially need one.
- After each change (or turning a layer on), check: does every newly visible thing have a note or tag?
- Put the note in clear space outside the object; short leader landing on the object; no crossings.

## Schedules — after changing row count

- Schedules often sit in a frame drawn by a dynamic block; **stretch the frame with the table** (`dynset <frame> "Distance2" …` with `--dyn`) or the old bottom edge leaves a line through the table. Measure row spacing on the plot against `tblrowh`.
- Loose symbols in a SYMBOL column move down with their rows; select everything below the insertion point.
- **After changing column widths, measure**: AutoCAD enforces a minimum width (two-line rotated headers ≈ 0.375"), so the value you set may not take. On the plot check table edges coincide with the frame and the longest row doesn't wrap unexpectedly.
