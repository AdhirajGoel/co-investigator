---
name: experiment-cycle
description: Plan discriminating scientific experiments or reconcile experimental observations with prior predictions. Use for experiment planning, analysis interpretation, and choosing the next test; preserves raw records and separates observations from inference.
---

# Experiment Cycle

Read `context/project-context.md`, `context/collaboration.md`, and the narrowest primary records relevant to the request. Choose the branch the scientist asked for.

## Plan

Establish the decision, competing explanations, system, endpoint, controls, normalization, replication unit, and practical constraints. Specify predicted outcomes and the next action for each, including an inconclusive result. Distinguish exploratory choices from prespecified tests.

When a procedure depends on a commercial reagent or instrument, inspect the applicable manufacturer manual and record its version. Do not invent concentrations, sequences, parameters, or product instructions from memory. Discuss unresolved scientific or operational choices before making them executable.

Write agent-proposed plans in `plans/`. The scientist owns approval and execution. Use `templates/experiment-plan.md` when helpful; offer the configured independent review before a consequential plan is adopted.

## Interpret

Treat `experiments/` and `data/` as primary records. Never rewrite them to match an interpretation. Establish sample identity, units, normalization, replicate provenance, quality controls, and missing information before analysis. Preserve failed controls and exclusions in the analysis record.

Place reproducible scripts, configuration, and derived tables in `syntheses/data-analysis/<analysis>/`. Record the command, environment, input hashes, and checks. Separate descriptive measurements, statistical support, and causal interpretation. Do not substitute technical replicates for biological replication.

Write `syntheses/<date>-<topic>-conclusions.md`, linked to the primary record and analysis. State which predictions were supported, contradicted, or remain untested. Use `templates/conclusions.md` if useful.

## Maintain continuity

If the evidence changes the working model, append the decision and link a dated superseding conclusion. Update current context and the next question; keep old interpretations available. Ask the scientist about consequential changes in direction. Do not manufacture progress when the evidence remains inconclusive.
