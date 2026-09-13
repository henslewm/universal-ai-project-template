# Bounded execution harness

A worker harness executes one architected work packet and nothing else. Cline is the default harness; it is not the architect and not a source of truth. This implements Issue #7.

The harness sits in exactly one gap: between the reservation the feedback controller grants and the result it records. Everything around that gap already exists and is reused rather than duplicated. `WORK_PACKET_PROTOCOL.md` owns the contract and its revisions. `MODEL_ROUTING.md` owns tier and effort selection and its replayable decision ledger. `FEEDBACK_PROTOCOL.md` owns the reservation, the attempt budget, failure evidence and escalation. `GITHUB_LEDGER_PROTOCOL.md` owns publication of the resulting evidence. No routing decision, attempt counter or scope rule lives inside the harness or inside Cline.

`scripts/execution_harness.py` never invokes a model, never runs the harness command, and never verifies that reported work actually happened. It prepares a bounded brief, emits the exact invocation, and ingests a report. An operator or a later authorized automation runs the harness itself.

## Setup and authority

1. Copy `config/execution-harness.example.json` to project-specific configuration. The committed example is `enabled: false` and every model identifier in it is a placeholder; replace them with the real resource ids your router configuration declares.
2. Each binding maps one routed resource id to one harness, provider, model and optional API base. A local OpenAI-compatible server is named by its URL; cloud credentials are named **only** by environment variable, never embedded. Configuration validation refuses credential-like material anywhere in the file, unknown `{placeholder}` names, a templated command, a binding without `{brief}` or `{report}`, duplicate harness ids and duplicate resource bindings.
3. Confirm the harness flag names against the installed harness version before enabling. This adapter never runs the command, so a wrong flag surfaces when the operator runs it rather than silently. The committed example was confirmed against Cline CLI 3.86.2, where three things matter:
   - `--data-dir` gives the run its own isolated state, so a bounded run never reads or rewrites the operator's global Cline configuration. Prefer it for every dispatch.
   - The CLI has no output-file flag, so the worker writes the report itself. The brief's report contract is what makes that reliable, and `ingest` refuses a report that does not match it.
   - `--provider lmstudio` uses the native local provider and rejects `--base-url`; an OpenAI-compatible provider accepts a base URL instead. Either satisfies a local server. `cline auth` also insists on an API key argument even for a local server that ignores it, so name a placeholder through `credential_env` rather than inlining a literal — the configuration validator refuses credential-like material.
4. Dispatch preparation requires `enabled: true`. Everything else — approval, the bound configuration digest, the attempt budget — is enforced by the controllers this harness defers to.

```text
python scripts/execution_harness.py --config config/execution-harness.json validate-config
python scripts/execution_harness.py --config config/execution-harness.json verify-report RUNDIR/brief.json RUNDIR/report.json
python scripts/execution_harness.py --config config/execution-harness.json --root . dispatch LEDGER RUNDIR --router-config config/model-router.json --request request.json
python scripts/execution_harness.py --config config/execution-harness.json ingest LEDGER RUNDIR/report.json
python scripts/execution_harness.py --config config/execution-harness.json abandon LEDGER --reason "..."
```

## Worker cycle

Read packet → inspect allowed context → implement or analyse → run the specified validation → report bounded evidence → retry within budget or return escalation state.

`dispatch` reserves one attempt through the feedback controller and writes a run directory containing `brief.json`, `BOUNDED_WORKER_RULES.md`, an empty `workspace/`, and `invocation.json` with the exact argv and the environment variable names required. The argv is built from `{rundir}`, `{workspace}`, `{brief}`, `{report}`, `{rules}`, `{provider}` and `{model}`; no other placeholder is accepted, and every one must be substituted. It does not create `report.json`; the worker writes that. A run directory is never reused, so evidence is never overwritten.

The brief carries only what the packet already permits. It is rendered from the controller's own worker context — the current contract revision, the controller status, remaining and per-tier attempt budgets, architect guidance, prior failure fingerprints and summaries — plus the harness binding and the report contract. There is no second, looser copy of the contract for the worker to read, and the brief is refused if it exceeds its configured bound or contains credential-like material.

`ingest` validates the report before it reaches the ledger: exact field set, a dispatch id matching the pending reservation, one validation check per contract validation id and no invented ids, non-empty evidence, a size within bound, no credential-like material, and `PASS` only when every check passed, scope is `within` and no architecture conflict is reported. A report that fails any of these is refused rather than recorded, so a worker cannot silently broaden its packet or grade itself.

## Failure, escalation and replaceability

A failed attempt is recorded with its evidence and fingerprint, and the next brief carries that evidence forward. A stronger tier therefore receives what was already tried instead of rebuilding context.

A worker that writes no report, or writes one the validator refuses, is a real outcome but never an inferred one. `ingest` refuses both and leaves the reservation untouched; `abandon` closes it, recording the operator's stated reason as the attempt's evidence. Because nothing was reported, scope is genuinely unknown, so the controller moves to an architect decision rather than looping a worker that may be structurally unable to complete the packet. The reason is required, bounded and credential-checked; absence alone never closes an attempt.

If preparation refuses after the reservation is already spent — no binding for the routed resource, an oversized brief — the attempt is closed as `PROVIDER_UNAVAILABLE` with the refusal as evidence rather than left pending. The controller escalates that to the architect rather than retrying, which is deliberate: a harness that cannot be prepared is an architecture or configuration problem, not a transient failure to loop on.

Cline is replaceable. Any harness that accepts a brief path and writes a report path can be bound instead, which is why the example declares a second non-Cline harness. Packets, contracts, routing decisions, attempt ledgers and published evidence remain valid across that substitution. Nothing here assumes a harness can natively assign a different model to every arbitrary subagent; the orchestration layer stays explicit precisely so that assumption is never load-bearing.

## Boundaries

No credential belongs in configuration, briefs, reports, run directories, logs or comments. The adapter records assertions a worker makes about its own validation, cost and scope; those are supplied evidence, not proof. It does not authenticate roles, verify that a model was called, confirm that a command was actually run, or accept work. Independent acceptance remains Issue #8. `verify-report` applies the same report contract to a brief and report pair without a ledger. It records nothing and accepts nothing; it exists so an operator-run demonstration can be checked by the real validator rather than by eye. A live run against a real local model is an operator action whose transcript is evidence for that run only and is not reproducible in CI.
