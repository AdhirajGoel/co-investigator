---
name: adversarial-peer-review
description: Run a user-invoked, two-round scientific peer-review and revision workflow for manuscripts, reports, and other claim-bearing artifacts. Use only when the user explicitly requests adversarial peer review, multi-reviewer scientific challenge, or a simulated peer-review cycle; it coordinates an editor, three independent review lenses, editorial judgment, and an auditable response-and-revision ledger.
disable-model-invocation: true
---

# Adversarial Peer Review

Use this only after explicit user invocation. It is an evidence-focused process for
challenging and improving a claim-bearing artifact, not a way to manufacture criticism
or to replace domain-specific ethics, regulatory, or statistical review.

## Setup

1. Confirm the artifact, its intended audience, requested review scope, and destination
   for the revised artifact and review records. Read applicable project instructions and
   follow project-local file, citation, and Git policy.
2. Identify authoritative sources and available verification tools. Cite only material
   actually inspected during the work; label unverified claims or remove them.
3. Read `context/collaboration.md` for approved models, reasoning effort, review depth, and spending authority. Use the scientist’s selected editor and independent reviewers. Do not switch models to save cost without permission.
4. Each reviewer needs an independent context. If delegation is unavailable, offer a separate agent session with an explicit brief. Record which reviews actually ran; never label self-review independent.

## Round 0 — editorial brief

The editor studies the artifact, project context, and available evidence, then writes a
review brief containing:

- scope, audience, key decisions, and explicit review questions;
- a claim–evidence–method matrix: each material claim, evidence/citation, method or
  inference supporting it, uncertainty, and verification status;
- three non-overlapping, collectively comprehensive review lenses adapted to the
  artifact. Unless adaptation is justified, use:
  1. evidence, citations, and factual support;
  2. methods, statistics, controls, reproducibility, and feasibility;
  3. causal logic, claim calibration, alternatives, clarity, and interpretation;
- criteria for accepting, partially accepting, or declining critiques.

The editor assigns one lens to each reviewer. Reviewers receive the artifact, relevant
context, and the brief, but not one another's instructions, findings, or drafts.

## Round 1 — three independent reviews

Run the three reviewers in parallel when supported. Each reviewer must:

- assess only its assigned lens while flagging a cross-cutting issue only when it is
  necessary to explain a material risk;
- make specific, falsifiable findings tied to sections, claims, data, or citations;
- verify relevant citations and factual claims against authoritative sources;
- distinguish major concerns, minor concerns, and strengths to preserve;
- give concise evidence, assumptions, decision criteria, and verification results;
- never provide or request hidden chain-of-thought.

A valid finding of no major issues is allowed. Never ask reviewers to invent objections
or treat an LGTM-style result as a failure.

## Editorial synthesis 1

The editor compiles the three reports into one decision memo. It deduplicates overlap,
resolves conflicts, and uses scientific editorial judgment. A critique may be declined
when it is unsupported, disproportionate to the question, conflicts with the evidence,
or would impose inappropriate requirements—for example, unjustified sample-size demands
for an experiment whose stated objective does not require them.

For every critique, record: source reviewer/lens, evidence, decision (`accept`,
`partial accept`, or `decline`), rationale, required revision, and verification needed.

## Response and revision 1

The response/revision agent receives the artifact and the editor's decision memo. It:

1. Writes a response-to-reviewers that records every accepted, partially accepted, and
   declined critique with concise reasons.
2. Applies only accepted, scientifically sound revisions to the artifact.
3. Rechecks changed claims, citations, calculations, and cross-references.
4. Preserves calibrated uncertainty and explains any critique declined on editorial
   grounds.

## Round 2 — independent reassessment

Run three new independent reviewers in parallel when supported. They assess the revised
artifact and response-to-reviewers using the same separated lenses. They must determine
whether accepted fixes are adequate, whether declined critiques were reasonably handled,
and whether revisions introduced new errors. They may return no major issues.

## Editorial synthesis 2 and final revision

The editor writes a second-round decision memo using the same evidence-based discretion.
The response/revision agent applies accepted final fixes, verifies the final artifact,
and writes the final response/revision ledger. Do not accept a critique merely because
it was repeated; scientific soundness and proportionality control the decision.

## Safety and access handling

Resolve access or safety blockers transparently with the scientist. Preserve the research question and stated authority; never invent credentials, conceal the subject, or change models to evade a refusal. Continue independent permitted work while blocked steps remain recorded.

## Required artifacts

Use project naming conventions. If none exist, save the final artifact beside the input
and place review records in a sibling `peer-review/` directory:

| Artifact | Purpose |
| --- | --- |
| `review-brief.md` | Scope, matrix, review lenses, and decision criteria. |
| `round-1-<lens>.md` (three files) | Independent first-round reports. |
| `round-1-decision-memo.md` | Editorial synthesis and disposition of every critique. |
| `response-and-revision-r1.md` | Response-to-reviewers and first revision record. |
| `round-2-<lens>.md` (three files) | Independent reassessments. |
| `round-2-decision-memo.md` | Editorial final decisions. |
| `final-response-revision-ledger.md` | Accepted and declined critiques, fixes, and verification. |

Commit or push only when the applicable project-local policy requires it. Otherwise do
not infer Git authorization.

## Final validation

Before reporting completion, confirm:

- the three lenses were non-overlapping and collectively cover the material risks;
- reviewers were independent and did not see one another's reports before submission;
- each citation and factual claim affected by a revision was checked or explicitly
  labeled unresolved;
- each accepted revision was applied and verified;
- every declined critique has a concise, scientifically sound rationale;
- the final response/revision ledger distinguishes accepted, partial, and declined
  critiques and links them to the final artifact;
- no safety or access-control refusal was bypassed;
- all project-local file, commit, and push policy was followed.
