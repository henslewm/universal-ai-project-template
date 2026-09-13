# Current Handoff

- **Prepared:** 2026-09-13 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** main
- **Latest accepted merge:** `b326dca1674ae858eacb83cda7cf67c96c2d0e12` (PR #20, closed #7). Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** none active. #8 is next and has not been started.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #8](https://github.com/henslewm/universal-ai-project-template/issues/8) — independent review, acceptance gates and minimal-context review packets. Issues #2 through #7 are closed through merged PRs #15 to #20. Read each child's completion comment for the limitations it carried forward rather than assuming a closed issue left nothing behind.

## What #7 left you

`EXECUTION_HARNESS_PROTOCOL.md` is the harness contract; `scripts/execution_harness.py` prepares a bounded brief and ingests a worker report, and never invokes a model or runs the harness command. Decisions ADR-010 through ADR-013. `docs/ISSUE_7_VALIDATION.md` is the full record: the acceptance mapping, four operator runs, and the review round with its five findings.

Two things there matter for #8 specifically.

First, #7's review was performed by the same model family as the implementer, on code it had written. Master #14 goal 9 prefers a different strong model for review when practical, and that preference was not met. It found five real defects, two of which were gaps in its own earlier correction — so the arrangement is not worthless, but it demonstrably misses things a cross-family reviewer catches, exactly as happened on #6. #8 is where this becomes machinery rather than a promise. Do not let #8 close with its own gates unexercised by a reviewer that did not write them.

Second, the harness deliberately accepts a worker's assertions about its own validation, cost and scope as *supplied evidence, not proof*. Run 4's assertions happened to survive independent rechecking because that packet was objectively checkable by a committed checker — a property of the packet, not of the adapter. Independent acceptance is #8's job, and this is the gap it exists to close.

## Verified state

240 tests pass on Linux and Windows. Repository validation passes 57 required paths and `scripts/sync_skills.py --check` reports 0 differing files. CI `validate` was green on PR #20 before merge.

## Exact next action

Begin #8 in a fresh session, orienting from master #14 and #8 only plus these durable documents. Do not start it in the same session that merged #7 — master #14 requires rereading it before selecting the next child, and a fresh read after a merge is the point of that rule. Nothing is in flight, no branch is pending, and no reservation is open.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`, so autonomy on a real project is not authorized and nothing so far activates it. Everything proceeds as the maintainer's explicitly authorized template maintenance.

`scripts/sync_skills.py` (without `--check`) mirrors the whole tree into the distribution payload; use it rather than copying files by hand, and `--check` is what CI enforces. This checkout has no repository virtualenv and must not gain one: a venv inside the working tree makes `scripts/validate_project.py` fail on vendored `.pem` files. `jsonschema==4.26.0` is installed into a disposable interpreter outside the repository.

Confirm harness flags against the installed harness version before enabling a binding; the committed Cline argv was illustrative and wrong until checked against Cline CLI 3.86.2. The same applies to `context_overhead_tokens`, `context_growth_reserve_tokens` and `served_context_window` — all three are operator declarations the adapter cannot verify, and an understated value still admits a dispatch a worker cannot accept. The live demo kit lives outside this repository at `_harness-demo\run-2`; its `harness-config.json` is a standalone copy, not the committed example, so keep the two in step when the schema gains required fields.

Work on this repository moved from Cowork to the Claude Code CLI at the repository root on 2026-09-13, which is what `MASTER_CLAUDE_CODE.md` prescribes and where `gh` is authenticated.

## Boundaries

All harness fixtures are synthetic and offline. The adapter does not authenticate roles, verify that a model was called, confirm a command ran, or accept work. No credential belongs in configuration, briefs, reports, run directories or logs. Model-performance calibration remains #12 and should receive #7's run-4 profile — roughly 7.5 tokens per second of generation for a trivial packet on a 27B partially offloaded to system RAM — as an input, not as an acceptance result. Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
