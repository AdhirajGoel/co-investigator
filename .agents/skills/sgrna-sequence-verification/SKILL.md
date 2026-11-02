---
name: sgrna-sequence-verification
description: Verify assembled sgRNA or spacer plasmids against a cloning spreadsheet and FASTA files using explicit backbone length. Use for sequence QC; checks length and both-strand spacer presence and fails on empty, invalid, missing, or ambiguous inputs.
---

# Sequence Verification

Confirm the expected non-spacer backbone length from the scientist or an identified reference. Do not infer it from a previous project. This check covers sequence length and spacer presence; full construct validation requires alignment against a complete reference.

Use a project-local Python environment with openpyxl (`requirements-tools.txt`). Set `SKILL_DIR` to the directory containing this file, then run:

```sh
.venv/bin/python "$SKILL_DIR/scripts/verify_sgRNA.py" --xlsx cloning.xlsx --fasta-dir sequences --backbone-len 1000
```

The number above is an argument example, not a recommended backbone. Replace it with the verified value.

The spreadsheet defaults to a `Plasmids` worksheet with `Plasmid` and `Spacer (final)` columns; `Gene` is optional. Use the script’s `--help` for column and sheet overrides. Each plasmid must match exactly one FASTA filename containing its ID as a distinct token. Each FASTA must contain one assembled sequence.

Use the spacer exactly as supplied, including any intentional leading base. Both forward and reverse-complement matches are valid. Empty or malformed rows, duplicate IDs, ambiguous mappings, invalid sequences, and missing files must fail the batch. Exit zero means every row passed both checks. Optional `--csv` writes a derived results table.

Report each failure and its reason. Preserve the source spreadsheet and FASTAs. Link the verification output to the experiment record and record the reference used for backbone length.

CSV reports require a new output path; an existing file is never overwritten.
