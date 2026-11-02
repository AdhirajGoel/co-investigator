# {{name}}

{{question}}

Open this folder in Codex or Claude Code and ask the agent to read `AGENTS.md`. Your current project state is in [context/project-context.md](context/project-context.md); working preferences are in [context/collaboration.md](context/collaboration.md).

Original observations belong in `experiments/`, raw data in `data/`, proposed plans in `plans/`, literature work in `research/`, and agent interpretations in `syntheses/`. The [skill guide](docs/skills.md) lists available capabilities.

Run `python3 tools/workspace.py check .` to check workspace structure and skill links. Optional Python tools use `.venv/bin/python` after installing `requirements-tools.txt` into that environment.
