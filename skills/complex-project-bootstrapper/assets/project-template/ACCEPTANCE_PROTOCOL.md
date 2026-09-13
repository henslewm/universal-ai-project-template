# Independent review and acceptance gates

Work is accepted on contract and evidence, never on an agent declaring success. This implements Issue #8.

The acceptance controller occupies exactly one gap: between the feedback controller's `REVIEW_PENDING` — an objective worker `PASS` awaiting judgment — and the packet's `REVIEW → ACCEPTED` transition. Everything around that gap already exists and is reused rather than duplicated. `WORK_PACKET_PROTOCOL.md` owns the contract, its risk classification and the gate floor that risk requires. `MODEL_ROUTING.md` owns reviewer-tier selection and its decision ledger. `FEEDBACK_PROTOCOL.md` owns the attempt budget the corrective work after a rejection is spent from. `EXECUTION_HARNESS_PROTOCOL.md` owns dispatching that corrective work. `GITHUB_LEDGER_PROTOCOL.md` owns publishing the acceptance row this controller's record justifies.

`scripts/acceptance.py` keeps one append-only, hash-chained ledger per reviewed task. It never invokes a model and never runs a harness. It does execute one thing, and that exception is the point: the contract's own declared validation commands, so that the deterministic gate records what was **independently observed** rather than transcribing what a worker asserted. Issue #7 established that a worker report is supplied evidence, not proof; this controller is where the difference is enforced.

## Gates and the risk floor

Every contract's risk tier fixes a floor of required gates, declared once as `REVIEW_FLOORS` in `scripts/work_packet.py`:

| Risk | Floor |
|---|---|
| `low` | deterministic |
| `medium` | deterministic + model review |
| `high` | deterministic + model review + cross-family |
| `critical` | deterministic + model review + cross-family + architect review + user decision |

A packet may assign more in its optional `review.required_gates` block, and project configuration may add gates per risk in `additional_gates`; neither can remove a floor gate, and contract validation refuses a block below its floor. A contract repair cannot change `risk` or `review` — a repair exists to fix wording, never to lower the gates. Review requirements are therefore assigned in the work packet, and loosening them is structurally impossible rather than merely prohibited.

- **Deterministic** (`run-checks`): executes each validation's architect-declared `command` in the reviewed workspace — exact argv, no shell, bounded timeout and output, credential-scanned before recording — and records exit code, output, duration and a digest of the workspace it checked. A validation without a command is `NOT_MACHINE_RUNNABLE` and fails closed: acceptance then requires a recorded operator attestation for that check, and an operator may never attest over a runnable check or their own implementation. This gate runs first because it is the cheapest; a reviewer is never engaged before it passes.
- **Model review** (`prepare-review` / `ingest-review`): one independent reviewer at the packet's `reviewer_tier`, working from the review packet alone.
- **Cross-family** (high and critical): the approving reviewer's declared model family must differ from every implementation actor's, or an explicit `waive-cross-family` with a stated reason is recorded and becomes part of the acceptance evidence. The waiver is visible, never silent, and is cleared by resubmission.
- **Architect review** (critical): a review performed by the recorded architect identity.
- **User decision** (critical): an explicit recorded approval by a non-implementer decider.

## The review packet

`prepare-review` renders the reviewer's entire context from the ledger's own records — nothing is curated in, and there is no second, looser copy of the contract. It contains: the exact contract revision under review; the worker's result labeled `result_supplied_by_worker`; the artifact (bounded diff or file content with digest, or an exact reference when oversized); the deterministic gate's results labeled `independent_validation` — the reviewer sees both streams and any disagreement between them is itself a finding; recorded attestations; prior review rounds with their verdicts and failures; the packet's open questions; and the report contract with its exact field shapes read from the schema, so the terms are stated rather than guessed. The rendered packet is bounded in both canonical and indented form and credential-scanned in both, and a `review_id` binds the report to this opening and no other. This is what keeps premium reviewer context minimal: the reviewer never rereads the project.

## Reviewer verdicts

`APPROVE`, `REJECT_BOUNDED`, `NEEDS_EVIDENCE`, `NEEDS_ESCALATION`, `ARCHITECTURE_CONFLICT`. A report states one finding per acceptance criterion with evidence cited from the packet; `met` without evidence, an unknown criterion id, a mismatched review id or reviewer identity, an oversize body, credential-like material, or `APPROVE` with any criterion not met is refused rather than recorded. A review that produced no usable report closes only through `abandon-review` with a stated reason; absence is never inferred.

