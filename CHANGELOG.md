# Changelog

## 2026-09-13 — Issue #9 software + hardware domain template

- Add `config/domains/software-hardware.schema.json` and `scripts/software_hardware.py`: the software-hardware `domain` block becomes structural — one named component, hardware assumptions citing contract sources, protocol references, every validation mapped to one rung of the verification ladder, and a declared hardware status limited to `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING`.
- Register per-profile domain rules in `work_packet.DOMAIN_MODULES`, applied inside `validate_contract` on every contract-validation path and at the acceptance ATTESTATION event; no existing refusal, floor or gate is loosened.
- Bind the ladder to the acceptance split: machine rungs must declare a command the deterministic gate re-executes; hardware rungs must not, and their attestation must bind a validated hardware evidence record by digest with a `pass` outcome recorded by the attesting operator.
- Derive the earned hardware status from the acceptance ledger (`software_hardware.py status`): `VERIFIED_ON_HARDWARE` only for an accepted task whose hardware rungs were all attested; a machine-only acceptance never earns it.
- Extend the software-hardware bootstrap intake to nine required orientation fields; rewrite `templates/software-hardware/PROFILE.md` and `DOMAIN_PROFILE.md`; cross-reference the work-packet, acceptance and bootstrap protocols.
- Ship `examples/software-hardware/`: a fictional synthetic sensor bridge with 27 runnable tests decomposed into six component-scoped packets (one hardware-in-loop and one field attested check), a hardware evidence example and an operator procedure; update the software-hardware example contract.
- Add 25 tests (309 total); register 14 new required paths (81 total).

## 2026-09-13 — Issue #8 independent acceptance gates

- Add the acceptance controller: one append-only hash-chained ledger per reviewed task, filling the gap between the feedback controller's REVIEW_PENDING and the packet's REVIEW → ACCEPTED transition.
- Independently re-execute the contract's declared validation commands as the deterministic gate — the single deliberate exception to the metadata-only pattern — recording observed exit codes, bounded output and a workspace digest, and failing closed to non-implementer attestation for checks without a command.
- Assign risk-tier gate floors in the work-packet layer (low deterministic; medium + model review; high + cross-family; critical + architect review and user decision); packets and configuration can only tighten, and contract repair can no longer change risk or the review block.
- Render bounded, credential-scanned minimal-context review packets from ledger records only, separating worker-supplied claims from independently observed results; enforce five reviewer verdicts with structural refusals, submission-bound gate satisfaction, and a hard cross-family gate with recorded waiver.
- Return bounded rejections to the worker inside the same frozen budget with the contract failures in the next brief, escalate repeated identical rejections, and let acceptance — never a lone approval — close the task ledger.
- Dogfood the machinery on Issue #8's own diff: a Gate D failure contradicting the implementer's clean-run claim, a real gate-bypass finding from a minimal-context reviewer, the regression-tested correction, and acceptance only after re-review; record in `docs/ISSUE_8_VALIDATION.md`.

## 2026-09-13 — Issue #7 bounded execution harness

- Add a preparation-and-ingestion adapter that renders only packet-permitted context into a worker brief, emits the exact harness invocation, and never invokes a model or runs the harness command.
- Refuse a worker report that invents or omits a validation id, grades itself, widens scope, carries credential-like material or exceeds its bound; close an unreported attempt only through an explicit `abandon` with a stated reason.
- Refuse a dispatch whose brief, rules, declared harness overhead and reserved output cannot fit the window the routed resource is actually served in, closing the spent reservation with the arithmetic as evidence.
- Bind routed resources to harnesses by configuration with credentials named only by environment variable, and declare a non-Cline adapter so replaceability is demonstrated rather than asserted.
- Record four operator-executed live runs, including the passing one, with each failure's correction and the limitations carried forward in `docs/ISSUE_7_VALIDATION.md`.

## 2026-09-12 — Issue #6 GitHub task ledger

- Add canonical task/issue registration, complete packet and feedback publication, exclusive comment claims and pinned recovery.
- Detect live issue/PR/accepted-commit drift, unpublished records, untracked discoveries and stale structured project status.
- Deliver six issue forms and linked PR conventions; preserve explicit authority and metadata-only acceptance boundaries.

## 2026-09-12 — Issue #5 bounded feedback controller

- Reserve worker intents durably before dispatch and replay immutable events to recover task state and cumulative usage.
- Enforce total/per-tier limits, stable repeated-failure escalation, focused context, finite repair/recovery/diagnosis allowances and sticky architecture/approval holds.
- Require complete objective-check reports before moving to independent review; preserve raw failures, explicit provider recovery and bounded comment evidence views.
- Validate concurrency, crash/refusal paths and generated-profile delivery with synthetic records; retain actual acceptance in #5 and its PR.

## 2026-09-12 — Issue #4 capability router and economic governor

- Add provider-independent configuration with disabled fictional examples for LM Studio, Mistral, Claude and OpenAI/Codex.
- Select within exact effort and authorized tier paths using risk/complexity floors, accepted-result cost estimates, supplied performance observations and bounded retry/fallback policy.
- Save immutable local routing decisions with original inputs, reasons, exclusions, cost components and deterministic replay; retain explicit offline and execution-authority boundaries.
- Cover routing failure paths and delivery through generated projects; retain actual checks/review/acceptance in #4 and its PR.

## 2026-09-12 — Issue #3 work-packet contract foundation

- Add a shared JSON Schema contract and complete synthetic examples for all three domains.
- Generate GitHub issue views from canonical packets; preserve versioned snapshots and validate recorded lifecycle, roles, evidence references and dependency graphs.
- Keep packet tools local and optional to bootstrap; document their trust boundary and future executor/review responsibilities.
- Cover packet failure paths and generated root/native/standalone delivery; retain actual validation/review and acceptance evidence in Issue #3 and its PR.

## 2026-09-12 — Issue #2 bootstrap activation foundation

- Integrate inactive project generation, staged profile intake, complete review packets and explicit fingerprint-bound activation.
- Reject incomplete/malformed setup, stale configuration/documents, domain/workflow changes, cyclic dependencies and initialized-project rebootstrap.
- Apply the gate to every model startup and synchronize root/native/standalone payloads with a CI consistency check.
- Verify 32 tests, including all three profiles and Windows Git commit/clone approval portability; record independent review and remaining limitations in `docs/ISSUE_2_VALIDATION.md`.


## 2026-08-29 — v1.0.0

- Created universal multi-model project structure.
- Added native entrypoints for Codex, Claude Code, ChatGPT web, Claude web, and GitHub Copilot.
- Added bootstrap, validation, connector selection, skill selection, handoff, and source-ledger workflows.
