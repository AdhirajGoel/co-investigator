# Development checks

Run these commands from the release checkout with Python 3.10 or newer:

```sh
python3 tools/workspace.py check .
python3 -m unittest discover -s tests -v
```

The structural check verifies required files, skill metadata, and the relative links that expose the same skills to Codex and Claude Code. It also reports optional dependencies without installing them.

The tests exercise workspace creation, literature retrieval and validation, PDF reading, and sequence verification with disposable software fixtures and mocked network responses. Tests that require unavailable optional tools are skipped; inspect the output before reporting coverage. The [setup procedure](../START_HERE.md) describes those dependencies. If using a project virtual environment, run both commands with `.venv/bin/python`.

Keep research source material, experimental data, and findings out of this reusable release. Scientific skill changes belong in `.agents/skills/`; preserve the corresponding relative links in `.claude/skills/`.
