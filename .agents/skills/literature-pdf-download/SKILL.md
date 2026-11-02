---
name: literature-pdf-download
description: Retrieve and validate full-text scientific PDFs by PMID, DOI, or bibliography, preserving per-paper provenance and unresolved-paper records. Use for collecting literature; use read-pdf for reading downloaded files.
---

# Literature PDF Download

Read the project’s collaboration and sharing rules. Use existing valid downloads before network retrieval. Set `SKILL_DIR` to this skill’s directory. Read each script’s `--help` before first use. Keep corpus artifacts under a scientist-selected directory, normally `literature/<topic>/` in the project.

## Establish the corpus

Create `records.json` under the corpus root. Each record needs a stable unique `id`, a PMID or DOI, a safe relative `section`, an absolute `dest` within the corpus root, `status: "pending"`, and an empty `attempts` array. Include citation metadata when known. Never use an identifier or title directly as an unchecked filename.

Example schema (replace every illustrative value):

```json
[{"id":"paper-1","doi":"10.example/replace-with-a-real-doi","section":"background","dest":"/path/to/corpus/background/paper-1.pdf","status":"pending","attempts":[]}]
```

## Open routes first

1. Run `python3 "$SKILL_DIR/scripts/get_routes.py" records.json --out routes.json`. It queries Europe PMC. Optional `--email` enables Unpaywall for unresolved DOIs; obtain the scientist’s own contact email and keep it out of tracked artifacts. A missing lookup remains unresolved, not proof of a paywall.
2. Merge only `oa`, `pmcid`, `pdf_url`, and `host` from routes into records by exact `id`. Preserve destinations, sections, metadata, and attempt history. Never fabricate a successful route.
3. Run `python3 "$SKILL_DIR/scripts/fetch_oa.py" records.json --root /path/to/corpus`. It tries Europe PMC PDF rendering and the discovered direct PDF URL. It validates the manifest before downloading, preserves existing valid files, uses temporary downloads, and writes records plus manifests. `pdfinfo` from Poppler is required to mark a PDF verified.
4. If a publisher offers a legitimate direct PDF that open routes missed, set `pdf_url` to the inspected HTTPS URL, record its source, and rerun the downloader for that record. Do not overwrite a verified file.

## Browser and institutional routes

Browser access is optional and requires the scientist’s direction. Prefer the host’s dedicated browser capability. Without existing authentication, use an isolated browser. Never inspect or reuse personal tabs, cookies, saved profiles, or extensions merely because they are available.

If the scientist explicitly chooses the bundled Chrome route, install this skill’s pinned dependencies with `npm ci --prefix "$SKILL_DIR"`, then launch a dedicated profile with `bash "$SKILL_DIR/scripts/launch_chrome.sh"`. Keep the printed profile path and exact PID for cleanup. Connect only to that task-owned browser:

```sh
node "$SKILL_DIR/scripts/browser_grab.mjs" records.json --root /path/to/corpus --profile TASK_PROFILE --port PORT
```

The helper checks the exact dedicated process arguments and debugging-port ownership before attaching. It follows DOI or PMID landing pages, captures PDF responses and downloads, and validates temporary files with Poppler before publishing without replacement. It reports unresolved items. It never automates CAPTCHA interactions. Let the scientist handle sign-in or a challenge in that dedicated session; stop if access remains unavailable. Never bypass subscriptions or access controls. Use the same helper after the scientist completes an authorized sign-in. Close only the recorded browser PID when finished and authorized.

## Reconcile

After any download route run:

```sh
python3 "$SKILL_DIR/scripts/corpus.py" records.json --root /path/to/corpus
```

This verifies PDF signatures, minimum size, readable positive page count, destination containment, duplicate identities, and reconciliation between records and files. It writes `manifest.json`, `MANIFEST.md`, and `MISSING.md` for unresolved items. Per-paper attempts retain the route, outcome, timestamp, and failure reason. Exit zero means every paper is verified and every PDF belongs to a record.

Use read-pdf to inspect downloaded content before making claims. A successful download does not establish citation support. State verified, missing, and blocked counts; never describe a partial corpus as complete. Preserve any unresolved paper’s precise next action.
