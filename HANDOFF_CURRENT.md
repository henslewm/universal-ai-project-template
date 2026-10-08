# Current Handoff

- **Prepared:** 2026-10-08 (end of the cloud session that ran the ADR-096 retrofit)
- **Repository:** `henslewm/universal-ai-project-template`
- **Gate:** ACTIVE since 2026-10-08 (`validate_bootstrap.py config/bootstrap.json --require-active` passes on `main`).
- **Scope:** the four ADR-096 milestones only; nothing outside them.

## Milestones

| Milestone | State |
|---|---|
| Records current | Done: PR #121 merged (`4ac2d68`) |
| Unknown-cost state (ADR-097) | Done: PR #122 merged (`4921427`) after 3 Codex rounds, all findings fixed |
| Auto-closeout (ADR-094) | PR #116, head `64b463a`, Codex round 3 of 4 requested; 2 rounds answered (11 findings, all fixed or answered, every thread resolved); CI green; still a **draft** |
| External worker launcher (OL-036) | Not started; next after #116 |

## Next action

1. PR #116: read Codex round 3 on `64b463a` with `gh api` (reviews, review comments, issue comments). Do not rely on notifications; they missed round 1. Fix actionable findings with regressions; round 4 is the last allowed (ADR-089). The owner marks it ready for review and merges it, because `closeout.py merge` cannot run until #116 is on `main`.
2. Then the launcher milestone: scope it under `EXECUTION_HARNESS_PROTOCOL.md`, starting from the ADR-077 limits, and rely on ADR-097 (unknown costs bar metered resources). Branch from `main`.
3. Owner: decide OL-040 (PR #118 reuses ADR-095/096 and is outside scope; PR #119 is superseded).

## Notes

- The owner removed the ADR-091 `ask` block on `main` (`fcfecf8`). The Claude Code auto-mode classifier refuses an agent editing `.claude/settings.json`, `MASTER_CLAUDE_CODE.md` and, at times, this file. Leave such edits to the owner and do not work around the refusal.
- `closeout.py ready` and `merge` need gh GraphQL. Claude cloud sessions refuse GraphQL, so run them on the owner's machine.
- After switching branches, run `python3 scripts/sync_skills.py` before the suite. The gitignored payload keeps the previous branch's files (OL-037), and a stale one fails `test_bootstrap_integration`.
- `test_cli_exit_codes` times out when stdin is an open pipe (OL-039); run the suite with `< /dev/null`.
- Next free ADR: ADR-098. ADR-062: one writer per tree. A session on the owner's Mac also works this repository; check for its pushes before multi-file work.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
- A stash on the cloud clone (`superseded by 9967655`) holds a duplicate of an already-merged fix; it is safe to ignore.
