# Capability routing and economic policy

`scripts/model_router.py` implements Issue #4's deterministic, offline routing decision. It consumes a validated work packet, resource configuration and complete request/history, and saves an immutable local task-ledger record. It never calls a provider, reads credentials, authenticates evidence, activates autonomy, or changes the packet. Live dispatch, feedback orchestration, GitHub publication and measured telemetry are owned by #7, #5, #6 and #12 respectively. Independent acceptance enforcement is #8.

## Configure resources without changing contracts

Install `requirements-work-packets.txt` in your chosen Python environment. Copy `config/model-router.example.json` to a project routing configuration and validate it:

```bash
python scripts/model_router.py validate-config config/model-router.json
```

The example contains seven **disabled, fictional resources**: LM Studio T0/T1, Mistral T2, Claude T3/T4 and OpenAI/Codex T3/T4. Names, prices, context sizes, capability assessments and performance figures are examples, not current product claims. Verify the actual model, access method, limits and prices before enabling a project resource. Downloading a model, obtaining API access and session-based access are separate setup actions; configuring an adapter name does not implement or prove any of them.

Provider IDs and adapter names are replaceable configuration. A resource names one provider/model/tier and explicit effort profiles (`low`, `medium`, `high`, `very_high`). The router does not silently substitute effort levels. An executor must map a supported effort to the selected adapter's real controls and reject unsupported mappings. `credential_env` stores only the name of an environment variable, or null for access that does not use one. Keep values outside repository files. The router neither reads that variable nor tests connectivity. `enabled` means eligible for offline planning, not operationally available.

The JSON Schema includes strict `$defs/config` and `$defs/request` definitions. Validation also rejects duplicate IDs, unknown provider references, decreasing risk/complexity policies, nonfinite values and contradictory history. Estimated acceptance probabilities must be between 0.000001 and 1; estimates are not confidence guarantees.

## Prepare a request

Build the request from the packet's latest revision. This Python example prepares metadata only:

```python
import json
from pathlib import Path

packet = json.loads(Path("task.ready.json").read_text(encoding="utf-8"))
revision = packet["revision_history"][-1]
request = {
    "schema_version": "1.0",
    "binding": {
        "task_id": packet["task_id"], "revision": revision["version"],
        "contract_hash": revision["hash"], "role": "worker"
    },
    "task_class": "bounded-parser",
    "input_tokens": 4000, "output_tokens": 1000,
    "unavailable_providers": [], "unavailable_resources": [],
    "attempts": [], "observations": []
}
with Path("routing-request.json").open("x", encoding="utf-8") as output:
    json.dump(request, output, indent=2)
```

Use the full prior history for this **task + revision + role**. The worker uses the packet's total `retry_budget.max_attempts`; the reviewer has a separate `max_review_attempts` policy. `role_api_budget_usd` also applies separately to each role, not as a combined project spending ceiling. Routing a reviewer must not discard or reset the worker history. The caller must retain both streams and their prior decision records. These local assertions cannot establish that a caller supplied every real attempt.

Each recorded dispatch attempt contains its sequence, resource/provider IDs, tier, outcome, actual reported API cost and elapsed seconds, original decision/configuration hashes, and evidence references. Configuration/model replacements do not invalidate old resource IDs in history: the original saved decision retains the original configuration for replay. Histories must remain consecutive and monotonic in tier, may not repeat a decision ID, must honor explicit escalation, and cannot continue after a terminal outcome. Observations and outcome strings are supplied evidence assertions, not authenticated provider receipts.

Availability filters are explicit caller inputs. Filtering a disabled/unavailable resource does not consume an attempt. A recorded `PROVIDER_UNAVAILABLE` dispatch does consume one total attempt, excludes that provider for the rest of this revision/role history, and tries eligible alternatives at the same tier before higher authorized tiers. This gives fallback a finite bound. A recovered provider requires a deliberate recovery/history policy in the later executor; do not erase failed attempts to make it eligible.

## Selection and stopping rules

