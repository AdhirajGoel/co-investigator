#!/usr/bin/env python3
"""
verify_sgRNA.py — verify cloned sgRNA / spacer plasmids against sequencing fasta files.

For each plasmid row in a cloning spreadsheet, check:
  1. Sequence length matches the expected value (backbone length + spacer length).
  2. The spacer is present in the assembled sequence, on either strand.

The verifier is deliberately fail-closed: empty input, invalid spacers, missing or
ambiguous FASTA mappings, and malformed rows cannot produce an ALL PASS result.
"""
import argparse
from collections import Counter
import csv
import glob
import os
import re
import sys

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl not found. Install requirements-tools.txt into the project .venv and run with .venv/bin/python.")


RESULT_FIELDS = [
    "plasmid",
    "gene",
    "spacer_len",
    "seq_len",
    "len_ok",
    "found",
    "strand",
    "expected",
    "verdict",
    "reason",
]


def revcomp(s):
    return s.translate(str.maketrans("ACGTacgt", "TGCAtgca"))[::-1]


def load_fasta(path):
    seq = []
    headers = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                headers += 1
                if headers > 1:
                    raise ValueError("Expected one assembled sequence per FASTA")
                continue
            if headers != 1 or re.fullmatch(r"[ACGTNacgtn]+", line) is None:
                raise ValueError("Invalid FASTA sequence or missing header")
            seq.append(line)
    if headers != 1 or not seq:
        raise ValueError("FASTA contains no assembled sequence")
    return "".join(seq).upper()


