# Current Handoff

- **Prepared:** 2026-09-13 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** issue-7-cline-harness
- **Latest pushed commit:** recorded in the closing commit of this handoff; run `git log --oneline -1` to confirm before trusting any figure here
- **Scope:** Issue #7 only; master #14 is unchanged.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #7](https://github.com/henslewm/universal-ai-project-template/issues/7) and [PR #20](https://github.com/henslewm/universal-ai-project-template/pull/20). Issues #2 through #6 are closed; the latest accepted merge is PR #19 at `5e0a28c62ff9fdaa9c9764713742e97f12061040`. Completion evidence and the limitations carried forward are linked in those issues.

#7 delivers a bounded, replaceable worker harness occupying one gap only: between the reservation the feedback controller grants and the result it records. `EXECUTION_HARNESS_PROTOCOL.md` is the contract. `scripts/execution_harness.py` prepares and ingests; it never invokes a model and never runs the harness command. Routing, attempt budgets and scope rules stay outside it, so Cline never becomes the architect. Decisions are ADR-010, ADR-011 and ADR-012.

## State: all five acceptance criteria met

The live criterion — "a bounded sample task can execute through Cline using LM Studio" — **is now satisfied**. Run 4 on 2026-09-13 executed the demo packet through Cline against `qwen/qwen3.8-27b` on a local LM Studio server. `verify-report` returned `valid: true`, `outcome: PASS`, `scope_status: within`, one check under `VC-1`, 1 of 1 passed, exit 0. The worker's central claim was verified independently rather than accepted: `python -B check.py` in the workspace printed exactly `ALL CHECKS PASSED` with exit 0, and the workspace contained exactly `check.py` and `solution.py` — no `__pycache__` and none of the temporary capture files the report says it deleted.

It took four runs. Runs 1 through 3 each produced a correction rather than a retry, and `docs/ISSUE_7_VALIDATION.md` is the full record with the acceptance mapping, the four transcripts' findings, the review limitation and the boundaries. Read it before reopening any of this. In short: run 1's model never called a tool and fabricated success, exposing the unreported-attempt stranding path (ADR-011); run 2 did the work but reported non-conformingly, exposing three brief defects (`a2039a3`, `b4f5161`); run 3 hit an 8192-token window that the harness should have refused up front (ADR-012).

Offline evidence: 19 harness tests and the full suite of 235 tests pass on Linux and Windows, repository validation passes 57 required paths, and `scripts/sync_skills.py --check` reports 0 differing files.

## Exact next action

1. Run an independent adversarial review of PR #20 against `EXECUTION_HARNESS_PROTOCOL.md`, concentrating on the ADR-012 context gate and the report contract. Report findings before changing anything.
2. Answer every finding in place with a regression for each, on this branch.
3. Merge PR #20 and close #7 with the acceptance criteria mapped to evidence, stating the review limitation: the reviewer was the same model family as the implementer and had seen the implementation, which master #14 treats as a fallback rather than preferred independent review. On #6 that arrangement found two real stranding paths and a later cross-family review still found a P1 in the remediation — so state it, do not overstate it.
4. Reread master #14 before selecting #8. Do not start #8 in the same session that merges #7.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`, so autonomy on a real project is not authorized and nothing in this work activates it. Everything proceeds as the maintainer's explicitly authorized template maintenance.

`scripts/sync_skills.py` (without `--check`) mirrors the whole tree into the distribution payload; use it rather than copying files by hand, and `--check` is what CI enforces. This checkout has no repository virtualenv, and must not gain one: a venv inside the working tree makes `scripts/validate_project.py` fail on vendored `.pem` files. `jsonschema==4.26.0` is installed into a disposable interpreter outside the repository.

Confirm harness flags against the installed harness version before enabling a binding; the committed Cline argv was illustrative and wrong until it was checked against Cline CLI 3.86.2. Measure `context_overhead_tokens` the same way: it is a property of the installed harness, and an understated value still admits a dispatch the worker cannot accept. The live demo kit lives outside this repository at `_harness-demo\run-2` and its `harness-config.json` is a standalone copy, not the committed example — keep the two in step when the schema gains required fields.

Work on this repository moved from Cowork to the Claude Code CLI at the repository root on 2026-09-13, which is what `MASTER_CLAUDE_CODE.md` prescribes and where `gh` is authenticated.

## Boundaries

All harness fixtures are synthetic and offline. The adapter records assertions a worker makes about its own validation, cost and scope; those are supplied evidence, not proof. Run 4's assertions survived independent checking because that packet was objectively checkable by a committed checker — a property of the packet, not of the adapter. It does not authenticate roles, verify that a model was called, confirm a command ran, or accept work. No credential belongs in configuration, briefs, reports, run directories or logs. Independent acceptance machinery remains #8, and model-performance calibration remains #12. No master edits, credential changes, permission changes or branch deletion are part of #7.
