---
name: citation-validation
description: Validate citations and literature-backed claims in life-sciences artifacts against PubMed before final delivery. Use automatically only for life-sciences reports, manuscripts, evidence syntheses, or similar artifacts that contain citations or literature claims; do not use for non-scientific artifacts or citation-free drafts.
---

# Citation Validation

Validate provenance only. Do not perform writing-style editing, broad fact-checking, peer review, or full-text literature analysis.

## Scope and precedence

Run after drafting and before final saving or delivery of an in-scope life-sciences artifact. Re-run after any substantive change to a citation or to a citation-bearing claim.

Do not run for non-life-sciences artifacts. For a life-sciences artifact, first state-check whether it contains citations or literature/evidence-backed claims. If neither is present, no-op.

Honor explicit user, journal, template, and project instructions. Trust a current success header only when it covers every retained in-scope claim and both the cited references and citation-bearing claims are unchanged. An incomplete or unavailable status remains unresolved.

## Validation workflow

1. Use the scientist’s configured model and verification preferences in `context/collaboration.md`.
2. Build a temporary, private claim–evidence–citation matrix. Do not add it to the artifact or save it unless the user explicitly requests it or project policy requires it.
3. For each scholarly article, query PubMed. Confirm that the article record exists and that its title and abstract support the associated claim. Use abstracts for claims they directly support. For a claim about a specific method, figure, numerical result, or causal mechanism, inspect the supporting full-text passage; if unavailable, mark that claim unverified rather than treating an abstract match as validation.
4. Do not use model memory as evidence. If an article cannot be verified in PubMed, prefer a suitable PubMed-indexed replacement. Retain a non-PubMed source only when it is genuinely appropriate (for example, an official method, database, protocol, or website), exists, and directly supports the claim.
5. If a citation or claim is unsupported, find a valid replacement. If none exists, revise or remove the unsupported citation or claim, then revalidate the changed material. If a claim remains unverified because its supporting evidence is unavailable, label it unverified and use the incomplete status below while it remains in the artifact.

## PubMed unavailable

Use PubMed as the source of record. Do not silently use an alternate endpoint or substitute model knowledge.

If PubMed cannot be queried, still save or deliver the artifact. Add the unavailable status header below with a brief, truthful reason. Do not claim that citations were validated.

## Status marker

For internal life-sciences reports, add exactly one current status header near the beginning of the artifact. Use the success marker only after every retained in-scope claim has been verified against adequate inspected evidence:

```text
Citation status: validated against PubMed and cited primary sources. Revalidate after citation or claim changes.
```

If PubMed was available but any retained in-scope claim remains unverified, use:

```text
Citation status: incomplete; retained claims remain unverified: [identify the claims and briefly explain the missing evidence].
```

If PubMed was unavailable, use:

```text
Citation status: not validated — PubMed verification unavailable: [brief reason].
```

Omit the header only when the user explicitly requests a sharing-ready or publication-ready artifact. For those artifacts, disclose a material validation gap in the delivery message instead.

Stay silent when validation succeeds without changes. Briefly disclose only material citation replacements, removed or revised claims, or unresolved evidence gaps. Never block delivery solely because PubMed is unavailable.
