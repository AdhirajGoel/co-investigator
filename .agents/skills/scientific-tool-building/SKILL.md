---
name: scientific-tool-building
description: Build or adapt a project-specific scientific script or agent skill and link it to the research it supports. Use for repeated calculations, primer or cloning utilities, data processing, and analysis tools; resolve scientific assumptions before implementation.
---

# Scientific Tool Building

Read the project context, collaboration rules, and `tools/registry.md`. The scientist can describe the task in ordinary language; handle implementation details yourself.

1. Establish the input, expected output, scientific assumptions, and intended use. Inspect a supplied schema or sample before asking. Ask only for unresolved choices that change the scientific result or authority to act.
2. Reuse a registered tool or suitable existing dependency where possible. For primer or sequence tasks, obtain the reference sequence, orientation, design constraints, and acceptance criteria from the scientist or an identified source. Never substitute invented research sequences.
3. Keep code under `tools/` or the relevant analysis directory. Use a project-local environment. Preserve raw inputs; write derived outputs separately. Validate units, identifiers, missing values, and ambiguous matches before reporting success.
4. Add a small test or self-check using disposable, clearly artificial inputs. Cover one normal case and the failure that would most plausibly create a misleading scientific result. Test the actual command and output, not just function names.
5. Register the tool’s purpose, command, dependencies, inputs/outputs, assumptions, verification, and dependent artifacts in `tools/registry.md`. A script should explain its arguments with `--help`.
6. If a repeated procedure warrants an agent skill, write a focused SKILL.md under `.agents/skills/<name>/`. Use portable paths and include required scripts/references. Create the matching relative directory link in `.claude/skills/`, then run `python3 tools/workspace.py check .`. Keep project-specific skills local; do not modify personal installations.

Before handing over, show the scientist how to request the tool in ordinary language and where to inspect its results. Record the tool’s existence in current context when relevant to the next work.
