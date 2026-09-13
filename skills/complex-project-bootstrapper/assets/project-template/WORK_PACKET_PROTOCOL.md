# Work-packet contract and local task records

The architect gives a worker one bounded contract: what to produce, permitted context and scope, interfaces, tests/evidence, capability and effort bounds, retry budget, review tier, and escalation path. `config/work-packet.schema.json` is the canonical structural contract for all three domain profiles. `scripts/work_packet.py` uses that schema directly; it adds cross-field, history and dependency checks.

`retry_budget.max_attempts_by_tier` optionally sets caps for specific tiers in the authorized worker path; each cap is a positive integer no greater than `max_attempts`. The feedback controller freezes effective limits and retains cumulative task/tier counters across contract repairs. See `FEEDBACK_PROTOCOL.md` for durable reservations, repeated-failure controls and architect/human holds.

These are **local metadata tools**. Creating a packet or recording `READY`, `ACCEPTED`, `MERGED` or `VERIFIED` does not execute anything, authenticate an actor, verify an external result, publish a GitHub record or grant autonomy. Actual execution must still pass `scripts/validate_bootstrap.py config/bootstrap.json --require-active` and the project's applicable permissions. Future harness, review, ledger and domain implementations must verify the assertions recorded here before relying on them.

## Install the packet-tool dependency

Use Python 3.12 and install the pinned validator in your chosen environment:

```sh
python -m pip install -r requirements-work-packets.txt
```

Existing bootstrap commands and `validate_project.py` remain standard-library-only. Only the packet tools/tests need this dependency. The standalone bootstrap distribution carries the schema, tool, requirements and examples into generated projects. CI installs the dependency before running the test suite.

