# Current Handoff

- **Prepared:** 2026-10-08 (cloud session that finished PR #116, built the launcher milestone and recorded PR #124's merge)
- **Repository:** `henslewm/universal-ai-project-template`
- **Gate:** ACTIVE since 2026-10-08 (`validate_bootstrap.py config/bootstrap.json --require-active` passes).
- **Scope:** the four ADR-096 milestones only; nothing outside them. Shipped milestones take defect fixes only (ADR-098).

## Milestones

| Milestone | State |
|---|---|
| Records current | Done: PR #121 merged (`4ac2d68`); frozen (ADR-098) |
| Unknown-cost state (ADR-097) | Done: PR #122 merged (`4921427`); frozen (ADR-098) |
| Auto-closeout (ADR-094) | Done: PR #116 merged (`066a37c`) after 4 Codex rounds; frozen (ADR-098) |
| External worker launcher (OL-036) | Merged: PR #124 (`41e3a68`, ADR-099), the old launcher restored with the ADR-077 limits. No automated review covered head `f1a61b4` before the merge; a post-merge Codex review was requested. Not done until the owner's first real launch succeeds |

## Next action

1. Post-merge Codex review of PR #124 (head `f1a61b4`): read it with `gh api` on PR #124 and answer each finding under ADR-063; a fix goes in a new pull request with a regression shown failing first.
2. Owner: edit `MASTER_CLAUDE_CODE.md` → Delegation, the sentence "Dispatch to an external harness (Cline, local models) stays operator-run until a separate decision (OL-036)", to say the architect session runs `scripts/worker_launcher.py` itself under ADR-099 and subagents do not. Agents are refused edits to that file.
3. Owner, first real launch, on the Mac or Windows 11:
   - On Windows, first run `python -m unittest discover -s tests -p "test_worker_launcher.py"`; the Windows path has never run.
   - Use a zero-priced (local) binding first: `abandon` on a metered resource records an unknown cost and bars paid routing for that task (ADR-097).
   - A Node-based harness such as Cline needs an absolute-path wrapper that sets `PATH` (and `SystemRoot` on Windows); the child environment holds only the binding's credential variable.
   - Set `role_api_budget_usd` in the router configuration; the architect never raises it.

## Notes

- The architect runs `launch` as a background task or with `--timeout-seconds` below its command timeout (R-022): the launcher stops the tree only at the bound or on Ctrl+C.
- `closeout.py ready` and `merge` need gh GraphQL. Claude cloud sessions refuse GraphQL, so run them on the owner's machine.
- The Claude Code auto-mode classifier refuses an agent editing `.claude/settings.json`, `MASTER_CLAUDE_CODE.md` and, at times, this file. Leave such edits to the owner and do not work around the refusal.
- After switching branches, run `python3 scripts/sync_skills.py` before the suite. The gitignored payload keeps the previous branch's files (OL-037), and a stale one fails `test_bootstrap_integration`.
- `test_cli_exit_codes` times out when stdin is an open pipe (OL-039); run the suite with `< /dev/null`.
- Next free ADR: ADR-100. ADR-062: one writer per tree. A session on the owner's Mac also works this repository; check for its pushes before multi-file work.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
