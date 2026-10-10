# Current Handoff

- **Prepared:** 2026-10-09 (owner's Windows 11 machine; branch `claude/first-worker-launch`, uncommitted until the architect commits)
- **Repository:** `henslewm/universal-ai-project-template`
- **Gate:** ACTIVE since 2026-10-08 (`validate_bootstrap.py config/bootstrap.json --require-active` passes).
- **Scope:** the four ADR-096 milestones only; nothing outside them. Shipped milestones take defect fixes only (ADR-098).

## Milestones

| Milestone | State |
|---|---|
| Records current | Done: PR #121 merged (`4ac2d68`); frozen (ADR-098) |
| Unknown-cost state (ADR-097) | Done: PR #122 merged (`4921427`); frozen (ADR-098) |
| Auto-closeout (ADR-094) | Done: PR #116 merged (`066a37c`) after 4 Codex rounds; frozen (ADR-098) |
| External worker launcher (OL-036) | Merged: PR #124 (`41e3a68`, ADR-099) and fixes #126, #128, #130, #132. First real launch ran on Windows 2026-10-09 but produced no worker report, so "not done until the owner's first real launch succeeds" is NOT met (OL-043) |

## First launch result (2026-10-09, Windows 11, architect Claude Opus 5.5)

- Windows launcher tests: 35 ran, OK, 1 skipped (FIFO, POSIX-only).
- Harness: Cline CLI 3.0.70 (`npm install -g cline@3.0.70`; 3.0.69 lacked its win32-x64 binary). Protocol text says 3.86.2; npm's latest is 3.0.70. Wrapper `C:\Users\hensl\worker-runs\cline_wrapper.py` (absolute-path python.exe) sets `PATH`, `SystemRoot` and an empty `HOME`/`USERPROFILE`/`TEMP`, and the harness argv adds `--config {rundir}/harness-config`. LM Studio's `lmstudio` provider needs no key (binding credential_env null).
- Models in LM Studio: qwen3.8-27b (17.7 GB) is too large for the RAM headroom with Docker Desktop running; huihui-qwen3.8-27b-abliterated (10.5 GB) fits the 12 GB RTX 3060 (about 7 tok/s in-run).
- Evidence and local configs (outside git): `C:\Users\hensl\worker-runs\2026-10-09-first-launch\` (router with one zero-priced LM Studio resource and `role_api_budget_usd` 5; feedback policy `attempt_timeout_seconds` 3600; packet LAUNCH-WIN-001, retry_budget 2).
- Attempt 1 was killed by Claude Code's host for low system memory (about 27 min); attempt 2 hit the 3400 s bound after the worker looped on the 16 KB `brief.json` structure and never wrote a report. Both abandoned at $0. Ledger: 2/2 attempts used, NEEDS_ARCHITECT, task exhausted.
- Launcher behaviour verified on Windows: scoped environment, job-object tree stop, TIMED_OUT with next action abandon, relaunch guard.

## Next action

1. Owner decides OL-041 (brief readability: smaller brief, Markdown rendering, or another model or harness; defect fixes only under ADR-098), OL-042 (unknown-scope abandon spends the contract repair) and OL-043 (whether launcher-path success suffices).
2. If another launch is wanted: a new ledger for a fresh task, a zero-priced binding first (`abandon` on a metered resource records an unknown cost and bars paid routing, ADR-097), `role_api_budget_usd` set in the router configuration (the architect never raises it). Start Claude Code with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` or keep RAM free so the host does not kill the background launcher.
3. Commit and push this branch with `python scripts/closeout.py push` (not yet done).

## Notes

- This tree may be shared with a Codex session: untracked `config/codex.toml` appeared at 21:57 local on 2026-10-09 and another writer switched the branch to `main`. Check for other writers before multi-file work (ADR-062).
- The Claude Code auto-mode classifier refused Cline with `--auto-approve` ("Create Unsafe Agents"). The owner added local allow rules in `.claude/settings.local.json` (gitignored) for `python scripts/worker_launcher.py *` and `python C:/Users/hensl/worker-runs/cline_wrapper.py *`. The classifier has also refused agent edits to `.claude/settings.json`, `MASTER_CLAUDE_CODE.md` and, at times, this file. Never work around a refusal.
- The architect runs `launch` as a background task or with `--timeout-seconds` below its command timeout (R-022): the launcher stops the tree only at the bound or on Ctrl+C.
- A Node-based harness needs an absolute-path wrapper that sets `PATH` (and `SystemRoot` on Windows); the child environment holds only the binding's credential variable.
- `closeout.py ready` and `merge` need gh GraphQL. Claude cloud sessions refuse GraphQL, so run them on the owner's machine.
- Before merging, confirm the PR head is the commit the last Codex round reviewed and that no fix is still being pushed.
- On macOS the launcher tests fail under the default `TMPDIR` ("Startup document path contains a symlink"); set `TMPDIR` to a path with no link. The tests and `closeout.py ready` need `jsonschema` (`requirements-work-packets.txt`).
- After switching branches, run `python3 scripts/sync_skills.py` before the suite (OL-037). `test_cli_exit_codes` times out when stdin is an open pipe (OL-039); run the suite with stdin closed.
- Next free ADR: ADR-100. No decision was made in this session.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
