#!/usr/bin/env python3
"""Session-scoped PDF extraction cache for the read-pdf skill.

Uses pdf-inspector when available and Poppler's pdftotext as a fallback. The
source PDF is never modified. Persistent output is created only by `export`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CACHE_VERSION = 2
DEFAULT_TTL_SECONDS = 24 * 60 * 60


class PdfCacheError(RuntimeError):
    pass


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def cache_root(value: str | None) -> Path:
    root = Path(value) if value else Path(tempfile.gettempdir()) / "read-pdf-cache-v2"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def require_pdf(value: str) -> Path:
    pdf = Path(value).expanduser().resolve()
    if not pdf.is_file():
        raise PdfCacheError(f"PDF not found: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise PdfCacheError(f"Expected a .pdf file: {pdf}")
    return pdf


def file_hash(pdf: Path) -> str:
    digest = hashlib.sha256()
    with pdf.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry_dir(root: Path, digest: str) -> Path:
    return root / digest


def meta_path(entry: Path) -> Path:
    return entry / "meta.json"


def load_meta(entry: Path) -> dict:
    try:
        meta = json.loads(meta_path(entry).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PdfCacheError(f"Unreadable PDF cache at {entry}: {exc}") from exc
    if meta.get("cache_version") != CACHE_VERSION:
        raise PdfCacheError(f"Unsupported PDF cache version at {entry}")
    return meta


def write_meta(entry: Path, meta: dict) -> None:
    target = meta_path(entry)
    temporary = entry / ".meta.json.tmp"
    temporary.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, target)
    try:
        target.chmod(0o600)
    except OSError:
        pass


def touch_meta(entry: Path, meta: dict, ttl_seconds: int) -> None:
    now = time.time()
    meta["accessed_at"] = now
    meta["expires_at"] = now + ttl_seconds
    write_meta(entry, meta)


def command(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise PdfCacheError(f"Required command is unavailable: {name}")
    return executable


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise PdfCacheError(f"Command failed ({argv[0]}): {detail}")
    return result


def pdfinfo_page_count(pdf: Path) -> int:
    output = run([command("pdfinfo"), str(pdf)]).stdout
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if not match:
        raise PdfCacheError("pdfinfo did not report a page count")
    count = int(match.group(1))
    if count < 1:
        raise PdfCacheError("PDF has no pages")
    return count


def quality_reasons(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return ["no_text"]
    reasons: list[str] = []
    alphanumeric = sum(ch.isalnum() for ch in stripped)
    if alphanumeric < 10:
        reasons.append("sparse_text")
    replacement = stripped.count("\ufffd") + stripped.count("\x00")
    controls = sum(ord(ch) < 32 and ch not in "\n\r\t" for ch in stripped)
    if replacement / max(len(stripped), 1) > 0.01 or controls:
        reasons.append("suspected_garbled_text")
    return reasons


def extract_pdf_inspector(pdf: Path) -> tuple[list[dict], dict]:
    try:
        import pdf_inspector  # type: ignore
    except ImportError as exc:
        raise PdfCacheError("pdf-inspector Python package is unavailable") from exc

    try:
        result = pdf_inspector.extract_pages_markdown(str(pdf))
    except Exception as exc:  # native extension errors vary by PDF
        raise PdfCacheError(f"pdf-inspector failed: {exc}") from exc

    table_pages = {int(page) for page in getattr(result, "pages_with_tables", [])}
    column_pages = {int(page) for page in getattr(result, "pages_with_columns", [])}
    extracted: list[dict] = []
    for item in result.pages:
        page_number = int(item.page) + 1
        text = str(item.markdown or "")
        reasons = quality_reasons(text)
        if bool(item.needs_ocr) and "parser_requested_ocr" not in reasons:
            reasons.append("parser_requested_ocr")
        extracted.append(
            {
                "page": page_number,
                "text": text,
                "reasons": reasons,
                "has_table": page_number in table_pages,
                "has_columns": page_number in column_pages,
            }
        )
    return extracted, {
        "backend": "pdf-inspector",
        "is_complex": bool(getattr(result, "is_complex", False)),
    }


def extract_pdftotext(pdf: Path) -> tuple[list[dict], dict]:
    page_count = pdfinfo_page_count(pdf)
    output = run([command("pdftotext"), "-layout", str(pdf), "-"]).stdout
    parts = output.split("\f")
    if parts and not parts[-1].strip():
        parts.pop()
    if len(parts) != page_count:
        parts = []
        for page in range(1, page_count + 1):
            parts.append(
                run(
                    [
                        command("pdftotext"),
                        "-f",
                        str(page),
                        "-l",
                        str(page),
                        "-layout",
                        str(pdf),
                        "-",
                    ]
                ).stdout
            )
    extracted = [
        {
            "page": page,
            "text": text,
            "reasons": quality_reasons(text),
            "has_table": False,
            "has_columns": False,
        }
        for page, text in enumerate(parts, 1)
    ]
    return extracted, {"backend": "pdftotext", "is_complex": False}


def extract(pdf: Path, backend: str) -> tuple[list[dict], dict]:
    errors: list[str] = []
    if backend in {"auto", "pdf-inspector"}:
        try:
            return extract_pdf_inspector(pdf)
        except PdfCacheError as exc:
            errors.append(str(exc))
            if backend == "pdf-inspector":
                raise
    if backend in {"auto", "pdftotext"}:
        try:
            pages, details = extract_pdftotext(pdf)
            if errors:
                details["fallback_reason"] = errors[-1]
            return pages, details
        except PdfCacheError as exc:
            errors.append(str(exc))
    raise PdfCacheError("; ".join(errors) or f"Unsupported backend: {backend}")


def remove_entry(root: Path, entry: Path) -> None:
    try:
        entry.relative_to(root)
    except ValueError as exc:
        raise PdfCacheError(f"Refusing to remove cache outside {root}") from exc
    if entry.is_dir():
        shutil.rmtree(entry)


def purge_expired(root: Path) -> list[str]:
    removed: list[str] = []
    now = time.time()
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        try:
            meta = load_meta(entry)
        except PdfCacheError:
            continue
        if float(meta.get("expires_at", 0)) <= now:
            remove_entry(root, entry)
            removed.append(entry.name)
    return removed


def public_status(entry: Path, meta: dict, reused: bool) -> dict:
    status = {
        "backend": meta["backend"],
        "cache_key": meta["source_sha256"],
        "cache_reused": reused,
        "expires_at": meta["expires_at"],
        "page_count": meta["page_count"],
        "page_count_verified": meta["page_count_verified"],
        "pages_needing_vision": [
            page["page"] for page in meta["pages"] if page["reasons"]
        ],
        "rendered_pages": [
            page["page"] for page in meta["pages"] if page.get("render_file")
        ],
        "pages_with_tables": [
            page["page"] for page in meta["pages"] if page["has_table"]
        ],
        "pages_with_columns": [
            page["page"] for page in meta["pages"] if page["has_columns"]
        ],
    }
    fallback_reason = meta.get("backend_details", {}).get("fallback_reason")
    if fallback_reason:
        status["fallback_reason"] = fallback_reason
    return status


def ingest(
    pdf: Path,
    root: Path,
    ttl_seconds: int,
    backend: str,
    refresh: bool = False,
) -> tuple[Path, dict, bool]:
    if ttl_seconds < 1:
        raise PdfCacheError("TTL must be at least 1 second")
    purge_expired(root)
    digest = file_hash(pdf)
    entry = entry_dir(root, digest)
    if entry.is_dir() and not refresh:
        try:
            meta = load_meta(entry)
            backend_matches = backend == "auto" or meta.get("backend") == backend
            if backend_matches and len(meta.get("pages", [])) == int(meta.get("page_count", -1)):
                touch_meta(entry, meta, ttl_seconds)
                return entry, meta, True
        except PdfCacheError:
            pass
        remove_entry(root, entry)
    elif entry.exists():
        remove_entry(root, entry)

    verified_page_count = pdfinfo_page_count(pdf) if shutil.which("pdfinfo") else None
    pages, details = extract(pdf, backend)
    if not pages:
        raise PdfCacheError("Extractor returned no pages")
    if verified_page_count is not None and len(pages) != verified_page_count:
        raise PdfCacheError(
            f"Extractor returned {len(pages)} pages; pdfinfo reports {verified_page_count}"
        )
    expected = list(range(1, len(pages) + 1))
    actual = [int(page["page"]) for page in pages]
    if actual != expected:
        raise PdfCacheError(f"Extractor returned non-contiguous pages: {actual}")

    entry.mkdir(mode=0o700, parents=True)
    pages_dir = entry / "pages"
    pages_dir.mkdir(mode=0o700)
    records: list[dict] = []
    try:
        for page in pages:
            filename = f"{page['page']:06d}.txt"
            target = pages_dir / filename
            target.write_text(page.pop("text"), encoding="utf-8")
            try:
                target.chmod(0o600)
            except OSError:
                pass
            records.append({**page, "text_file": f"pages/{filename}", "render_file": None})
        now = time.time()
        meta = {
            "cache_version": CACHE_VERSION,
            "source_sha256": digest,
            "source_name": pdf.name,
            "source_path": str(pdf),
            "created_at": now,
            "accessed_at": now,
            "expires_at": now + ttl_seconds,
            "page_count": len(records),
            "page_count_verified": verified_page_count == len(records),
            "backend": details["backend"],
            "backend_details": details,
            "pages": records,
        }
        write_meta(entry, meta)
    except Exception:
        remove_entry(root, entry)
        raise
    return entry, meta, False


def parse_pages(spec: str | None, page_count: int) -> list[int]:
    if not spec:
        return list(range(1, page_count + 1))
    selected: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise PdfCacheError(f"Invalid page selection: {spec!r}")
        if "-" in part:
            if part.count("-") != 1:
                raise PdfCacheError(f"Invalid page range: {part!r}")
            start_text, end_text = part.split("-", 1)
            start = int(start_text) if start_text else 1
            end = int(end_text) if end_text else page_count
            if start > end:
                raise PdfCacheError(f"Page range start exceeds end: {part!r}")
            selected.update(range(start, end + 1))
        else:
            selected.add(int(part))
    invalid = sorted(page for page in selected if page < 1 or page > page_count)
    if invalid:
        raise PdfCacheError(f"Pages outside 1-{page_count}: {invalid}")
    return sorted(selected)


def page_record(meta: dict, page_number: int) -> dict:
    return meta["pages"][page_number - 1]


def page_text(entry: Path, record: dict) -> str:
    return (entry / record["text_file"]).read_text(encoding="utf-8")


def ensure_cache(args: argparse.Namespace) -> tuple[Path, dict, bool]:
    pdf = require_pdf(args.pdf)
    root = cache_root(args.cache_root)
    return ingest(pdf, root, args.ttl_seconds, args.backend, getattr(args, "refresh", False))


def cmd_ingest(args: argparse.Namespace) -> None:
    entry, meta, reused = ensure_cache(args)
    emit(public_status(entry, meta, reused))


def cmd_read(args: argparse.Namespace) -> None:
    entry, meta, _ = ensure_cache(args)
    for page_number in parse_pages(args.pages, meta["page_count"]):
        record = page_record(meta, page_number)
        print(f"\n=== page {page_number} ===")
        text = page_text(entry, record).rstrip()
        print(text or "(no extractable text)")
        if record["reasons"]:
            print(f"[[vision required: {', '.join(record['reasons'])}]]")
        layout_flags = [
            label
            for label, present in (
                ("table", record["has_table"]),
                ("columns", record["has_columns"]),
            )
            if present
        ]
        if layout_flags:
            print(f"[[visual layout review recommended: {', '.join(layout_flags)}]]")
        if record.get("render_file"):
            print(f"[[render: {entry / record['render_file']}]]")


def snippet(text: str, start: int, length: int = 280) -> str:
    left = max(0, start - length // 3)
    right = min(len(text), left + length)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def cmd_search(args: argparse.Namespace) -> None:
    entry, meta, _ = ensure_cache(args)
    query = args.query.casefold().strip()
    if not query:
        raise PdfCacheError("Search query is blank")
    terms = [term for term in re.findall(r"\w+", query) if len(term) > 1]
    hits: list[dict] = []
    for record in meta["pages"]:
        text = page_text(entry, record)
        folded = text.casefold()
        phrase_at = folded.find(query)
        score = 1000 if phrase_at >= 0 else sum(folded.count(term) for term in terms)
        if score:
            first = phrase_at if phrase_at >= 0 else min(
                (folded.find(term) for term in terms if folded.find(term) >= 0), default=0
            )
            hits.append(
                {
                    "page": record["page"],
                    "score": score,
                    "snippet": snippet(text, first),
                    "needs_vision": bool(record["reasons"]),
                    "has_table": record["has_table"],
                    "has_columns": record["has_columns"],
                    "needs_visual_review": bool(
                        record["reasons"] or record["has_table"] or record["has_columns"]
                    ),
                }
            )
    hits.sort(key=lambda hit: (-hit["score"], hit["page"]))
    emit({"query": args.query, "hits": hits[: args.limit]})


def cmd_render(args: argparse.Namespace) -> None:
    pdf = require_pdf(args.pdf)
    entry, meta, _ = ensure_cache(args)
    if args.pages:
        pages = parse_pages(args.pages, meta["page_count"])
    else:
        pages = [page["page"] for page in meta["pages"] if page["reasons"]]
        if not pages:
            raise PdfCacheError("No pages need vision; specify --pages to render others")
    renders_dir = entry / "renders"
    renders_dir.mkdir(mode=0o700, exist_ok=True)
    executable = command("pdftoppm")
    rendered: list[dict] = []
    for page_number in pages:
        record = page_record(meta, page_number)
        relative = f"renders/page-{page_number:06d}.png"
        target = entry / relative
        if not target.is_file() or args.refresh_render:
            prefix = target.with_suffix("")
            run(
                [
                    executable,
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    "-singlefile",
                    "-r",
                    str(args.dpi),
                    "-png",
                    str(pdf),
                    str(prefix),
                ]
            )
        record["render_file"] = relative
        rendered.append({"page": page_number, "path": str(target)})
    touch_meta(entry, meta, args.ttl_seconds)
    emit({"rendered": rendered})


def cmd_export(args: argparse.Namespace) -> None:
    entry, meta, _ = ensure_cache(args)
    unresolved = [page["page"] for page in meta["pages"] if page["reasons"]]
    if unresolved:
        raise PdfCacheError(
            "Refusing incomplete Markdown export; visually verify/reconstruct pages: "
            + ", ".join(map(str, unresolved))
        )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    for record in meta["pages"]:
        chunks.append(f"<!-- Page {record['page']} -->\n\n{page_text(entry, record).strip()}")
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write("\n\n".join(chunks).rstrip() + "\n")
    except FileExistsError as exc:
        raise PdfCacheError("Export destination already exists; choose a new path") from exc
    emit({"output": str(output), "page_count": meta["page_count"], "verified_complete": True})


def cmd_clean(args: argparse.Namespace) -> None:
    root = cache_root(args.cache_root)
    if args.expired:
        emit({"removed": purge_expired(root)})
        return
    if not args.pdf:
        raise PdfCacheError("Provide a PDF or use --expired")
    pdf = require_pdf(args.pdf)
    entry = entry_dir(root, file_hash(pdf))
    existed = entry.is_dir()
    remove_entry(root, entry)
    emit({"removed": existed, "cache_key": entry.name})


def add_cache_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cache-root", help=argparse.SUPPRESS)
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    parser.add_argument(
        "--backend",
        choices=("auto", "pdf-inspector", "pdftotext"),
        default="auto",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Create or reuse a temporary PDF cache")
    ingest_parser.add_argument("pdf")
    ingest_parser.add_argument("--refresh", action="store_true")
    add_cache_options(ingest_parser)
    ingest_parser.set_defaults(func=cmd_ingest)

    read_parser = subparsers.add_parser("read", help="Print cached text for selected pages")
    read_parser.add_argument("pdf")
    read_parser.add_argument("--pages", help="1-indexed pages such as 1,3,5-8")
    add_cache_options(read_parser)
    read_parser.set_defaults(func=cmd_read)

    search_parser = subparsers.add_parser("search", help="Search cached page text")
    search_parser.add_argument("pdf")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=8)
    add_cache_options(search_parser)
    search_parser.set_defaults(func=cmd_search)

    render_parser = subparsers.add_parser("render", help="Render selected pages for vision")
    render_parser.add_argument("pdf")
    render_parser.add_argument("--pages", help="1-indexed pages such as 1,3,5-8")
    render_parser.add_argument("--dpi", type=int, default=180)
    render_parser.add_argument("--refresh-render", action="store_true")
    add_cache_options(render_parser)
    render_parser.set_defaults(func=cmd_render)

    export_parser = subparsers.add_parser("export", help="Write complete cached text as Markdown")
    export_parser.add_argument("pdf")
    export_parser.add_argument("output")
    add_cache_options(export_parser)
    export_parser.set_defaults(func=cmd_export)

    clean_parser = subparsers.add_parser("clean", help="Remove one PDF cache or expired caches")
    clean_parser.add_argument("pdf", nargs="?")
    clean_parser.add_argument("--expired", action="store_true")
    clean_parser.add_argument("--cache-root", help=argparse.SUPPRESS)
    clean_parser.set_defaults(func=cmd_clean)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except (PdfCacheError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
