#!/usr/bin/env python3
"""Extract tables (and optionally full text) from a PDF using pdfplumber.

Part of the `read-pdf` skill. This is a fixed, narrowly-scoped script so it can be
allowlisted without granting blanket `python3` execution. Read-only: never modifies
the source PDF.

Usage:
    python3 extract_tables.py FILE.pdf [--pages 1-20] [--text] [--no-tables]

  --pages 1-20   Limit to a page range (1-indexed, inclusive). Default: all pages.
  --text         Also print the page text (in addition to tables).
  --no-tables    Skip table extraction (use with --text for plain text via pdfplumber).
"""
import argparse
import sys


def parse_pages(spec, n_pages):
    """Return zero-indexed selected pages or raise ValueError with a fixable error."""
    if n_pages < 1:
        raise ValueError("PDF has no pages")
    if not spec:
        return range(n_pages)

    spec = spec.strip()
    if not spec:
        raise ValueError("page range is blank; use N, N-M, N-, or -M")
    if spec.count("-") > 1:
        raise ValueError(f"invalid page range {spec!r}; use N, N-M, N-, or -M")

    try:
        if "-" in spec:
            lo_text, hi_text = spec.split("-", 1)
            if not lo_text and not hi_text:
                raise ValueError
            lo = int(lo_text) if lo_text else 1
            hi = int(hi_text) if hi_text else n_pages
        else:
            lo = hi = int(spec)
    except ValueError as exc:
        raise ValueError(
            f"invalid page range {spec!r}; use positive integers such as 7, 5-20, 5-, or -20"
        ) from exc

    if lo < 1 or hi < 1:
        raise ValueError(f"page numbers must be at least 1; got {spec!r}")
    if lo > hi:
        raise ValueError(f"page range start must not exceed end; got {spec!r}")
    if lo > n_pages or hi > n_pages:
        raise ValueError(f"page range {spec!r} is outside this {n_pages}-page PDF; choose pages 1-{n_pages}")
    return range(lo - 1, hi)  # 0-indexed for pdfplumber

def main():
    ap = argparse.ArgumentParser(description="Extract tables/text from a PDF (pdfplumber).")
    ap.add_argument("pdf", help="Path to the PDF file")
    ap.add_argument("--pages", default="", help="Page range, e.g. 5-20 or 7")
    ap.add_argument("--text", action="store_true", help="Also print page text")
    ap.add_argument("--no-tables", action="store_true", help="Skip table extraction")
    args = ap.parse_args()

    try:
        import pdfplumber
    except ImportError:
        sys.exit("pdfplumber not available. Install it or fall back to pdftotext.")

    try:
        pdf = pdfplumber.open(args.pdf)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Could not open {args.pdf!r}: {e}")

    with pdf:
        try:
            idxs = parse_pages(args.pages, len(pdf.pages))
        except ValueError as exc:
            ap.error(str(exc))
        for i in idxs:
            page = pdf.pages[i]
            print(f"\n=== page {i + 1} ===")
            if args.text:
                print(page.extract_text() or "(no extractable text)")
            if not args.no_tables:
                tables = page.extract_tables()
                if not tables:
                    if not args.text:
                        print("(no tables on this page)")
                    continue
                for t_idx, t in enumerate(tables, 1):
                    print(f"--- table {t_idx} ---")
                    for row in t:
                        print(" | ".join((c or "").strip() for c in row))


if __name__ == "__main__":
    main()
