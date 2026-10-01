"""Merge single-sheet PDFs into one set and verify every page.

    python merge_pdfs.py out.pdf sheet1.pdf sheet2.pdf ...

DWG To PDF exports OFF layers as *hidden* PDF layers (OCG /OFF). insert_pdf drops that hidden state,
so geometry you switched off reappears in the merged set. After merging, each page is rendered at low
dpi and compared with its source; a mismatch means that sheet must be re-plotted with
(freeze-off-layers) in core.py plot --pre. Exit code 1 on mismatch."""
import fitz, hashlib, sys


def sig(page):
    return hashlib.md5(page.get_pixmap(dpi=30).tobytes()).hexdigest()


def build(sheets, out):
    d = fitz.open()
    for s in sheets:
        d.insert_pdf(fitz.open(s))
    d.save(out)
    merged = fitz.open(out)
    bad = [s for i, s in enumerate(sheets) if sig(merged[i]) != sig(fitz.open(s)[0])]
    print('OK' if not bad else 'MISMATCH', merged.page_count, 'pages ->', out, bad)
    return bad


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sys.exit(1 if build(sys.argv[2:], sys.argv[1]) else 0)
