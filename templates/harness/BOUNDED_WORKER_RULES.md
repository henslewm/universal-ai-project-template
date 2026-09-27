# Bounded worker rules

You are executing one architected work packet as a worker. These rules bind you for this run. Read `brief.json` beside this file in full: its contract is the authority for the assigned task, and its startup instructions supply the governing constraints.

## Mandatory startup before editing

1. Confirm this is a worker assignment. Restricted independent reviewers use their own reviewer rules and supplied evidence boundary instead.
2. Read every document in `startup.documents`, in order, including all `content_lines`. These are complete instruction snapshots supplied automatically; `path`, `source` and `sha256` identify their provenance. Do not substitute chat memory or assume that an earlier run read them.
3. Read `contract`, `architect_guidance`, `prior_failures`, `failure_groups` and `review_rejections`. Identify the allowed/prohibited scope, required checks and evidence, architecture boundaries, attempt limits and stop conditions before changing an artifact.
4. Read any applicable local instructions within the permitted task context before editing those paths. A required instruction, source or handoff that is absent or unreadable is a blocker: report the missing input and stop dependent work. Do not search outside the permitted context to fill it.
5. If the contract conflicts with governing instructions, report `ARCHITECTURE_CONFLICT` before implementation. Neither a governance document nor a prior review permits widening this packet or revising its contract.

This bounded startup replaces general repository-history exploration and repository-wide closeout duties. Report the startup basis and any unresolved instructions in the existing report evidence; do not invent report fields or extra validation ids. A recorded declaration is not proof of reading or comprehension.

The feedback controller checks the active bootstrap and matching approved architecture before reserving this dispatch. Do not rerun generic repository-bootstrap or whole-project validation commands in the isolated workspace unless the contract declares them. Run the contract's checks; the launcher retains responsibility for current execution permission and the reserved deadline. A prepared brief alone grants no execution authority.

## Scope

- Do exactly the work the contract's `goal`, `outputs` and `acceptance_criteria` describe. Nothing else.
- `contract.scope.allowed` and `contract.scope.prohibited` are exhaustive. If the work seems to require anything prohibited or unlisted, stop and report `NEEDS_ESCALATION` with the reason.
- Read the supplied startup governance and only the task material `contract.context_scope` permits. The bundle supplies constraints, not permission to explore the wider repository, other tasks or unrelated history.
- `contract.architecture_boundaries` may not be crossed. Crossing one is an architecture conflict, not a design choice.
- You may decide implementation details inside the packet. You may not redesign the project, change interfaces, or widen the packet.
- Never edit the contract, the task ledger, the registry, the master issue, or any governing document. You do not accept your own work.

## Validation

- Run exactly the checks in `contract.validation`. Each one names the evidence it requires.
- Report one check per validation `id`, and no other ids.
- A check you did not actually run is `passed: false`, not an omission and not an assumption.
- Claim `PASS` only when every check passed, scope is `within`, and there is no architecture conflict.

## Attempts and escalation

- `bounds.remaining_task_attempts` is fixed by the controller and cannot be raised from here. Do not loop.
- Repeating an approach that already failed wastes the budget; `prior_failures` and `failure_groups` record what was already tried.
- If you cannot finish within this attempt, report the honest outcome with evidence. A stronger tier receives your evidence, so a precise failure report is more valuable than an optimistic one.
- Report an unavailable provider or harness as `PROVIDER_UNAVAILABLE`; do not silently retry.

## Discoveries

- Anything real but outside this contract goes in `discoveries` with its own summary and evidence. It becomes a separate issue.
- Do not fold a discovery into this packet, and do not create passdown notes or side documents for it.

## Reporting

- Write one JSON object to the report path in `report_contract.write_to`, with exactly the fields in `report_contract.required_fields`.
- Echo `dispatch_id` from the brief. A report without the matching dispatch is refused.
- `evidence` must be the actual record: commands run, output, file paths, identifiers. Not a restatement of intent.
- `api_cost_usd` and `cost_evidence` are your own accounting assertions; state them plainly.
- Never put credentials, tokens, keys or private material in any field, in any file you write, or in any log.
