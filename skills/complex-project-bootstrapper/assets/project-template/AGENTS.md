# Codex Startup Router

This repository uses a shared multi-model control plane.

## Read before substantive work

Read these files in order:

1. `MASTER_INSTRUCTIONS.md`
2. `MASTER_CODEX.md`
3. `PROJECT_CHARTER.md`
4. `PROJECT_STATE.md`
5. `OPEN_LOOPS.md`
6. `DECISIONS.md`
7. `FACTS_AND_ASSUMPTIONS.md`
8. `SOURCE_INDEX.md`
9. `RISK_REGISTER.md`
10. `HANDOFF_CURRENT.md`

Then inspect `git status`, the current branch, and the newest relevant commits.

## Core behavior

- Treat the repository, not prior chat memory, as the durable state.
- Ask only questions that cannot be answered from the repo or approved connectors and that materially change execution.
- Use `instructions/profiles/` only when the task matches a profile.
- Use `.agents/skills/complex-project-bootstrapper/` for new-project initialization or project retrofits.
- Use `.codex/agents/` for parallel, non-overlapping subagent work.
- Run `python scripts/validate_project.py` before completing material repository changes.
- Apply the closeout protocol in `MASTER_INSTRUCTIONS.md`.

## Safety

Do not force-push, delete evidence, expose secrets, send external communications, change permissions, or perform consequential external writes without explicit user authority.
