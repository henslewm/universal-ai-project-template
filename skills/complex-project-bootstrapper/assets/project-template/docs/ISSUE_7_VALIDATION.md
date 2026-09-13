# Issue #7 validation and review

Issue: [Integrate Cline as bounded execution harness with LM Studio and cloud tiers](https://github.com/henslewm/universal-ai-project-template/issues/7). #6 was closed through merged PR #19 at `5e0a28c62ff9fdaa9c9764713742e97f12061040` before this child began. Locked master #14 title/body and order remain unchanged.

## Acceptance mapping

- **A bounded sample task can execute through Cline using LM Studio.** Met by an operator-executed run on 2026-09-13 against `qwen/qwen3.8-27b` served by a local LM Studio OpenAI-compatible server. The worker read its brief in one tool call, created the required module, ran the contract's validation command, and wrote a report that `verify-report` accepts with `outcome: PASS` and one validation check under the contract's own id. The criterion took four runs; the three that failed are recorded below because each produced a correction.
- **Provider configuration is documented without secrets.** `config/execution-harness.example.json` is committed `enabled: false` with placeholder model identifiers, no API base secrets and credentials named only by environment variable. `config_valid` refuses credential-like material anywhere in the configuration, an unsafe API base, and a credential given as a literal rather than an environment-variable name. `EXECUTION_HARNESS_PROTOCOL.md` documents setup, including that `cline auth` demands a key argument even for a local server that ignores it, so a placeholder is named through `credential_env`.
- **Worker cannot silently broaden its packet.** The brief renders only the controller's own worker context and the current contract revision; there is no second, looser copy. `ingest` refuses a report with an unexpected field, a missing or invented validation id, a mismatched dispatch id, empty evidence, an oversize body, credential-like material, or `PASS` claimed while any check failed, scope is not `within`, or an architecture conflict is reported.
- **Failed attempts preserve evidence for the next tier.** A recorded failure carries its evidence and fingerprint, and the next brief carries `prior_failures` and `failure_groups` forward. An attempt that produced no usable report is closed only through an explicit `abandon` with a stated reason, which becomes that attempt's evidence (ADR-011). A reservation spent on a harness that cannot be prepared is closed as `PROVIDER_UNAVAILABLE` with the refusal as evidence rather than left pending (ADR-010, ADR-012).
- **Cline is replaceable.** Bindings map routed resource ids to harnesses by configuration, and the committed example declares a second non-Cline `command` adapter so substitutability is visible rather than asserted. Packets, contracts, routing decisions, attempt ledgers and published evidence are unchanged by substitution. Nothing assumes a harness natively routes a different model to each arbitrary subagent; the orchestration layer stays explicit so that assumption is never load-bearing.

## Offline validation — 2026-09-13 UTC

The full suite passed all 235 tests on Linux and on Windows. The 19 focused harness tests exercise configuration refusals, brief-only-permitted-context, the complete report contract, path substitution, that dispatch never executes a harness, a spent reservation closed as `PROVIDER_UNAVAILABLE`, no second reservation while one is pending, no run-directory reuse, the `abandon` paths, `verify-report`, and the ADR-012 capacity refusals. Repository validation passed 57 required paths and `scripts/sync_skills.py --check` reported 0 differing files.

All harness fixtures are synthetic and offline. The adapter never invokes a model and never runs the harness command, so no test in this suite calls a provider.

## Live operator runs

A live run against a real local model is an operator action. Its transcript is evidence for that run only and is not reproducible in CI. Four runs were performed on 2026-09-13; the full transcripts and analysis are in the child issue.

### Run 1 — `ektome-qwen2.5-coder-7b-instruct`, no report at all

The model narrated tool calls as prose, never read the brief, explicitly assumed hypothetical requirements, then claimed in past tense to have completed the work. Session telemetry showed `enableTools: true` and zero tool invocations, so the harness was configured correctly and the model simply did not use tools.

Two things follow. The report contract held: the fabricated success reached no record, because no conforming report existed. And the run exposed a defect in the harness itself. A dispatched attempt that produced no report left the reservation pending forever — the same stranding class the #6 reviews caught twice. Corrected under **ADR-011**: `ingest` now refuses a missing or malformed report without touching the reservation, and `abandon` closes it with an operator-stated reason as the attempt's evidence. Absence is never inferred.

### Run 2 — `qwen/qwen3.8-27b`, correct work, non-conforming report

The model did the work correctly but wrote a report the validator refuses, with partly fabricated evidence. Three brief defects caused it, all corrected:

- `report_contract.write_to` was the literal `{report}` placeholder, so the worker guessed a path. Every path the worker needs is now substituted, and a `paths` block states them explicitly (`a2039a3`).
- The brief was written as one canonical JSON line, which the worker's line-based file reader truncated; it then fought the file with three different workarounds. The brief is now written indented while still being measured and credential-scanned in canonical form (`b4f5161`).
- The report contract never stated the shape of a validation check, so the worker planned `{"id", "status"}` against a schema requiring `check_id, passed, failure_code, expected, actual, evidence`. The contract now carries `validation_check_fields`, `outcomes` and `scope_status_values`, read from the controller's own schema, plus a rule naming *check_id, not id* (`b4f5161`).

A worker cannot be blamed for a contract that does not state its terms. Each of these was a harness defect, not a model failure.

### Run 3 — capacity refusal the harness should have made first

The run failed before any work: `request (9139 tokens) exceeds the available context size (8192 tokens)`. The model was loaded in an 8192-token window and the harness's own system prompt and tool definitions accounted for most of it, so no brief of any size could have fit. The readable-brief fix had also grown the brief from 3.7 KB to 6.5 KB, which contributed but was not the cause.

This was a harness gap, not merely a misconfigured model. `scripts/model_router.py` compares the architect's declared `input_tokens + output_tokens + context_churn_tokens` against a resource's *declared* `context_window`. Nothing checked what the harness adds afterwards — the rendered brief, the worker rules and the harness's own prompt — and nothing represented that a locally hosted model is served in the window it happened to be loaded with, which can be far below the model family's declared window. Corrected under **ADR-012**.

### Run 4 — criterion met

With all of the above in place and the model reloaded in a larger window, the worker completed the packet and reported conformingly. `verify-report` returned `valid: true`, `outcome: PASS`, `scope_status: within`, one check under `VC-1`, 1 of 1 passed, exit code 0.

The worker's central claim was then verified independently rather than accepted from the report: running `python -B check.py` in the workspace printed exactly `ALL CHECKS PASSED` with exit code 0, and the final workspace listing contained exactly `check.py` and `solution.py` — no `__pycache__`, and none of the temporary capture files the report says it created and deleted. The report's scope claim therefore checks out against the filesystem, not only against itself.

The run took 9 iterations over roughly 25 minutes on an RTX 3060 with the 27B partially offloaded to system RAM. Input context grew from 5,480 to 13,649 tokens across the run without hitting the window, which is the ADR-012 estimate behaving as intended.

## Review

The implementer ran an independent review pass on this child. Master #14 treats same-model-family review as a fallback rather than the preferred independent review, and that limitation applies to #7's closure: the reviewer and the implementer were the same model family, and the reviewer had seen the implementation. On #6 the same arrangement found two permanent-stranding paths, and a separate cross-family review then found a P1 in that remediation. Both facts are recorded here so the strength of this review is not overstated. Independent acceptance machinery remains #8.

The three live-run defects above were found by running the harness against real models rather than by review, which is the point of requiring a live criterion at all. A reviewer reading the brief renderer would not have noticed that a one-line JSON file is unreadable to a line-based reader.

## Explicit boundaries

The adapter records assertions a worker makes about its own validation, cost and scope. Those are supplied evidence, not proof. Run 4's assertions survived independent checking because the task was objectively checkable by a committed checker; that property belongs to the packet, not to the adapter. The adapter does not authenticate roles, verify that a model was called, confirm that a command actually ran, or accept work.

The context estimate is a character-count approximation and deliberately conservative. It is not a tokenizer. An understated `context_overhead_tokens` or an overstated `served_context_window` will still admit a dispatch the worker cannot accept, and a declared served window is an operator assertion about how a model is hosted, which the adapter cannot verify.

Model-performance calibration remains #12. Run 4 establishes that one local model can satisfy the contract on one low-complexity packet; it establishes nothing about which tier should receive which work, and its run profile — roughly 7.5 tokens per second of generation for a trivial packet — is a calibration input, not an acceptance result.

No credential belongs in configuration, briefs, reports, run directories or logs. The template remains deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`, so autonomy on a real project is not authorized and nothing in #7 activates it. No master edits, credential changes, permission changes or branch deletion were part of this child.

## Decisions

- **ADR-010** — the harness is a preparation-and-ingestion adapter that never invokes a model or runs the harness command; routed resources bind to harnesses by configuration; a reservation spent on an unpreparable harness closes as `PROVIDER_UNAVAILABLE`.
- **ADR-011** — a dispatched attempt that produced no usable report is closed only through an explicit `abandon` with a stated reason, never by inferring the absence of a report file.
- **ADR-012** — a dispatch whose brief, rules, declared harness overhead and reserved output cannot fit the window the routed resource is actually served in is refused before a worker is handed it.

## Review findings and corrections

The review pass examined the harness, its schema, its configuration and its tests against `EXECUTION_HARNESS_PROTOCOL.md`, concentrating on the ADR-012 capacity gate and the report contract. It returned five findings, all corrected on this branch with a regression each. They are recorded under **ADR-013**, which extends ADR-012.

**The capacity check covered the opening prompt only.** `dispatch` summed the harness overhead, the brief, the rules and the reserved output, and compared that to the served window. A worker's context grows with every tool result it reads, and the passing run grew from 5,480 to 13,649 tokens across nine iterations. A dispatch sized to its first turn alone can therefore pass the gate and still exhaust the window halfway through — and with the original `>= 0` boundary, a dispatch with exactly zero headroom was accepted. `limits.context_growth_reserve_tokens` is now required and included in the requirement, so a dispatch must have declared room to grow. The committed example declares 4,000, calibrated against that observed run rather than guessed. This is a declaration, not a prediction: an understated reserve still admits a doomed dispatch, which the protocol states.

**A configuration contradiction cost a bounded attempt.** A binding claiming a larger served window than its routed resource declares was caught inside the capacity path, after the reservation was spent, so it closed an attempt as `PROVIDER_UNAVAILABLE` and escalated the task to an architect decision. Nothing about that check needs a reservation. `bindings_consistent` now runs before anything is spent, and the regression confirms the refusal leaves the attempt ledger empty.

**The configured brief bound measured a form no worker reads.** `brief_max_chars` was checked against the canonical single-line rendering while the file written to disk is the indented one, which is substantially larger — 6.5 KB against 3.7 KB for the demo packet. An operator setting a bound to protect a small context window was therefore protected against the wrong number. Both forms are now bounded and both are credential-scanned.

**A refused reservation left a directory that blocked its own retry.** The run directory was created before the reservation. When the controller refused to reserve — a hold, an exhausted budget, a stale approval anchor — an empty directory remained, and the natural retry at the same path then failed with `FileExistsError` for an attempt that never existed. Reuse is still refused before anything is spent, but the directory is created only once an attempt exists.

**The brief's field set was declared in three places.** The renderer, the ledger-free verifier and the tests each carried their own copy, so adding a field to the brief would leave `verify-report` rejecting valid briefs. `BRIEF_FIELDS` is now the single declaration all three read.

Two of these — the growth reserve and the brief bound — were defects in the correction that closed run 3, which is worth stating plainly: the fix for a capacity failure itself shipped with a capacity gap. That is the same pattern the #6 reviews found, where a remediation introduced a P1, and it is the argument for cross-family review rather than against review generally.
