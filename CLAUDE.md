@MASTER_INSTRUCTIONS.md
@MASTER_CLAUDE_CODE.md
@PROJECT_CHARTER.md
@HANDOFF_CURRENT.md

# Claude Code Startup Router

Use the imported files as the controlling project context. Inspect the current branch, `git status`, and recent relevant commits before substantive work. Run `python scripts/validate_project.py` before completing material changes.

The remaining startup files are not imported, so they do not load into every session and every subagent. Read them from the repository when the startup protocol in `MASTER_INSTRUCTIONS.md` calls for them:

- `PROJECT_STATE.md`
- `OPEN_LOOPS.md`
- `DECISIONS.md`
- `FACTS_AND_ASSUMPTIONS.md`
- `SOURCE_INDEX.md`

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, and a matching material-architecture fingerprint. Missing, invalid, or inactive state, or an unavailable runtime/validator, means no autonomous execution: resume bootstrap through `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md` within existing permissions.

Once activated, routine work within the approved scope and existing permissions may proceed without approval for each step. User-reserved actions, material architecture changes, and consequential external actions retain their applicable explicit-authority requirements. Activation does not expand tool or connector permissions.