The implementation uses [jsonschema's Draft 2020-12 validator and format checker](https://python-jsonschema.readthedocs.io/en/stable/validate/), with local schema references only. Shape validation is supplemented by the semantic checks below.

## Canonical packet structure

| Field | Meaning |
|---|---|
| `schema_version` | Packet format, currently `1.0`; unrelated to provider/model versions. |
| `task_id`, `domain_profile` | Stable task identity and one of `software-hardware`, `family-law`, `civil-rights-nc`. |
| `revision_history` | Ordered complete contract snapshots with consecutive version, hash, actor, timestamp and reason. The **last snapshot is the sole current contract**. |
| `state` | Current recorded state; it must match replay of all lifecycle events. |
| `events` | Consecutive events with kind, from/to, version/hash, declared actor/role, time, reason and evidence references. |

The contract contains:

- title, parent objective/milestone, goal and non-goals;
- allowed and prohibited scope; inputs, outputs and a named/versioned interface;
- task-ID dependencies, assumptions and identified authoritative sources;
- acceptance criteria and specified validations linked to those criteria, including required evidence;
- complexity/risk, minimum/maximum capability tiers, reasoning effort and reviewer tier;
- finite retry allowance, ordered escalation tiers, minimal context and architecture boundaries;
- `domain` extension data. Extensions cannot replace or weaken required common fields.

A profile may register domain rules over its `domain` block in `DOMAIN_MODULES` in `scripts/work_packet.py`; `validate_contract` applies them after the common checks wherever a contract is validated — packet validation, feedback contract repair and acceptance initialization — so a profile rule cannot be bypassed by choosing the path. The `software-hardware` profile registers `scripts/software_hardware.py`: one named component per packet, hardware assumptions citing contract sources, every validation mapped to one rung of the verification ladder, a declared `command` required at machine rungs and refused at hardware rungs, and `hardware_status` limited to `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING` because `VERIFIED_ON_HARDWARE` is earned in the acceptance ledger, never authored. `examples/software-hardware/` is the worked decomposition.

Capability tiers are integers 0–4 with the meanings in `AUTONOMY_CONTROL_PLANE.md`. Reasoning effort is the provider-independent classification `low`, `medium`, `high` or `very_high`; the future router maps it to an available provider's settings. Minimum tier must not exceed maximum. Escalation tiers must strictly increase above the starting minimum and remain within maximum. Reviewer tier is a separate policy field. Risk-specific review policy and actual attempt enforcement remain the later review/router/worker controls.

All required descriptions are nonblank. Every acceptance criterion must have a specified validation; criterion references and source/validation/criterion IDs must be valid and unambiguous. Required arrays must be populated except dependencies, assumptions and escalation, which may legitimately be empty. If a task has no external input, explicitly describe its internal fixture or no-input interface. Source records may reference an embedded synthetic specification rather than an external document.

## Create and render a contract

Three complete, fictional contract examples are under `examples/work-packets/`. The legal examples demonstrate record indexing/extraction, not legal conclusions or real matters. The software example is a synthetic protocol, not physical hardware evidence; its `domain` block is the structural form the software-hardware profile now requires.

Run from the project root; use a new output filename for every operation:

```sh
python scripts/work_packet.py create examples/work-packets/software-hardware.contract.json --task-id TASK-1 --profile software-hardware --actor "Architect" --reason "Initial bounded decomposition" --output task-1-proposed.json
python scripts/work_packet.py validate task-1-proposed.json
python scripts/work_packet.py graph task-1-proposed.json
python scripts/work_packet.py render task-1-proposed.json --output task-1-issue.md
```

For another domain, use its contract file and matching `--profile`. Creation requires a complete contract and always records version 1 at `PROPOSED`. No command infers approval from an example or from successful validation.

`render` produces a deterministic GitHub issue body containing the entire current contract, identity/version/hash, revision provenance and latest recorded event. Domain extensions appear as fenced JSON so arbitrary keys, nested arrays and scalar types retain their exact meaning. It omits old contract bodies to keep worker context bounded. Keep the canonical JSON in the project's controlled work-record location and link it when publishing the generated issue. Do not maintain an independently edited copy of the issue contract. `templates/TASK.md` points to this generation workflow; automatic GitHub publishing and the broader issue-form family belong to #6.

## Record the lifecycle

The normal path is:

```text
PROPOSED -> ARCHITECTED -> READY -> IN_PROGRESS -> VALIDATING -> REVIEW
REVIEW -> ACCEPTED -> VERIFIED
                   -> MERGED -> VERIFIED
```

`ACCEPTED` supports non-code results such as reviewed research artifacts. A merge record follows acceptance; an integrator cannot skip review by jumping directly from `REVIEW` to `MERGED`.

| Transition | Declared role | Additional local check |
|---|---|---|
| PROPOSED → ARCHITECTED → READY | architect | READY requires a complete dependency graph when dependencies exist. |
| READY → IN_PROGRESS → VALIDATING | worker | Starting requires all dependencies recorded VERIFIED. |
| VALIDATING → IN_PROGRESS | worker | Bounded correction record; the executor must enforce the retry budget. |
| VALIDATING → REVIEW | worker | Nonempty evidence references. |
| REVIEW → IN_PROGRESS | reviewer | Evidence references explaining bounded rejection. |
| REVIEW → ACCEPTED | reviewer | Evidence references; actor must differ from every implementation actor recorded for this revision. |
| ACCEPTED → MERGED or VERIFIED; MERGED → VERIFIED | integrator | Nonempty evidence references. |

From a nonterminal working/paused state, an architect, worker or reviewer may record `BLOCKED`, `ESCALATED`, `ARCHITECTURE_CONFLICT` or `FAILED`; only the architect records `NEEDS_DECISION` or `SUPERSEDED`. Self-transitions are not allowed. Paused states return to `ARCHITECTED` through an architect event with evidence references, then pass readiness again. This event merely records a claimed resolution; a human-decision or architecture conflict still requires its actual approval outside this metadata tool. `SUPERSEDED` has no ordinary outgoing transition. Contract revision is a separate architect operation.

For example, these commands record planning metadata only:

```sh
python scripts/work_packet.py transition task-1-proposed.json --to ARCHITECTED --role architect --actor "Architect" --reason "Contract reviewed against the approved decomposition" --output task-1-architected.json
python scripts/work_packet.py transition task-1-architected.json --to READY --role architect --actor "Architect" --reason "No task prerequisites" --output task-1-ready.json
```

Use repeated `--evidence` arguments for evidence references when required. Files are created exclusively: existing inputs, outputs and previous versions are never overwritten by supported commands. To record another change, choose another output path. Commit those records according to the project ledger policy.

## Dependencies and the first task graph

The architect supplies complete contract JSON for the initial decomposition. The tool automatically wraps those contracts into packets, validates their complete dependency graph, and renders their issue representations; it does **not** infer task decomposition from free-text intake or invoke a model.

```sh
python scripts/work_packet.py graph prerequisite-verified.json dependent-architected.json
python scripts/work_packet.py transition dependent-architected.json --to READY --role architect --actor "Architect" --reason "Prerequisite result recorded verified" --graph prerequisite-verified.json dependent-architected.json --output dependent-ready.json
```

Supply exactly one current record for each task in the complete transitive graph. Duplicate IDs, unknown dependencies, self-dependencies and cycles are rejected. Ordering is deterministic. A packet in READY or any later normal state requires each dependency to be recorded `VERIFIED`; this is deliberately stricter than merely accepted or merged. Revalidating the graph therefore catches a prerequisite whose newer contract revision has invalidated its readiness.

For transitions supplied with `--graph`, the graph's target record must exactly match the packet being transitioned, including history and current state. The resulting graph is validated with the updated target. A dependent task cannot advance by supplying an unrelated or stale target record. Validate complete graphs before interpreting any single packet as eligible for execution; single-packet validation cannot establish external dependency completeness.

The complete interactive-intake → architect-generated first task graph → approval → live worker demonstration remains an end-to-end integration requirement for #13, using these #3 contracts and the later routing/harness controls. The audit's need for that explicit integrated acceptance test remains recorded as a clarification; this tool does not claim to complete it.

## Contract changes and provenance

Prepare a complete revised contract JSON, then:

```sh
python scripts/work_packet.py revise task-1-ready.json --contract revised-contract.json --actor "Architect" --reason "Clarify the output error contract" --output task-1-v2-proposed.json
```

This preserves all prior snapshots and events, appends one full snapshot, and resets the state to `PROPOSED`. Previous implementation/review events continue to reference their original revision and do not approve the new version. A no-change revision is rejected. The revised task must pass architecture/readiness again. An actual material architecture change still requires the bootstrap/human decision process; recording a new packet does not supply that approval.

The SHA-256 binds schema version, task identity, profile, contract revision and the full contract, including all domain extensions. Validation checks every historical snapshot and replays event ordering, hashes, state edges, declared roles and timestamps. It catches accidental edits without a corresponding coherent revision trail. Actor/time/reason are preserved in the revision's matching creation event.

This is local workflow integrity, not cryptographic authentication or tamper resistance against someone who can rewrite and rehash the entire record. Declaring a different actor name does not establish independence. Evidence references are strings: the later verifier must check their actual content, task revision, adequacy and authenticity. Similarly, allowed/prohibited scope are explicit contracts, not a filesystem sandbox. The future harness must enforce them, the finite retry policy, real review gates and the bootstrap activation gate.

## Validation and distribution

```sh
python -m unittest discover -s tests -p "test_work_packet.py"
python scripts/validate_project.py
python scripts/sync_skills.py --check
```

The test suite exercises all three profiles, malformed contracts/history, legal and illegal state transitions, actor separation, revisions, dependency failures, deterministic rendering, command-line errors and preservation of prior files. Synthetic records do not establish real legal, hardware, provider or deployment outcomes.