`REJECT_BOUNDED` must name specific contract failures — an existing criterion, validation, or scope/architecture rule, what failed, evidence, and a corrective action performable **inside the current contract**. A fix that needs a wider contract is an escalation, never a corrective action, which is how review cannot silently change scope in either direction: the reviewer cannot edit the contract, and the rejection cannot smuggle new requirements into the worker's next attempt. A rejection repeating an earlier rejection's fingerprint escalates to the architect instead of looping, and reviews are bounded by `max_review_attempts`.

## Acceptance and what follows

`accept` refuses unless every required gate has a passing record on this ledger: deterministic satisfied, the latest completed review per required review gate approving, the cross-family rule or its recorded waiver, the user decision where required — and the recording actor is the approving reviewer (or the controller for a deterministic-only packet) and not an implementation actor. Only then is the task's closure justified: `sync-feedback` records the condensed decision in the feedback ledger, which performs the packet's `REVIEW → ACCEPTED` transition — or, for a rejection, `REVIEW → IN_PROGRESS` with the contract failures carried into the next worker brief as `review_rejections`, spending the same frozen attempt budget. For a packet not under a feedback ledger, `apply` performs the same transition on the packet file. `verify-review` applies the report contract to a packet/report pair with no ledger; it records nothing and accepts nothing.

```text
python scripts/acceptance.py --config config/acceptance.json validate-config
python scripts/acceptance.py --config config/acceptance.json init LEDGER --packet packet.json --result result.json --artifact artifact.json --implementers implementers.json --controller "..." --architect "..."
python scripts/acceptance.py --config config/acceptance.json run-checks LEDGER --workspace DIR
python scripts/acceptance.py --config config/acceptance.json attest LEDGER --validation-id V-2 --operator "..." --evidence "..."
python scripts/acceptance.py --config config/acceptance.json prepare-review LEDGER RUNDIR --gate model_review --reviewer-actor "..." --model-family "..." --tier 3
python scripts/acceptance.py --config config/acceptance.json ingest-review LEDGER RUNDIR/review-report.json
python scripts/acceptance.py --config config/acceptance.json accept LEDGER --actor "..."
python scripts/acceptance.py --config config/acceptance.json sync-feedback LEDGER FEEDBACK_LEDGER
python scripts/acceptance.py --config config/acceptance.json verify-review RUNDIR/review-packet.json RUNDIR/review-report.json
```

## Domain rules at the gates

A profile registered in `scripts/work_packet.py` can add rules at two points and nowhere else: its contract rules run inside `INIT` through the common contract validation, and its attestation rule runs inside `ATTESTATION` after the common refusals. For `software-hardware`, a validation at a hardware rung (`hardware_in_loop`, `field`) has no command by construction, so it always reaches this gate as `NOT_MACHINE_RUNNABLE`; its attestation must then carry the lines `scripts/software_hardware.py hardware-evidence` prints for a validated hardware evidence record — the record digest, its rung, device identity, firmware, observation time, a `pass` outcome and the recording operator, who must be the attesting operator. A failed observation is never attested; it returns to the worker as a failure. `software_hardware.py status LEDGER` then derives the earned hardware status from this ledger's records alone: `VERIFIED_ON_HARDWARE` only when the ledger is `ACCEPTED` and every hardware-rung validation is attested, and `UNVERIFIED_ON_HARDWARE` for any accepted task whose checks were all machine-runnable, however green they were.

## Boundaries

The controller enforces independence against **declared** identities: reviewer actor, model family, implementers, attesting operators and deciders are recorded declarations it cannot authenticate, and the protocol says so plainly rather than implying otherwise. A misdeclared reviewer family defeats the cross-family gate exactly as an understated context window defeats the capacity gate; the declaration is in the record, so it is auditable, not invisible. The deterministic gate executes only commands the architect committed into the contract, in the reviewed workspace, and executing a check is not accepting work. Evidence a reviewer cites is evidence from the packet; the controller does not verify external claims. Acceptance here justifies — but does not perform — merge, publication, or closure, which remain with the integrator, the GitHub ledger, and their own authorities. No credential belongs in configuration, packets, reports, ledgers or logs.
