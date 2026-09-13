# Bounded execution harness

A worker harness executes one architected work packet and nothing else. Cline is the default harness; it is not the architect and not a source of truth. This implements Issue #7.

The harness sits in exactly one gap: between the reservation the feedback controller grants and the result it records. Everything around that gap already exists and is reused rather than duplicated. `WORK_PACKET_PROTOCOL.md` owns the contract and its revisions. `MODEL_ROUTING.md` owns tier and effort selection and its replayable decision ledger. `FEEDBACK_PROTOCOL.md` owns the reservation, the attempt budget, failure evidence and escalation. `GITHUB_LEDGER_PROTOCOL.md` owns publication of the resulting evidence. No routing decision, attempt counter or scope rule lives inside the harness or inside Cline.

`scripts/execution_harness.py` never invokes a model, never runs the harness command, and never verifies that reported work actually happened. It prepares a bounded brief, emits the exact invocation, and ingests a report. An operator or a later authorized automation runs the harness itself.

## Setup and authority

1. Copy `config/execution-harness.example.json` to project-specific configuration. The committed example is `enabled: false` and every model identifier in it is a placeholder; replace them with the real resource ids your router configuration declares.
2. Each binding maps one routed resource id to one harness, provider, model and optional API base. A local OpenAI-compatible server is named by its URL; cloud credentials are named **only** by environment variable, never embedded. Configuration validation refuses credential-like material anywhere in the file, unknown `{placeholder}` names, a templated command, a binding without `{brief}` or `{report}`, duplicate harness ids and duplicate resource bindings.
3. Confirm the harness flag names against the installed harness version before enabling. The example's Cline argv is illustrative: this adapter never runs it, so a wrong flag surfaces when the operator runs the command, not silently.
4. Dispatch preparation requires `enabled: true`. Everything else — approval, the bound configuration digest, the attempt budget — is enforced by the controllers this harness defers to.

```text
python scripts/execution_harness.py --config config/execution-harness.json validate-config
python scripts/execution_harness.py --config config/execution-harness.json --root . dispatch LEDGER RUNDIR --router-config config/model-router.json --request request.json
python scripts/execution_harness.py --config config/execution-harness.json ingest LEDGER RUNDIR/report.json
```

## Worker cycle

Read packet → inspect allowed context → implement or analyse → run the specified validation → report bounded evidence → retry within budget or return escalation state.

`dispatch` reserves one attempt through the feedback controller and writes a run directory containing `brief.json`, `BOUNDED_WORKER_RULES.md`, an empty `workspace/`, and `invocation.json` with the exact argv and the environment variable names required. It does not create `report.json`; the worker writes that. A run directory is never reused, so evidence is never overwritten.

The brief carries only what the packet already permits. It is rendered from the controller's own worker context — the current contract revision, the controller status, remaining and per-tier attempt budgets, architect guidance, prior failure fingerprints and summaries — plus the harness binding and the report contract. There is no second, looser copy of the contract for the worker to read, and the brief is refused if it exceeds its configured bound or contains credential-like material.

`ingest` validates the report before it reaches the ledger: exact field set, a dispatch id matching the pending reservation, one validation check per contract validation id and no invented ids, non-empty evidence, a size within bound, no credential-like material, and `PASS` only when every check passed, scope is `within` and no architecture conflict is reported. A report that fails any of these is refused rather than recorded, so a worker cannot silently broaden its packet or grade itself.

## Failure, escalation and replaceability

A failed attempt is recorded with its evidence and fingerprint, and the next brief carries that evidence forward. A stronger tier therefore receives what was already tried instead of rebuilding context.

If preparation refuses after the reservation is already spent — no binding for the routed resource, an oversized brief — the attempt is closed as `PROVIDER_UNAVAILABLE` with the refusal as evidence rather than left pending. The controller escalates that to the architect rather than retrying, which is deliberate: a harness that cannot be prepared is an architecture or configuration problem, not a transient failure to loop on.

Cline is replaceable. Any harness that accepts a brief path and writes a report path can be bound instead, which is why the example declares a second non-Cline harness. Packets, contracts, routing decisions, attempt ledgers and published evidence remain valid across that substitution. Nothing here assumes a harness can natively assign a different model to every arbitrary subagent; the orchestration layer stays explicit precisely so that assumption is never load-bearing.

## Boundaries

No credential belongs in configuration, briefs, reports, run directories, logs or comments. The adapter records assertions a worker makes about its own validation, cost and scope; those are supplied evidence, not proof. It does not authenticate roles, verify that a model was called, confirm that a command was actually run, or accept work. Independent acceptance remains Issue #8. A live run against a real local model is an operator action whose transcript is evidence for that run only and is not reproducible in CI.
