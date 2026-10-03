# Current Handoff

- **Prepared:** 2026-10-03
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `claude/trim-to-sw-hw-tracks` (five commits since `main`: `53de2db`, `ac371d3`, `0bfd28a`, `d58473a`, `3b63fe6`). No PR is open yet. The records pass is uncommitted.
- **Scope:** Trim to software and hardware tracks, owner-approved 2026-10-03 (ADR-083).

## What changed

- Legal profiles archived to `archive/legal/` and not served. `worker_launcher` and `github_ledger` removed (supersedes ADR-077, the launcher part of ADR-073, and ADR-007, ADR-008, ADR-009, ADR-025).
- The payload mirror `skills/complex-project-bootstrapper/assets/project-template` is no longer tracked; `scripts/sync_skills.py` and CI build it before tests.
- Software-only projects use the `software-hardware` profile; `--no-hardware` selects the `web-ui` track (satisfies ADR-082's web-ui bootstrap item).
- Bound documents changed, so any activated project needs re-approval (OL-029).
- Records updated: `DECISIONS.md` (ADR-083), `CHANGELOG.md`, `PROJECT_STATE.md`, `OPEN_LOOPS.md` (OL-029 to OL-035, annotations on OL-022, OL-024 to OL-027), `RISK_REGISTER.md` (R-009 note, R-016).

## Verified state

- 434 tests; 2 expected Windows-only failures (exec-bit tests in `tests/test_sync_skills.py`).
- `python scripts/validate_project.py` passes with 81 required paths.
- Tracked lines about 43k, down from about 92k.
- The records pass itself was not re-validated after these edits.

## Exact next action

1. Open a PR from `claude/trim-to-sw-hw-tracks`, request `@codex review` on the head SHA (ADR-074), answer every actionable finding, then wait for the owner's merge go-ahead.
2. `elf_sha256` enforcement is deliberately docs-only; do not add enforcement under this PR.
3. Owner decisions pending: OL-032 (uncommitted `.claude/settings.json` and `docs/proposed-beta-readiness-spec.md`, left untouched), OL-030 (charter item F), OL-028 (charter A-D, F).

## Notes

- Unchecked: whether generated projects inherit `archive/` (OL-035). `software_hardware.py:369` lazily imports `acceptance` (OL-034). `bootstrap_project.py`'s charter template still says "legal/business choices" (OL-031).
- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
