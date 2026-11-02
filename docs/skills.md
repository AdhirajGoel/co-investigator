# Scientific skills

Ask in ordinary language, or explicitly invoke a skill. Codex uses `$skill-name`; Claude Code uses `/skill-name`. Both can also read the SKILL.md by its path. If another installed skill has the same name, point to the project-local file.

| Skill | Use it for | Runtime |
|---|---|---|
| literature-pdf-download | Retrieve and validate PDFs; preserve routes, attempts, and missing-paper records | Python, curl; optional browser route |
| read-pdf | Search and read PDFs by page; inspect figures and tables | Poppler; optional pdfplumber |
| literature-synthesis | Build a question-driven evidence synthesis and testable alternatives | Agent and source access |
| citation-validation | Check that cited sources support scientific claims | Agent and PubMed access |
| adversarial-peer-review | Requested two-round review with independent evidence, methods, and interpretation lenses | Agent with independent delegation or separate sessions |
| experiment-cycle | Plan discriminating tests and reconcile observations with predictions | Agent; project-specific analysis tools |
| scientific-tool-building | Add a tested script or skill and connect it to project records | Agent; task-specific dependencies |
| sgrna-sequence-verification | Check assembled sequence length and spacer presence on either strand | Python and openpyxl |
| scientific-writing | Write or revise scientific prose while preserving evidence and meaning | Agent |

The workspace copies each skill into `.agents/skills/` and gives Claude Code a relative link under `.claude/skills/`. Global installations are untouched. After editing a project skill, verify it with `python3 tools/workspace.py check .`; restart the agent if discovery has not refreshed.

Host documentation: [Codex skills](https://developers.openai.com/codex/skills) and [Claude Code skills](https://code.claude.com/docs/en/skills).
