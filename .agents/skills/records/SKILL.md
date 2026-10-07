---
name: records
description: Update the project's closeout records after verified work (state, open loops, decisions, sources, risks, handoff, changelog) by briefing the record-keeper agent, then validate. Use when the records Stop hook reports the records are behind the work, or when the user says "update the records", "do the closeout", "refresh the handoff" or ends a meaningful session.
---

# Records

Runs steps 1 to 8 of `MASTER_INSTRUCTIONS.md` → "Required closeout protocol". That section is the authority for what each record holds; this skill only gathers the facts and delegates. It never commits, pushes or merges; step 9 stays with the user's authority.

## 1. Gather the verified facts

From this session only, with evidence, not recollection:

- What changed: `git status`, `git log --oneline origin/main..HEAD`, `git diff --stat origin/main...HEAD`.
- Validation actually run and its result (validator, tests, `sync_skills.py --check`), with counts.
- Pull request state: number, head SHA, review round, open findings (`gh pr view`).
- Decisions made, quoting the user's words and the date, and which ADR or loop each touches.
- Anything left undone, blocked or unverified, and who owns the next action.

## 2. Brief the record-keeper

Delegate to the `record-keeper` agent with the facts above. The brief states the scope (the records in closeout steps 1 to 7), the acceptance check (`python scripts/validate_project.py` passes), the next free ADR, OL, R and SRC numbers, and the attempt limit of 2. A Claude Code session delegates by default (`MASTER_CLAUDE_CODE.md` → Delegation); on another platform, do the same steps directly.

## 3. Verify the result

- Read the record-keeper's diff rather than trusting its report: every claim traces to a fact from step 1, nothing is invented, and no closed loop or old state section was rewritten.
- Run `python scripts/validate_project.py`. In the template repository also run `python scripts/sync_skills.py` and then `--check`. On a FAIL, re-brief once, then fix it yourself.

## 4. Report

The records changed, the validator result, and whether the work is ready to commit. Commit only when the user has authorized it.
