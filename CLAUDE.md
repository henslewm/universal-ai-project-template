@MASTER_INSTRUCTIONS.md
@MASTER_CLAUDE_CODE.md
@PROJECT_CHARTER.md
@HANDOFF_CURRENT.md

# Claude Code Startup Router

Use the imported files as the controlling project context. Inspect the current branch, `git status`, and recent relevant commits before substantive work. Run `python scripts/validate_project.py` at startup, before trusting the startup views, and again before completing material changes.

The remaining startup reads are not imported, so they do not load into every session and every subagent. Read the views the startup protocol in `MASTER_INSTRUCTIONS.md` names: the `## Current` section of `PROJECT_STATE.md`, the `## Open` table of `OPEN_LOOPS.md`, the `## Index` of `DECISIONS.md` and `FACTS_AND_ASSUMPTIONS.md`; open anything else by ID when a record cites it.

The bootstrap / autonomy gate in `MASTER_INSTRUCTIONS.md` applies before autonomous substantive work; delegation follows `MASTER_CLAUDE_CODE.md` → "Delegation".
