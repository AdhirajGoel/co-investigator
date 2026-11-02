# Agent entry point

If the scientist asks to set up a project, read `START_HERE.md` and follow it. Otherwise establish whether you are editing this reusable framework or working in an initialized research workspace. Never populate the framework with a scientist’s research.

Skills are in `.agents/skills/`; `.claude/skills/` contains relative links to the same folders. Read the applicable SKILL.md before using its scripts. If a global skill has the same name, explicitly load this project’s file. Follow the scientist’s chosen models and permissions.

Use an isolated environment for optional dependencies. Do not install global skills, change global agent settings, read browser profiles, or initialize/push Git repositories as a side effect of setup. Setup and tests use no model APIs or credentials.

For framework changes, run `python3 -m unittest discover -s tests -v` and `python3 tools/workspace.py check .`. Keep the runtime Python-standard-library-only; optional skill dependencies are listed in `requirements-tools.txt`. Keep supporting files with their skills and preserve the Claude links.
