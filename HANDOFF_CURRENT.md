# Current Handoff

- **Prepared:** 2026-09-13 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** issue-7-cline-harness
- **Latest pushed commit:** `008f409a2962f871a3f421bb403abc41703b9649`
- **Scope:** Issue #7 only; master #14 is unchanged.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #7](https://github.com/henslewm/universal-ai-project-template/issues/7) and [PR #20](https://github.com/henslewm/universal-ai-project-template/pull/20). Issues #2 through #6 are closed; the latest accepted merge is PR #19 at `5e0a28c62ff9fdaa9c9764713742e97f12061040`, which closed #6 after five automatic review rounds and one independent review. Completion evidence and the limitations carried forward are linked in those issues.

#7 delivers a bounded, replaceable worker harness occupying one gap only: between the reservation the feedback controller grants and the result it records. `EXECUTION_HARNESS_PROTOCOL.md` is the contract. `scripts/execution_harness.py` prepares and ingests; it never invokes a model and never runs the harness command. Routing, attempt budgets and scope rules stay outside it, so Cline never becomes the architect. Decisions are ADR-010 and ADR-011.

Working tree is clean and nothing is unpushed. The offline half is complete: 16 harness tests and the full suite of 232 tests pass on Linux and Windows, repository validation passes and the bootstrap distribution check reports 0 differing files.

## The one criterion still unmet

"A bounded sample task can execute through Cline using LM Studio" is **not yet satisfied**. An operator run on 2026-09-13 against `ektome-qwen2.5-coder-7b-instruct` produced no report at all: the model narrated tool calls as prose, never read the brief, explicitly assumed hypothetical requirements, then claimed in past tense to have completed the work. Session telemetry showed `enableTools: true` and zero tool invocations, so Cline was configured correctly and the model simply did not use tools. Full transcript analysis is in #7.

Two things follow. The report contract held — the fabricated success reached no record, because no conforming report existed. And the run exposed a stranding path in the harness itself, now fixed under ADR-011: a dispatched attempt producing no report left the reservation pending forever, so `ingest` now refuses a missing or malformed report without touching the reservation, and `abandon` closes it with an operator-stated reason as evidence. Absence is never inferred.

Next action: either retry the live run with a tool-calling-capable local model (`qwen/qwen3.8-27b` is loaded and is the mapped local escalation tier), or accept #7 with this limitation stated explicitly and carry model-capability calibration into #12. That is the maintainer's decision and it is recorded as open in #7. After it is settled: request review on PR #20, answer findings in place, merge, close #7 with evidence, and reread master #14 before #8.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`, so autonomy on a real project is not authorized and nothing in this work activates it. Everything proceeds as the maintainer's explicitly authorized template maintenance.

`scripts/sync_skills.py` (without `--check`) mirrors the whole tree into the distribution payload; use it rather than copying files by hand, and `--check` is what CI enforces. This checkout has no repository virtualenv, and must not gain one: a venv inside the working tree makes `scripts/validate_project.py` fail on vendored `.pem` files. `jsonschema==4.26.0` is installed into a disposable interpreter outside the repository. Confirm harness flags against the installed harness version before enabling a binding; the committed Cline argv was illustrative and wrong until it was checked against Cline CLI 3.86.2.

## Boundaries

All harness fixtures are synthetic and offline. The adapter records assertions a worker makes about its own validation, cost and scope; those are supplied evidence, not proof. It does not authenticate roles, verify that a model was called, confirm a command ran, or accept work. No credential belongs in configuration, briefs, reports, run directories or logs. Independent acceptance machinery remains #8, and model-performance calibration remains #12. No master edits, credential changes, permission changes or branch deletion are part of #7.
