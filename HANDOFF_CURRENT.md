# Current Handoff

- **Prepared:** 2026-10-07
- **Repository:** `henslewm/universal-ai-project-template`
- **Scope:** the template is unfrozen (ADR-093) for two owner objectives: less drift and token cost at session start, and delegation by default. Owner-requested work since the freeze also landed on `main`: ask rules (ADR-091) and fewer copy/pastes with a layperson README (ADR-092).

## What was done

- ADR-093 (PR #110, branch `claude/eager-davinci-lhxve0`): startup reads are validator-checked views, the `## Current (date)` section of `PROJECT_STATE.md`, the `## Open` table of `OPEN_LOOPS.md` and the `## Index` of `DECISIONS.md`. `scripts/validate_project.py` → `validate_record_views` fails on a stale or repeated Current section, a closed loop in the open table, a repeated heading or ID, or an index row that does not resolve to exactly one full or archived row, in both directions. Full ADR rows 070 to 090 are archived verbatim. Duplicated rule text is replaced by pointers to `MASTER_INSTRUCTIONS.md`. Claude Code subagents carry model tiers and bounded-outcome reports, and `MASTER_CLAUDE_CODE.md` → Delegation makes delegation the default there only.
- The decision was authored as ADR-091 and renumbered ADR-093 when `main` was merged in.
- PR #110 was merged by the owner on 2026-10-07 as `ed30f33` (head `0fb220d`, not reviewed by Codex after its last fix); PR #115 (`docs/REFERENCE.md` in the validator's REQUIRED list) followed, at `c27c0d6`.
- From `main`: ADR-091 `permissions.ask` rules in `.claude/settings.json` (PR #111); ADR-092 interactive intake by default, `scripts/web_setup.py` and a layperson README with reference moved to `docs/REFERENCE.md` (PRs #113 and #114).

## Verified state

- `python scripts/validate_project.py` passes; `python scripts/sync_skills.py --check` clean; `python -m unittest discover -s tests -p "test_*.py"` passes (count in the changelog entry of 2026-10-07).
- The `permissions.ask` rules from ADR-091 are not live-verified; they need a restart before a dry `gh pr merge` can confirm the prompt.
- No project is activated from this template; `config/bootstrap.json` is absent, as expected.

## Next action

- No queued work; ask the owner before starting anything new.
- Owner decision OL-036: whether the architect may launch external harness workers automatically. Until then a human runs any harness worker (ADR-083).

## Notes

- Closeout dates the current section of `PROJECT_STATE.md`; a changelog entry newer than it fails validation.
- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
- `software_hardware.py` lazily imports `acceptance` (OL-034).
- The master's immutability rule still applies to issue #14's original text; future status changes stay comments.
- Never write the Codex trigger phrase in a PR comment unless requesting a review, because Codex acts on quoted text; that is how PR #110 went past the ADR-089 review cap.
- Branch `claude/auto-closeout` holds unfinished ADR-094 work from another session (`scripts/closeout.py` and validator checks); the next new decision should take ADR-095 or later and check that branch first.