def find_col(header, wanted, override, optional=False):
    """Return a unique column index, or exit with an actionable schema error."""
    target = (override if override is not None else wanted).strip().casefold()
    names = [str(value).strip().casefold() if value is not None else "" for value in header]
    matches = [i for i, name in enumerate(names) if name == target]
    if not matches and override is None:
        matches = [i for i, name in enumerate(names) if target in name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        sys.exit(f"Ambiguous column '{override or wanted}'. Headers: {header}")
    if optional and override is None:
        return None
    sys.exit(
        f"Column '{override or wanted}' not found. Headers: {header}\n"
        f"Pass it explicitly with the matching --*-col flag."
    )


def _filename_contains_token(path, token):
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.search(
        rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
        stem,
        flags=re.IGNORECASE,
    ) is not None


def resolve_fasta(plasmid_id, fasta_paths):
    """Resolve exactly one FASTA by an unambiguous filename token."""
    substring_matches = [
        path
        for path in fasta_paths
        if plasmid_id.casefold() in os.path.basename(path).casefold()
    ]
    exact_matches = [
        path for path in substring_matches if _filename_contains_token(path, plasmid_id)
    ]
    if len(exact_matches) == 1:
        return exact_matches[0], ""
    if len(exact_matches) > 1:
        return None, "AMBIGUOUS_FASTA"
    return None, "NO_FASTA"


def write_csv(results, path):
    try:
        handle = open(path, "x", newline="", encoding="utf-8")
    except OSError as exc:
        sys.exit(f"Cannot create CSV; choose a new writable path: {exc}")
    with handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"Wrote {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--fasta-dir", required=True)
    ap.add_argument("--sheet", default="Plasmids")
    ap.add_argument("--backbone-len", type=int, required=True)
    ap.add_argument("--plasmid-col", default=None)
    ap.add_argument("--spacer-col", default=None)
    ap.add_argument("--gene-col", default=None)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    if args.backbone_len < 0:
        ap.error("--backbone-len must be non-negative")
    if not os.path.isdir(args.fasta_dir):
        ap.error(f"FASTA directory does not exist: {args.fasta_dir}")

    source_wb = openpyxl.load_workbook(args.xlsx, data_only=False)
    wb = openpyxl.load_workbook(args.xlsx, data_only=True)
    if args.sheet not in wb.sheetnames:
        ap.error(f"Sheet '{args.sheet}' not found. Sheets: {wb.sheetnames}")
    ws = wb[args.sheet]
    # Formula-only rows must remain visible even when Excel has not cached results.
    rows = [pair for pair in zip(source_wb[args.sheet].iter_rows(), ws.iter_rows())
            if any(cell.value is not None for cell in pair[0])]
    source_wb.close()
    wb.close()
    if not rows:
        ap.error(f"Sheet '{args.sheet}' has no non-empty rows")

    header = tuple(cell.value for cell in rows[0][1])
    if not any(value is not None and str(value).strip() for value in header):
        ap.error(f"Sheet '{args.sheet}' has no header row")

    pi = find_col(header, "Plasmid", args.plasmid_col)
    si = find_col(header, "Spacer (final)", args.spacer_col)
    gi = find_col(header, "Gene", args.gene_col, optional=True)

    data = []
    for source, cached in rows[1:]:
        for index in (pi, si):
            cell, value = source[index], cached[index]
            if cell.data_type == "f" and (value.data_type == "e" or value.value is None or not str(value.value).strip()):
                ap.error(f"Cell {cell.coordinate} has no usable cached formula value; recalculate and save the workbook or replace the formula with its value")
        data.append(tuple(cell.value for cell in cached))
    if any(pi >= len(row) or row[pi] is None or not str(row[pi]).strip() for row in data):
        ap.error("Every non-empty data row must contain a plasmid ID")
    fasta_paths = sorted(
        glob.glob(os.path.join(args.fasta_dir, "*.fasta"))
        + glob.glob(os.path.join(args.fasta_dir, "*.fa"))
        + glob.glob(os.path.join(args.fasta_dir, "*.fas"))
    )

    mappings = [resolve_fasta(str(row[pi]).strip(), fasta_paths) for row in data]
    fasta_uses = Counter(os.path.realpath(path) for path, _ in mappings if path)
    results = []
    all_pass = bool(data)
    seen_ids = set()
    for row, (fasta_path, mapping_status) in zip(data, mappings):
        plasmid = str(row[pi]).strip()
        gene = str(row[gi]).strip() if gi is not None and row[gi] is not None else ""
        raw_spacer = row[si] if si < len(row) else None
        spacer = str(raw_spacer).strip().upper() if raw_spacer is not None else ""
        base = dict(plasmid=plasmid, gene=gene)

        if plasmid.casefold() in seen_ids:
            results.append(
                dict(
                    **base,
                    spacer_len=len(spacer),
                    seq_len="",
                    len_ok=False,
                    found=False,
                    strand="-",
                    expected="",
                    verdict="CHECK",
                    reason="DUPLICATE_PLASMID_ID",
                )
            )
            all_pass = False
            continue
        seen_ids.add(plasmid.casefold())

        if not spacer or re.fullmatch(r"[ACGT]+", spacer) is None:
            results.append(
                dict(
                    **base,
                    spacer_len=len(spacer),
                    seq_len="",
                    len_ok=False,
                    found=False,
                    strand="-",
                    expected="",
                    verdict="CHECK",
                    reason="INVALID_SPACER: expected non-empty A/C/G/T sequence",
                )
            )
            all_pass = False
            continue

        spacer_len = len(spacer)
        expected = args.backbone_len + spacer_len
        if fasta_path and fasta_uses[os.path.realpath(fasta_path)] > 1:
            fasta_path, mapping_status = None, "AMBIGUOUS_FASTA"
        if not fasta_path:
            results.append(
                dict(
                    **base,
                    spacer_len=spacer_len,
                    seq_len="",
                    len_ok=False,
                    found=False,
                    strand=mapping_status,
                    expected=expected,
                    verdict="CHECK",
                    reason=mapping_status,
                )
            )
            all_pass = False
            continue

        try:
            seq = load_fasta(fasta_path)
        except (OSError, UnicodeError, ValueError) as exc:
            results.append(
                dict(
                    **base,
                    spacer_len=spacer_len,
                    seq_len="",
                    len_ok=False,
                    found=False,
                    strand="FASTA_ERROR",
                    expected=expected,
                    verdict="CHECK",
                    reason=f"FASTA_READ_ERROR: {exc}",
                )
            )
            all_pass = False
            continue

        seq_len = len(seq)
        len_ok = seq_len == expected
        fwd = spacer in seq
        rev = revcomp(spacer) in seq
        found = fwd or rev
        strand = "fwd" if fwd else ("rev" if rev else "-")
        reasons = []
        if not len_ok:
            reasons.append(f"length {seq_len} != expected {expected}")
        if not found:
            reasons.append("spacer absent on both strands")
        verdict = "OK" if len_ok and found else "CHECK"
        if verdict != "OK":
            all_pass = False
        results.append(
            dict(
                **base,
                spacer_len=spacer_len,
                seq_len=seq_len,
                len_ok=len_ok,
                found=found,
                strand=strand,
                expected=expected,
                verdict=verdict,
                reason="; ".join(reasons),
            )
        )

    hdr = (
        f"{'Plasmid':10} {'Gene':12} {'sp_len':6} {'seq_len':8} "
        f"{'expected':9} {'len_ok':7} {'found':6} {'strand':16} VERDICT"
    )
    print(hdr)
    print("-" * len(hdr))
    for result in results:
        print(
            f"{result['plasmid']:10} {result['gene']:12} "
            f"{str(result['spacer_len']):6} {str(result['seq_len']):8} "
            f"{str(result['expected']):9} {str(result['len_ok']):7} "
            f"{str(result['found']):6} {result['strand']:16} {result['verdict']}"
            + (f" — {result['reason']}" if result["reason"] else "")
        )
    print("-" * len(hdr))
    npass = sum(result["verdict"] == "OK" for result in results)
    if not data:
        print("0/0 passed — NO PLASMIDS TO CHECK")
    else:
        print(
            f"{npass}/{len(results)} passed both checks — "
            + ("ALL PASS" if all_pass else "SOME NEED REVIEW")
        )

    if args.csv:
        write_csv(results, args.csv)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
