# How collaboration is controlled

The scientist owns the research question and decides what findings mean for the project. The agent proposes approaches, carries out authorized work, and records evidence and reasoning in files the scientist can inspect.

`context/collaboration.md` holds preferences for initiative, approvals, output detail, citation format, independent review, models, and spending. A request such as “Discuss analysis choices with me before running them” changes that agreement. It applies to later sessions until the scientist changes it.

## Evidence and interpretation

Original observations live in `experiments/`; imported raw data live in `data/`. Preserve them. Agent-authored analysis and interpretation live in `syntheses/`, with scripts and intermediate outputs under the relevant analysis folder. A conclusion links to its inputs, method, and evidence. A plot does not replace that record.

`context/project-context.md` is the compact current view. It distinguishes established observations, working hypotheses, contradictory evidence, and the next question. When an interpretation changes, retain the older version and link the superseding conclusion. `context/decisions.md` records consequential choices and their reasons; `context/project-log.md` records completed work.

## Add a scientific tool

Describe the repeated task and the result you need. The scientific-tool-building skill asks only for unresolved scientific assumptions and input/output requirements, reuses suitable code, and tests the result on disposable fixtures. The tool’s record in `tools/registry.md` links its command, dependencies, inputs, checks, and analyses that depend on it. A tool may be a script, an external service, or another skill.

## Review and iteration

Citation validation checks scientific claims against inspected sources. Independent review is requested separately and uses the scientist’s selected depth and models. The review record preserves disagreements and explains which changes were accepted. Neither a favorable review nor a validated citation establishes a biological result that was never measured.

## Sharing

Local storage does not mean model inference is local: content supplied to a hosted agent follows that service’s data policies. Establish project-specific rules before processing restricted material. Git history, attachments, figures, and source licenses need review before sharing. Creating a workspace does not grant permission to publish it.
