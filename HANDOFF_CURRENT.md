# Current Handoff

- **Prepared:** 2026-10-07
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `claude/bootstrap-retrofit` (ADR-096)
- **Scope:** the template now runs under its own bootstrap gate. Autonomy is OFF until the owner activates the package.

## What was done

- ADR-096: `config/bootstrap.json` written by hand as a retrofit and taken to `AWAITING_APPROVAL` by `bootstrap_gate.py review`; `BOOTSTRAP_REVIEW.md` is the approval packet. `bootstrap_project.py --destination .` was not used, because a scratch dry run showed it rewrites the records, deletes `archive/` and sets `template_mode` false.
- `config/project.json` holds the template's own values (still `template_mode: true`); the charter records the owner's 2026-10-07 decisions.
- Records corrected: PR #117 (ADR-095) is merged at `ff5f5a4`.

## Verified state

- `python scripts/validate_project.py` passes; `python scripts/validate_bootstrap.py config/bootstrap.json` reports VALID at AWAITING_APPROVAL; `--require-active` fails (not activated, as expected).
- Unit suite and `sync_skills.py --check` pass after `python scripts/sync_skills.py` builds the gitignored payload (OL-037).

## Next action

1. Owner: merge this branch's PR, then run `python scripts/bootstrap_gate.py activate` at the repository root and type the approval line (OL-038). Any edit to a bound document (charter, connector plan, skill plan, domain profile) or `config/project.json` before activation needs `bootstrap_gate.py review` again.
2. After `--require-active` passes, work the approved milestones in order: Records current; Unknown-cost state; then Auto-closeout ADR-094 (finish branch `claude/auto-closeout`) and External worker launcher OL-036. Nothing outside them.

## Notes

- The next free ADR is ADR-097; ADR-094 stays reserved for `claude/auto-closeout`.
- `bootstrap_gate.py` review and activate now update only the `- **Status:**` line of the `## Current` section of `PROJECT_STATE.md`; dated history sections are left alone (Codex round 3). After activation, the Records current milestone closes OL-038 and rewrites the current section.
- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
- `software_hardware.py` lazily imports `acceptance` (OL-034).
