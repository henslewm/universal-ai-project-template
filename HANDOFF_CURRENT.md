# Current Handoff

- **Prepared:** 2026-10-07
- **Repository:** `henslewm/universal-ai-project-template`
- **Scope:** the template is unfrozen (ADR-093) for two owner objectives: less drift and token cost at session start, and delegation by default. Owner-requested work since the freeze also landed on `main`: ask rules (ADR-091) and fewer copy/pastes with a layperson README (ADR-092).

## What was done

- ADR-093 (PR #110, branch `claude/eager-davinci-lhxve0`): startup reads are validator-checked views, the `## Current (date)` section of `PROJECT_STATE.md`, the `## Open` table of `OPEN_LOOPS.md` and the `## Index` of `DECISIONS.md`. `scripts/validate_project.py` → `validate_record_views` fails on a stale or repeated Current section, a closed loop in the open table, a repeated heading or ID, or an index row that does not resolve to exactly one full or archived row, in both directions. Full ADR rows 070 to 090 are archived verbatim. Duplicated rule text is replaced by pointers to `MASTER_INSTRUCTIONS.md`. Claude Code subagents carry model tiers and bounded-outcome reports, and `MASTER_CLAUDE_CODE.md` → Delegation makes delegation the default there only.
- The decision was authored as ADR-091 and renumbered ADR-093 when `main` was merged in.
- PR #110 was merged by the owner on 2026-10-07 as `ed30f33` (head `0fb220d`, not reviewed by Codex after its last fix); PR #115 (`docs/REFERENCE.md` in the validator's REQUIRED list) followed, at `c27c0d6`.
- ADR-095 (PR #117, merged at `ff5f5a4`): the `record-keeper` subagent has Bash so it can run the validator itself; its instructions limit the shell to that check and read-only git commands. The first delegated records pass had to be validated by the architect because the agent had no shell.
- From `main`: ADR-091 `permissions.ask` rules in `.claude/settings.json` (PR #111); ADR-092 interactive intake by default, `scripts/web_setup.py` and a layperson README with reference moved to `docs/REFERENCE.md` (PRs #113 and #114).
- ADR-096 (PR #118, branch `claude/workflow-skills`, committed at `83bc978`, `main` at `ff5f5a4` merged in; renumbered from ADR-095, which PR #117 took): at the owner's direction, three skills for repeated work, `review-round` and `records` (user-invoked) and `status` (read-only), in `skills/` and mirrored by `sync_skills.py` into `.agents/skills/` and `.claude/skills/`; the validator requires them (95 paths) and checks native copies. Owner direction "run records automatically at the end of every session": new `scripts/records_due.py` plus `Stop` and `SessionEnd` hooks in `.claude/settings.json` send Claude to `/records` when work changed and `HANDOFF_CURRENT.md` did not (the `SessionEnd` hook can only warn); `/records` is now model-invocable by owner exception, `/review-round` stays user-invoked. The independent review returned FAIL with three findings, all fixed (`/review-round` push scope and request counting, `sync_skills.py` linked and orphan skills). ADR-094 is held by draft PR #116 (`claude/auto-closeout`), where a `/closeout` skill is planned.

## Verified state

- `python scripts/validate_project.py` passes; `python scripts/sync_skills.py --check` clean; `python -m unittest discover -s tests -p "test_*.py"` passes (count in the changelog entry of 2026-10-07).
- The `permissions.ask` rules from ADR-091 are not live-verified; they need a restart before a dry `gh pr merge` can confirm the prompt.
- ADR-096 branch, 2026-10-07: `sync_skills.py --check` clean; `validate_project.py` passes (95 required paths); 479 tests OK, 5 skipped (host-dependent); a simulated hook run on this branch printed a block. Verified live 2026-10-07: the `Stop` hook fired in this Windows session without a restart and blocked with the records-due reason; the `SessionEnd` warning is not yet observed live. Committed, pushed and PR #118 opened; Codex round 1 requested. Only projects generated after merge get the skills and hooks. Accepted limit: a non-bootstrapper skill's `assets/` is mirrored but dropped from the payload (none has one).
- No project is activated from this template; `config/bootstrap.json` is absent, as expected.

## Next action

- ADR-096 (PR #118, branch `claude/workflow-skills`): committed at `83bc978` and pushed; `main` (with ADR-095, PR #117) merged in. Codex round 1 of 4 returned three findings, all fixed (see the ADR-096 row). Then further rounds within the ADR-089 cap and the owner's merge go-ahead.
- Owner decision OL-036: whether the architect may launch external harness workers automatically. Until then a human runs any harness worker (ADR-083).

## Notes

- Closeout dates the current section of `PROJECT_STATE.md`; a changelog entry newer than it fails validation.
- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
- `software_hardware.py` lazily imports `acceptance` (OL-034).
- The master's immutability rule still applies to issue #14's original text; future status changes stay comments.
- Never write the Codex trigger phrase in a PR comment unless requesting a review, because Codex acts on quoted text; that is how PR #110 went past the ADR-089 review cap.
- Branch `claude/auto-closeout` holds unfinished ADR-094 work from another session (`scripts/closeout.py` and validator checks); the next new decision should take ADR-097 or later (ADR-095 is on `main`, ADR-096 is PR #118) and check that branch first.
