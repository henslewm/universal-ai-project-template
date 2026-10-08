# Current Handoff

- **Prepared:** 2026-10-08
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `claude/unknown-cost` (ADR-097), stacked on `claude/activate-template` (PR #121)
- **Scope:** milestones Records current (PR #121) and Unknown-cost state (ADR-097).

## What was done

- PR #120 (ADR-096 retrofit) merged to `main` at `7f04c75` on 2026-10-08. The owner merged it; the last head `9967655` came from a separate session on the owner's Mac after Codex round 4 of 4, so no Codex review covers it. CI was green.
- The owner activated the package on 2026-10-08 (commit `72ff167`). He sent identity "henslewm" and the approval line from a phone; this session passed both unchanged to `bootstrap_gate.py activate` (approved_at 2026-10-08T14:29:43Z).
- Unknown-cost state (ADR-097): abandoned attempts record `api_cost_usd: null`; routing sums only known costs and bars metered resources while a cost is unknown, across contract repairs; five regressions shown failing first.
- Records current: `PROJECT_STATE.md` has a new current section and the 2026-10-07 retrofit section is now history; OL-038 closed; OL-040 opened; changelog entry added.

## Verified state

- `python3 scripts/validate_bootstrap.py config/bootstrap.json --require-active` passes (ACTIVE). Run `python3 scripts/validate_project.py` before relying on the views.
- Open PRs from other sessions, untouched: #116 (draft `claude/auto-closeout`, ADR-094 WIP, an approved milestone); #118 (`claude/workflow-skills`, ADR number collision, conflicts, outside scope); #119 (draft, conflicts, superseded by PR #120's records). #118 and #119 are OL-040.

## Next action

1. Owner: merge PR #121, then the Unknown-cost state PR.
2. Next milestones: External worker launcher OL-036 (unblocked by ADR-097) and Auto-closeout ADR-094 (finish `claude/auto-closeout`, PR #116). Nothing outside the approved milestones.
3. Owner: decide OL-040 (whether #118 is wanted, which needs renumbering to ADR-097+ and an approval revision; whether to close #119).

## Notes

- The next free ADR is ADR-098; ADR-094 stays reserved for `claude/auto-closeout`.
- ADR-062: one writer per tree. A second session on the owner's Mac also works this repository, so confirm no other agent is writing before multi-file work.
- Any edit to a bound document (charter, connector plan, skill plan, domain profile) or `config/project.json` needs `bootstrap_gate.py review` and renewed approval.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
- OL-034: `software_hardware.py` lazily imports `acceptance`. OL-037 (fresh-clone payload; run `python scripts/sync_skills.py`) and OL-039 (CLI test stdin) are open and outside the milestones.
