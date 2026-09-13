# Current Handoff

- **Prepared:** 2026-09-13 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** issue-7-cline-harness
- **Latest pushed commit:** `dc3db55612375a0e7773aa8e6592c6a2ebb35d4c`
- **Scope:** Issue #7 only; master #14 is unchanged.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #7](https://github.com/henslewm/universal-ai-project-template/issues/7) and [PR #20](https://github.com/henslewm/universal-ai-project-template/pull/20). Issues #2 through #6 are closed; the latest accepted merge is PR #19 at `5e0a28c62ff9fdaa9c9764713742e97f12061040`, which closed #6 after five automatic review rounds and one independent review. Completion evidence and the limitations carried forward are linked in those issues.

#7 delivers a bounded, replaceable worker harness occupying one gap only: between the reservation the feedback controller grants and the result it records. `EXECUTION_HARNESS_PROTOCOL.md` is the contract. `scripts/execution_harness.py` prepares and ingests; it never invokes a model and never runs the harness command. Routing, attempt budgets and scope rules stay outside it, so Cline never becomes the architect. Decisions are ADR-010, ADR-011 and ADR-012.

The offline half is complete: 19 harness tests and the full suite of 235 tests pass, repository validation passes and the bootstrap distribution check reports 0 differing files.

## The one criterion still unmet

"A bounded sample task can execute through Cline using LM Studio" is **not yet satisfied**. It has never been claimed as satisfied. Three operator runs on 2026-09-13 each produced a real finding and each is recorded in #7:

1. `ektome-qwen2.5-coder-7b-instruct` produced no report at all: it narrated tool calls as prose, never read the brief, assumed hypothetical requirements, then claimed in past tense to have completed the work. Session telemetry showed `enableTools: true` and zero tool invocations, so Cline was configured correctly and the model simply did not use tools. The fabricated success reached no record, because no conforming report existed — and the run exposed a stranding path now fixed under ADR-011: an attempt producing no report left the reservation pending forever, so `ingest` now refuses a missing or malformed report without touching the reservation, and `abandon` closes it with an operator-stated reason. Absence is never inferred.
2. `qwen/qwen3.8-27b` did the work correctly but wrote a non-conforming report with partly fabricated evidence. That exposed three brief defects, all fixed: the report path was left as the literal `{report}` so the worker guessed (`a2039a3`); the brief was one canonical JSON line, which the worker's file reader truncated (`b4f5161`); and the brief never stated the shape of a validation check, so the worker planned `{"id", "status"}` against a schema requiring `check_id, passed, failure_code, expected, actual, evidence` (`b4f5161`).
3. The third run failed before any work: `request (9139 tokens) exceeds the available context size (8192 tokens)`. The 27B was loaded in an 8192-token window and Cline's own system prompt measured about 6805 tokens, so the brief could not fit whatever it contained. The readable-brief fix above had also grown the brief from 3.7 KB to 6.5 KB. This exposed a gap now closed under ADR-012: the router checks the architect's declared tokens against a resource's *declared* window, and nothing checked the brief, rules, harness overhead and reserved output against the window a resource is actually *served* in. `dispatch` now sums those and refuses with the arithmetic stated, reporting `context_estimate` on success; harnesses declare `context_overhead_tokens` and bindings may declare `served_context_window`.

Next action: the operator reloads `qwen/qwen3.8-27b` in LM Studio with a context window of at least 16384 tokens — 8192 cannot hold Cline's system prompt plus any brief — and reruns the prepared `run-2` command. Then either a passing run closes the criterion, or #7 is accepted with the limitation stated explicitly and model-capability calibration carried into #12. That is the maintainer's decision and it is recorded as open in #7. After it is settled: request review on PR #20, answer findings in place, merge, close #7 with evidence, and reread master #14 before #8.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`, so autonomy on a real project is not authorized and nothing in this work activates it. Everything proceeds as the maintainer's explicitly authorized template maintenance.

`scripts/sync_skills.py` (without `--check`) mirrors the whole tree into the distribution payload; use it rather than copying files by hand, and `--check` is what CI enforces. This checkout has no repository virtualenv, and must not gain one: a venv inside the working tree makes `scripts/validate_project.py` fail on vendored `.pem` files. `jsonschema==4.26.0` is installed into a disposable interpreter outside the repository. Confirm harness flags against the installed harness version before enabling a binding; the committed Cline argv was illustrative and wrong until it was checked against Cline CLI 3.86.2. Measure `context_overhead_tokens` the same way: it is a property of the installed harness, and an understated value still admits a dispatch the worker cannot accept.

## Boundaries

All harness fixtures are synthetic and offline. The adapter records assertions a worker makes about its own validation, cost and scope; those are supplied evidence, not proof. It does not authenticate roles, verify that a model was called, confirm a command ran, or accept work. No credential belongs in configuration, briefs, reports, run directories or logs. Independent acceptance machinery remains #8, and model-performance calibration remains #12. No master edits, credential changes, permission changes or branch deletion are part of #7.
