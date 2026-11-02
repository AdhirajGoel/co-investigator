# Co-Investigator

Co-Investigator contains nine scientific skills and a project structure for experimental scientists working with Codex or Claude Code. It connects a research question to the papers, hypotheses, experiment plans, analyses, and decisions behind the next experiment.

The agent helps inspect papers, develop testable explanations, and plan experiments with the scientist. The scientist performs the experiments and supplies the observations. The agent can then analyze the results, compare them with earlier predictions, and record what changed in the interpretation and why. Project context links to the evidence and decisions a later session needs to continue the work.

The system diagram connects the scientist and coding agent to project records, tools, and requested independent review.

![Co-Investigator: scientist and agent collaboration, persistent project records, and independent review](docs/figures/architecture.png)

*The scientist directs the agent’s work and controls consequential decisions. The [architecture guide](docs/architecture.md) explains the components and includes editable SVG and vector PDF versions.*

## Start with your agent

In an installed, signed-in Codex or Claude Code session, say:

> Set up https://github.com/AdhirajGoel/co-investigator for my research project. Follow START_HERE.md and ask me for the project-specific decisions.

Setup targets macOS with Python 3.10 or newer. Your agent follows [the setup procedure](START_HERE.md), creates a separate project folder, and records your choices about models, review depth, spending, sharing, and how much initiative it should take.

## Working together

Ask in ordinary language: “Read these papers and show which evidence supports each explanation,” “Compare these results with our predictions,” or “Add a tool for this repeated calculation.” The [included skills](docs/skills.md) cover literature, experiment planning and interpretation, writing, citation checks, independent review, and tool building, with utilities for PDF reading and sequence verification.

You can change the [collaboration rules](docs/collaboration.md) as the project develops. When you need another script or skill, describe its task; the agent establishes its inputs and assumptions, checks it, and records how to use it.

Co-Investigator grew out of experimental biology work. This release excludes the original study’s source material, data, and findings, and includes no scientific demo. [Developer checks](docs/development.md) use disposable software fixtures.

[MIT license](LICENSE). This is a static release with no ongoing maintenance commitment.
