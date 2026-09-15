# Bounded worker feedback

`scripts/feedback.py` implements Issue #5's local controller around the canonical packet and #4 router: reserve a dispatch, inspect objective-validation reports, detect repeated failure, preserve focused escalation evidence, and stop for architect/human decisions. It makes **no model calls** and runs **no external validators**. Actual execution/cancellation belongs to #7, GitHub publication/reconstruction to #6, and independent acceptance to #8.

## One task, one authoritative ledger

Keep one ledger directory for a managed task across restarts and contract repairs. Do not initialize another directory to reset limits. Initialization requires current valid `ACTIVE` bootstrap approval, a matching project/packet domain profile, an exact `READY` packet in a complete supplied dependency graph, an architect identity and both policies:

```bash
python scripts/feedback.py init task-ledger --root . --packet task.ready.json --graph task.ready.json dependency.verified.json --policy config/feedback.example.json --config config/model-router.json --architect project-architect
```

For an independent task, `--graph` contains only its own packet. Supply an existing parent directory; existing ledger directories are refused. Install `requirements-work-packets.txt` first. Enabled resources support offline selection; default examples remain disabled and fictional, and neither state proves live provider access.

The sole authority is consecutively numbered, exclusively created JSON events (`00000001.json`, etc.), each with timestamp and previous/current hashes. Replay derives state, counters and packet views. Appends validate first, then exclusively create, flush and synchronize the new file before returning a dispatch. On POSIX, the containing directory is also synchronized, as is the existing parent when the ledger directory is created; file-only synchronization does not guarantee directory-entry persistence. A synchronization failure returns no dispatch intent and preserves any already-written reservation for reconciliation. Windows retains file synchronization; Windows namespace durability across power loss is unverified. Competing writers cannot both reserve the same next event. Partial writes, gaps, unexpected files, bad hashes, descending timestamps and unreproducible transitions fail closed.

A persisted pending reservation survives process restarts and blocks another dispatch. Reconcile the original result or confirmed cancellation with actual cost/evidence; never delete a pending record to retry. Results can still be recorded after approval is revoked. Results received after their deadline cannot pass. An on-time reported pass can reach `REVIEW_PENDING`, which grants no acceptance or execution authority. The future executor must enforce the deadline and stop actual processes: timestamps alone cannot stop compute or reconcile unknown charges.

This is local workflow integrity, not authentication, a hostile-code sandbox, complete cross-machine accounting or protection against coherent record rewriting/deletion or creation of another ledger. Successful filesystem durability operations are part of the trust boundary. #6/#7 must preserve authoritative task identity, state, permissions and reservations.

## Frozen finite limits

`config/feedback.schema.json` defines policy, results and diagnoses; `config/feedback.example.json` supplies editable defaults:

| Limit | Default |
|---|---:|
| Reserved attempts at T0/T1/T2/T3/T4 | 3/3/2/2/1 |
| Same failure at one tier / across the task | 2 / 3 |
| Contract repairs / ordinary blocker resumptions | 1 / 3 |
| Nonterminal architect diagnoses, including deferrals | 5 |
| Worker context / recent detailed failures | 40,000 characters / 5 |
| Attempt deadline | 600 seconds |

The packet's `retry_budget.max_attempts` caps the whole task. Optional `max_attempts_by_tier` overrides selected authorized worker tiers and cannot exceed that total. Effective limits are frozen at initialization. The router can escalate sooner under its own failure policy; caps are maxima, not instructions to exhaust each tier.

All reservations count, including pending/outage attempts and those before resource swaps, recovery or contract repair. Repairs preserve cumulative task/tier/failure counters. Previous-revision API spend reduces the router's remaining role cap; current-revision history retains original costs and decisions. The routing policy is frozen, while resource mappings may change. Estimates are not hard billing controls. This controller supplies no aggregate telemetry yet; #12 owns that integration.

Diagnosis limits bound nonterminal diagnosis records. A final confirmed architecture-change stop can always be recorded, even after that allowance is exhausted; its sticky human-decision state prevents repetition. If a model performs diagnosis, #7 must also run it through a separately bounded/reserved architect packet and reconcile its usage; recording a diagnosis is not a model invocation or billing receipt.

## Reserve, act, validate, report

Supply an options JSON object with exactly `task_class`, `input_tokens`, `output_tokens`, `unavailable_providers` and `unavailable_resources` (the latter two are arrays of IDs). Reserve before work:

```bash
python scripts/feedback.py next task-ledger --root . --config config/model-router.json --options routing-options.json
```

Success returns `DISPATCH`, a saved decision ID, deadline, router record and focused context; a slot has already been consumed. Exit 0 means an intent was reserved, not that a model ran. Exit 2 means a recorded hold; exit 1 means invalid input or a refused operation. Pending/stale/concurrent requests cannot silently reserve another attempt.

Context contains the current contract/revision/hash, counters, grouped first/latest failure evidence, bounded recent validation detail and latest architect guidance. It excludes full prior packet revisions, provider configuration and unrelated discoveries. Oversized required context stops for decomposition instead of truncating scope or acceptance. Character limits are not token counts or provider-capacity guarantees.

