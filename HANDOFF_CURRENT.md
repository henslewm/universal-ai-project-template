# Current Handoff

- **Prepared:** 2026-10-08 (cloud session that answered PR #116 Codex round 3)
- **Repository:** `henslewm/universal-ai-project-template`
- **Gate:** ACTIVE since 2026-10-08 (`validate_bootstrap.py config/bootstrap.json --require-active` passes).
- **Scope:** the four ADR-096 milestones only; nothing outside them. Shipped milestones take defect fixes only (ADR-098).

## Milestones

| Milestone | State |
|---|---|
| Records current | Done: PR #121 merged (`4ac2d68`); frozen (ADR-098) |
| Unknown-cost state (ADR-097) | Done: PR #122 merged (`4921427`); frozen (ADR-098) |
| Auto-closeout (ADR-094) | PR #116, still a **draft**: Codex rounds 1 to 3 answered, every finding fixed with a regression, every thread resolved, CI green; round 4 of 4, the last (ADR-089), requested on the head carrying this note. Frozen once merged |
| External worker launcher (OL-036) | Not started; next after #116 merges |

## Next action

1. PR #116: read Codex round 4 with `gh api` (reviews, review comments, issue comments); do not rely on notifications. If clean, the owner marks #116 ready for review and merges it (`closeout.py merge` cannot merge its own pull request). If round 4 has findings, fix reproduced defects with regressions, decline the rest (ADR-063, ADR-098), and ask the owner how to proceed; no 5th round.
2. After #116 merges: the launcher milestone on a new branch from `main`, scoped under `EXECUTION_HARNESS_PROTOCOL.md` from the ADR-077 limits and relying on ADR-097. It builds on the frozen harness, feedback and router through their interfaces; a change to them that is not a defect fix goes to the owner first (ADR-098).
3. Owner: decide OL-040 (PR #118 reuses ADR-095/096 and is outside scope; PR #119 is superseded).

## Notes

- `closeout.py ready` counts CodeRabbit's 2026-10-07 review as a round, so after Codex round 4 it reports PR #116 past the cap of 4; the owner merges #116 by hand either way.
- The owner removed the ADR-091 `ask` block on `main` (`fcfecf8`). The Claude Code auto-mode classifier refuses an agent editing `.claude/settings.json`, `MASTER_CLAUDE_CODE.md` and, at times, this file. Leave such edits to the owner and do not work around the refusal.
- `closeout.py ready` and `merge` need gh GraphQL. Claude cloud sessions refuse GraphQL, so run them on the owner's machine.
- After switching branches, run `python3 scripts/sync_skills.py` before the suite. The gitignored payload keeps the previous branch's files (OL-037), and a stale one fails `test_bootstrap_integration`.
- `test_cli_exit_codes` times out when stdin is an open pipe (OL-039); run the suite with `< /dev/null`.
- Next free ADR: ADR-099. ADR-062: one writer per tree. A session on the owner's Mac also works this repository; check for its pushes before multi-file work.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