1. Validate the packet, configuration, binding and history. Workers require `READY` or `IN_PROGRESS`; reviewers require `REVIEW`. Packet states are metadata: the eventual executor must independently enforce the active bootstrap, complete dependency graph, permissions and acceptance gates.
2. Worker tiers are exactly `[min_tier] + escalation_path`, already bounded by `max_tier` in the contract. An empty path permits only the minimum. Reviewers use exactly `reviewer_tier`, which may exceed the worker maximum. Neither role can silently enlarge its allowed set.
3. Apply the maximum of the authorized minimum, configured risk floor, complexity floor and previously reached tier. High risk or complexity can skip cheap tiers. If the required floor exceeds the authorized set, stop for architect resolution; never downgrade.
4. Count failures at the current tier. After `failures_per_tier` recorded `FAIL` outcomes, or an explicit `NEEDS_ESCALATION`, require a strictly higher authorized tier. All recorded outcomes count against the total role attempt limit, including provider failures. A packet needs enough total attempts to reach its intended escalation path. The router does not execute a retry loop.
5. Exclude disabled/unavailable resources, unauthorized tiers, unsupported efforts, insufficient context, low estimated acceptance, and estimates exceeding the remaining per-role API cap. Compare input + output + estimated context-churn tokens to capacity. These are estimates; the executor must enforce real token limits, reserve spending and reconcile actual charges.
6. Choose the lowest estimated total cost per accepted result among eligible resources, breaking exact ties by resource ID. After an observed outage, eligible same-tier fallback has priority. Otherwise an economically better higher authorized tier may be selected immediately. Once selected and recorded in attempt history, a later decision cannot descend.

`PASS` stops further routing and requires the normal validation/independent acceptance gates; it does not mark the packet accepted. `BLOCKED` and `ARCHITECTURE_CONFLICT` stop for their existing resolution gates. Exhausted retry/API budgets, tier paths or resources produce explicit `STOP` records with reason codes. A spent positive API cap stops further routing even if a free resource is available; a configured zero cap permits zero-estimated-API resources. Ordinary resource exhaustion alone does not authorize contract or architecture changes.

## Economic estimate and future observations

All monetary inputs use USD; latency uses seconds, review uses minutes, and token prices use one million tokens. Policy values convert non-API effort/risk into comparable planning costs. For each candidate and exact effort:

```text
API cost = ((input tokens + estimated churn tokens) × input price
            + output tokens × output price) / 1,000,000
attempt cost = API cost + latency × wall-second cost
               + review minutes × review-minute cost
               + regression probability × regression penalty
expected cost per accepted result = attempt cost / acceptance probability
```

This stationary estimate expresses retry burden; it does not promise success within the remaining bounded attempts. Past API spend limits the next choice; past wall time is retained in the decision. Past costs are not charged twice in the candidate score. A local resource can have zero marginal API price and still lose on delay, context churn, review burden or acceptance probability.

Optional observations match **resource ID + task class + exact effort**. Supply per-attempt sample count, accepted count, regressions, mean latency/churn/review effort and a provenance reference. `accepted` must count objectively accepted results, not unreviewed worker `PASS` claims. Counts cannot exceed samples and duplicate aggregates are rejected. Means are per attempt, not already divided by acceptance probability. Each mean is blended with configured priors using `prior_samples`; acceptance/regression probabilities blend counts with weighted prior probabilities. Unmatched aggregates are retained in the request but do not affect ranking. Rename a resource when its model or behavior changes to prevent applying old-model observations to a new model. #12 will collect and evaluate observations; no collector or automatic calibration is claimed here.

Calculations use decimal arithmetic and deterministic resource ordering. Displayed costs are rounded to 12 decimal places; ranking uses unrounded values. Saved inputs allow exact replay with the recorded algorithm implementation. This is an auditable heuristic, not a global optimization proof or a hard billing limit.

## Save and replay the task-ledger decision

```bash
python scripts/model_router.py route task.ready.json --config config/model-router.json --request routing-request.json --output route-attempt-001.json
python scripts/model_router.py verify route-attempt-001.json
```

`route` requires a new output path and preserves existing files. It saves inputs plus the decision: packet revision/hash and role, configuration/request hashes, algorithm/policy version, reasons, every evaluated candidate's exclusion and score breakdown, remaining attempts, reported costs/time and selected model/provider/effort. `execution_authorized` is always false. A `STOP` decision is also saved, so a refusal is reviewable. Exit codes: 0 routed/replay/configuration success, 2 recorded stop, 1 invalid input or I/O refusal.

The record is the local task-ledger entry for #4. Retain it with the packet and later link/publish the decision summary through #6's GitHub ledger. Saved configuration/request snapshots preserve reviewability after a model swap. `verify` recomputes the decision from these snapshots, including all exclusions and hashes. It does not query external evidence or authenticate a caller, prove historical completeness, verify referenced earlier records, reserve money, or grant authority. Do not put credentials or raw sensitive prompts into routing records.