After actual work and objective validation, report a JSON object matching `$defs/result`: exact `dispatch_id`; bounded outcome/summary; `scope_status` (`within`, `violated`, `unknown`); `architecture_conflict`; `validation`; `evidence`; `discoveries`; `api_cost_usd`; and `cost_evidence`. Each validation entry contains the exact contract `check_id`, `passed`, `failure_code`, `expected`, `actual`, and evidence references. IDs must be unique and known. A failed check needs a stable nonblank code; successful entries can use empty diagnostic strings.

```bash
python scripts/feedback.py complete task-ledger result.json
```

Supported outcomes are `PASS`, `FAIL`, `BLOCKED`, `NEEDS_ESCALATION`, `ARCHITECTURE_CONFLICT`, and `PROVIDER_UNAVAILABLE`. Architecture diagnostics dominate every success label. Unknown/violated scope requires architect review. Late results fail for timeout. `PASS` requires every specified validation present and passed; contradictory reports become failures. An objective pass moves the packet to `REVIEW` and controller to `REVIEW_PENDING`, without acceptance or merge. Workers cannot replace contracts through result payloads.

Actual path/scope enforcement, test execution, source verification and independent review remain required: supplied flags/references do not prove these facts. Fingerprints retain validation IDs, stable failure category, expected/actual values, missing checks and scope/architecture/timeout indicators. ANSI presentation codes and whitespace are normalized; meaningful numbers/different values remain distinct. Freeform narration cannot evade repeated objective-failure detection. Raw reports remain immutable.

Ordinary failures retry/escalate only within the authorized path and frozen limits. Repeated task-wide failure stops for architect diagnosis. Unrelated discoveries remain evidence-backed issue proposals with originating attempt IDs; they never authorize expanded work. #6 will create/link those issues. `complete` performs no external write.

## Architect and human decisions

A worker architecture conflict immediately enters `ARCHITECTURE_HOLD` and stops dispatch. Scope concerns, repeated failures and exhausted limits require architect resolution. A diagnosis supplies `classification`, `reason`, `evidence`, the original `architecture_fingerprint`, and `revised_contract` (object only for repair; otherwise null):

```bash
python scripts/feedback.py diagnose task-ledger diagnosis.json --actor project-architect --root .
```

- `REPAIR_CONTRACT` requires unchanged current `ACTIVE` approval, initialized architect identity and remaining task/repair/diagnosis limits. Parent, scope, non-goals, interface, dependencies, architecture boundaries, domain and retry limits cannot change. A valid revision is rearchitected/readied while cumulative history, counters and spending remain. Permitted task-detail changes still require a supported architect judgment that architecture remains intact.
- `RESUME_WORK` releases only ordinary `BLOCKED` state under unchanged approval and finite limits. It records why the blocker was resolved. The raw blocked result remains immutable; its derived routing outcome becomes a failed prior attempt, retaining cost/count. Optional `resolved_providers` names only recorded unavailable providers whose recovery was established. Raw outages stay immutable; derived routing outcome becomes `PROVIDER_RECOVERED`, retaining reservations/cost without counting transport failure as objective model failure. Other outages remain excluded.
- `BLOCKED` records deferral without downgrading a stronger architecture/scope/repetition hold into a resumable blocker.
- `ARCHITECTURE_CHANGE` puts packet/controller in `NEEDS_DECISION`, requiring explicit user approval. Dispatch, repair and ordinary recovery are refused. Missing/invalid/changed approval before dispatch also records this durable hold. Recording a stop does not require active approval.

There is no ordinary recovery command out of `NEEDS_DECISION`. Prepare the changed architecture and explicit approval through `BOOTSTRAP_PROTOCOL.md`; preserve this ledger and its budgets when planning an authorized continuation. Later integration must define approved continuation/task migration explicitly. A fresh directory is not an automatic bypass.

Identity/fingerprint checks are workflow checks, not human authentication or proof that prose remains semantically within architecture. Architect classification and independent review remain essential. The controller revalidates its **saved initial graph**, not live prerequisites from other ledgers: #7 must check current authoritative dependency state and permissions before real dispatch. The snapshot cannot detect a prerequisite revised elsewhere.

## Inspect and prepare GitHub evidence

```bash
python scripts/feedback.py status task-ledger
python scripts/feedback.py context task-ledger
python scripts/feedback.py packet task-ledger
python scripts/feedback.py render task-ledger
```

`status` is the full derived evidence view; `packet` is a view, not a second controller authority. `render` prepares a bounded comment with counts/outcomes, failure groups, hashed evidence previews and exact immutable result/diagnosis event references. Truncation is marked; raw evidence remains in the ledger. Arbitrary diagnostics stay inside a suitably sized fenced JSON block. Oversized export is refused. #6 publishes/reconstructs records in GitHub; these commands make no external writes.

## Decision binding

An acceptance decision recorded through the `REVIEW` event is bound to one task revision and one worker result: it carries `binding` (task id, revision, contract hash) and `result_dispatch_id`, and the ledger refuses a decision whose binding differs from its packet or whose reviewed result is not the attempt awaiting review. The acceptance controller populates these from its own ledger; a hand-built decision must carry them too. This closes the path where one task's accepted ledger, supplied with another task's feedback ledger, moved an unreviewed task to `ACCEPTED`.

A ledger written before the binding was required still replays: a stored `REVIEW` event without `binding` and `result_dispatch_id` is validated under the pre-binding shape and its binding is not checked, because hash-chained history cannot be amended. The boundary is the presence of those fields and only replay of stored events may cross it; `review` refuses a new decision without them.
