---
name: read-pdf
description: Reliably read, search, summarize, answer questions about, or convert local PDF files using verified per-page extraction and a temporary session cache. Use for PDF Q&A, follow-up questions, text or table extraction, scanned or mixed PDFs, and explicit PDF-to-Markdown requests. Prefer the separate PDF artifact workflow for creating, editing, filling, or visually reviewing PDF files.
---

# Read PDF

Use a temporary, hash-keyed extraction cache so follow-up questions reuse verified page content. Keep ordinary reading and Q&A artifact-free. Write a Markdown file only when the user explicitly asks to save or export one.

## Start or reuse a session

Set `SKILL_DIR` to this skill's directory, then run:

```bash
python3 "$SKILL_DIR/pdf_cache.py" ingest "$PDF"
```

The JSON result reports the backend, verified page count, cache reuse, expiry, pages that need vision, and pages with tables or columns. The helper prefers `pdf-inspector`, falls back to `pdftotext`, and never modifies the source PDF. Do not install missing dependencies silently.

Use the same command on later turns. An unchanged PDF reuses its cache; a changed file receives a new hash and cache entry.

## Find and read content

Search before loading a large document into context:

```bash
python3 "$SKILL_DIR/pdf_cache.py" search "$PDF" "query terms" --limit 8
python3 "$SKILL_DIR/pdf_cache.py" read "$PDF" --pages 4,7-10
```

For a short PDF, `read` without `--pages` returns every page. Page numbers are always 1-indexed.

## Handle uncertain or visual pages

Treat every page listed in `pages_needing_vision` as unresolved text until checked. Render only the relevant pages, in modest batches:

```bash
python3 "$SKILL_DIR/pdf_cache.py" render "$PDF" --pages 4,7-10
```

Inspect the returned PNG paths with an available vision reader. Also inspect rendered pages when the answer depends on tables, figures, formulas, handwriting, multi-column order, small print, or exact layout. If vision or OCR is unavailable, state which pages remain unresolved and do not claim complete coverage.

For detailed tables, run the bundled fallback from the project root using the environment containing pdfplumber (`requirements-tools.txt`):

```bash
.venv/bin/python "$SKILL_DIR/extract_tables.py" "$PDF" --pages 5-20 --text
```

If that environment or pdfplumber is unavailable, report the missing optional tool and use the verified cache or rendered pages; do not install globally.

## Answer questions

Before answering:

1. Confirm the cache page count matches the PDF.
2. Search and read the pages relevant to the question.
3. Inspect any relevant page that needs vision or whose layout carries meaning.
4. Cite source page numbers in the answer.
5. Report unresolved pages or extraction limitations instead of guessing.

Reuse the cache for follow-up questions in the same task. Re-ingest automatically after cache expiry, a source-file change, or cache loss.

## Export only on explicit request

When the user explicitly requests a saved Markdown copy, use their destination or `~/Downloads` when none is supplied:

```bash
python3 "$SKILL_DIR/pdf_cache.py" export "$PDF" "$OUTPUT_MD"
```

Choose a new output path; export refuses to overwrite an existing file. Export also fails when pages still need vision, preventing silent partial Markdown. After visually reconstructing such pages, create the requested Markdown from the cached native text and verified visual content, preserving page markers, headings, lists, tables, captions, footnotes, and links as far as the source supports.

## Cache lifecycle

The default cache lives under the system temporary directory with a 24-hour idle TTL. It is internal state, not a user-facing artifact. Remove expired entries opportunistically:

```bash
python3 "$SKILL_DIR/pdf_cache.py" clean --expired
```

Run `python3 "$SKILL_DIR/pdf_cache.py" clean "$PDF"` only when the user asks to forget the document immediately. Do not delete unrelated cache entries.

## Report

For Q&A, report the pages consulted, whether native extraction or vision was used, and any limitations. For export, report the output path and verification performed. Do not expose internal cache paths unless they are needed to inspect rendered pages or diagnose a failure.
