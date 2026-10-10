# Current Handoff

- **Prepared:** 2026-10-10 (owner's Windows machine; first cloud launch)
- **Repository:** `henslewm/universal-ai-project-template`
- **Gate:** the owner re-approved the foundation after the ADR-100 charter change (2026-10-10T02:49Z, commit `e055c50`).
- **Scope:** the four ADR-096 milestones only; nothing outside them. Shipped milestones take defect fixes only (ADR-098).

## Milestones

| Milestone | State |
|---|---|
| Records current | Done: PR #121 merged (`4ac2d68`); frozen (ADR-098) |
| Unknown-cost state (ADR-097) | Done: PR #122 merged (`4921427`); frozen (ADR-098) |
| Auto-closeout (ADR-094) | Done: PR #116 merged (`066a37c`) after 4 Codex rounds; frozen (ADR-098) |
| External worker launcher (OL-036) | Merged: PR #124 (`41e3a68`, ADR-099), marker fix #126 (`11e9822`), its round-2 fixes #128 (`9004eff`) and the hard-link fix #130 (`cd07187`). Done 2026-10-10: the first real metered-cloud launch ran end to end on Windows within the packet limits (Mistral Devstral Medium, `SHB-CLOUD-002`, `REPORT_WRITTEN`, ingested; ADR-100's condition). Its work was not accepted; OL-041 tracks the launcher defects |

## Launcher review state (verified 2026-10-09)

- PR #128's sentinel-store P2 is fixed by #132 (`4b4f0ea`) and answered on the thread; its P1 on the legacy `<ledger>.launched/` layout was declined with a reason. No #128 finding is open.
- PR #130's head `063b640` had a clean Codex review (no findings).

## Next action

1. `SHB-CLOUD-004` (2026-10-10) met contract v2 at a measured USD 0.36; its report is ingested and `REVIEW_PENDING`. Next: run independent acceptance on it with `scripts/acceptance.py` (`ACCEPTANCE_PROTOCOL.md`), then launch further tasks the same way.
2. Launch on the cloud binding with `contract-v2.json` (in `~/worker-runs/2026-10-10-cloud-launch`), which names `bytes` input and a returned invalid result and adds the fixed `VAL-CONTRACT` checker. The harness configuration there declares `usage_format: "cline-json"`, so ingest measures the cost (ADR-102) and paid retries stay possible within the budget. The launcher makes the brief and rules read-only (ADR-101); the wrapper's own read-only step is redundant but harmless.
2. Run setup that works on Windows (`~/worker-runs/2026-10-10-cloud-launch`):
   - The wrapper `cline_wrapper.py` sets `PATH` with Python and Windows PowerShell (Cline runs commands through `powershell`; without it every command fails), `PATHEXT`, `SystemRoot` and an empty `HOME`, and makes `brief.json` and `BOUNDED_WORKER_RULES.md` read-only before Cline starts.
   - Binding: provider `mistral`, model `devstral-medium-latest`, `credential_env` `MISTRAL_API_KEY`; router `role_api_budget_usd` 10 (owner, 2026-10-10). `ANTHROPIC_API_KEY` on this machine is rejected by Anthropic ("invalid x-api-key").
   - An `abandon` on a metered resource bars paid routing for that task (ADR-097), so a failed attempt needs a fresh task.
   - Verify a worker's claims yourself: in a smoke test the model invented a command's output when the command failed.

## Notes

- The architect runs `launch` as a background task or with `--timeout-seconds` below its command timeout (R-022): the launcher stops the tree only at the bound or on Ctrl+C.
- `closeout.py ready` and `merge` need gh GraphQL. Claude cloud sessions refuse GraphQL, so run them on the owner's machine.
- Before merging, confirm the PR head is the commit the last Codex round reviewed and that no fix is still being pushed; #126 merged one push early.
- The Claude Code auto-mode classifier has refused agent edits to `.claude/settings.json`, `MASTER_CLAUDE_CODE.md` and, at times, this file; an edit the owner directed explicitly went through on 2026-10-09. Never work around a refusal.
- On macOS the launcher tests fail (32 of 34 errors: "Startup document path contains a symlink") under the default `TMPDIR`, because `/var` links to `/private/var`. Run them with `TMPDIR` set to a directory whose path has no link. The tests and `closeout.py ready` also need `jsonschema` (`requirements-work-packets.txt`), which the Mac's system Python lacks.
- After switching branches, run `python3 scripts/sync_skills.py` before the suite. The gitignored payload keeps the previous branch's files (OL-037), and a stale one fails `test_bootstrap_integration`.
- `test_cli_exit_codes` times out when stdin is an open pipe (OL-039); run the suite with `< /dev/null`.
- Next free ADR: ADR-103. ADR-062: one writer per tree. A session on the owner's Mac also works this repository; check for its pushes before multi-file work.
- Never write the Codex trigger phrase in a PR comment unless requesting a review.
