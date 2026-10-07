---
name: status
description: Show in one short screen what this project is working on right now - branch, pull request and review round, the handoff's next action, open high-priority loops and whether the validator passes. Read-only. Use when the user asks "what are we working on", "where are we", "status" or seems to have lost the thread.
---

# Status

Read-only. Change nothing, commit nothing, request nothing.

## Gather

- `git branch --show-current`, `git status --short`, `git log --oneline -3`.
- `gh pr view --json number,url,state,isDraft,headRefOid` for the current branch, if one exists. Count the automated-review rounds on it as `/review-round` step 2 does, and whether the head has been reviewed.
- `HANDOFF_CURRENT.md` → "Next action".
- The `## Open` table of `OPEN_LOOPS.md`: the High-priority rows and any owned by the owner.
- `python scripts/validate_project.py`: pass, or the first errors.

## Answer

Plain language, at most eight lines, in this order:

1. What we're working on: one sentence, naming the branch, PR and ADR.
2. Where it stands: uncommitted changes, review round K of 4, head reviewed or not.
3. Validator: passing, or what fails.
4. Next action: from the handoff, or the obvious next step.
5. What needs the user: decisions or actions only they can take.
