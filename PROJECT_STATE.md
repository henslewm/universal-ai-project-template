# Project State

- **Status:** TEMPLATE MAINTENANCE — end-of-day checkpoint prepared; local commit remains pending because this session cannot create `.git/index.lock`. `HANDOFF_CURRENT.md` names the guarded host-terminal commit helper. Issue #10's review conflict is reconciled to REJECT_BOUNDED on an unresolved `AC-ADVERSE` defect; the original acceptance ledger remains pending, not accepted. Resume substantive work only when the user returns.
- **Last verified:** 2026-09-18 UTC
- **Active branch:** `issue-10-family-law-domain` (off `main` at `d2350ec25474816545b4418a4c8c5cd97516e2c6`)
- **Controlling scope:** [Locked master #14](https://github.com/henslewm/universal-ai-project-template/issues/14); title/body/order unchanged.
- **Active child:** [Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10) — complete high-conflict NC family-law evidence/research template. The implementation at `29422ca` includes the round-1 and round-2 fixes. The original round-3 report rejects an `AC-ADVERSE` omission reproduced this session; its separate scope finding makes the report invalid for ingestion as written. A local reviewer withdrew their initial APPROVE on reconsideration and supplied an offline-valid REJECT_BOUNDED report (four of five criteria, one failure). No report has been ingested. Issue #10 remains open; no PR exists for this branch. See `docs/ISSUE_10_VALIDATION.md`, ADR-061/ADR-062 and `HANDOFF_CURRENT.md` before continuing.

## Verified foundation

Issues #2 through #9 are closed through merged PRs #15 to #34. #9 (complete software + hardware domain template and hardware-in-loop discipline) was accepted through its dogfood at `_acceptance-demo-9b` on 2026-09-14 (11 events, cross-family approval, no waiver, after ADR-026 to ADR-029), then its PR #34 went through 23 rounds of Codex review before a clean result and merge on 2026-09-15 at `d873ec5cd1be503a19880eacbaf9cfba764d9fa5`. Decisions ADR-041 through ADR-055 record every round; `docs/ISSUE_9_VALIDATION.md` holds the full mapping.

#9 delivered the software-hardware domain module (`scripts/software_hardware.py`, `config/domains/software-hardware.schema.json`) that structurally distinguishes a simulated pass (`command`, re-executed by the deterministic gate) from hardware-in-loop or field verification (an operator attestation binding a structured evidence record by digest, never a contract-declared claim). The 23-round review closed a class of gap in the generic acceptance controller that later domain modules should expect too: binding an operator's evidence to exactly the submission it was observed against is several independent checks, not one — the contract's revision and hash, the submitted result's dispatch identity, the artifact's actual identity (not merely a hash a reference-kind artifact can leave at a fixed empty-content value), and the observation's own timestamp bounded on both sides by the current submission and the attestation event. `acceptable()` also now distinguishes replaying an already-accepted ledger's history from justifying a brand-new acceptance today, so a stored decision that rested on since-invalidated evidence keeps replaying as history without letting a *new* decision rest on the same thing.

This is an unactivated reusable template under explicit maintenance authority. No real project registry, provider calls, credentials or permission changes are required. Generated projects should link their generated structured project-state index here and audit it against GitHub; task narration belongs in canonical issue comments.

## Post-#9 follow-up (PR #35, ADR-058)

An independent review of merged `main` after PR #34 found two real defects (ADR-056, ADR-057). PR #35's own review found ADR-057's zero-timeout `receive()` fix incomplete — it reopened the ADR-042 late-arrival hazard from the other direction and left a pre-existing chunked-frame bug unfixed, because no wall-clock/deadline measurement can distinguish "already-buffered data trickling in" from "data that arrived after the poll instant." The fix (ADR-058) adds `Port.available()`, sampled once per zero-timeout `receive()` as a fixed byte budget. A second review round found the sample itself ran outside the `_wire()` close-on-failure guard; both that and a stale documented test count were fixed. Merged 2026-09-16 at `d2350ec` after Codex and an independent reviewer both reported the final head clean.

## Issue #10, session 1 (family-law domain mechanism)

`scripts/family_law.py` and `config/domains/family-law.schema.json` apply the exact
acceptance-controller split #9 built (machine-runnable command vs. non-implementer attestation
bound to a digest-referenced evidence record), registered generically through
`work_packet.DOMAIN_MODULES` with no controller change required. The charter's six fact
categories (VERIFIED FACT, ALLEGATION, DISPUTED FACT, INFERENCE, LEGAL PROPOSITION, UNKNOWN) map
onto `fact_basis`/`fact_assertions` the same way #9's hardware status does: `VERIFIED_FACT` is
earned in the ledger, never authored in a contract. `adverse_authority` (required for any
`LEGAL_PROPOSITION` assertion) has no software-hardware precedent. One genuine addition beyond
the hardware mirror: `status` reports a third earned outcome, `CONTRADICTED_BY_SOURCE`, because
unlike a hardware pass/fail a primary source can legitimately contradict the claim it was
consulted to check — surfaced ahead of every other reason rather than read as merely unverified.
`DOMAIN_FIELDS["family-law"]` was expanded from 3 thin fields to the 10 the charter requires, kept
synchronized across the validator, `config/bootstrap.schema.json`, and the intake reference from
the start (applying #9's ADR-040 lesson proactively rather than discovering the drift later). See
ADR-059 and the design comment on Issue #10 for the full mechanism.

## Issue #10, session 2 (repeat-dogfood acceptance run)

Ran the repeat-dogfood exercise on `_acceptance-demo-10` (outside this repository), matching `_acceptance-demo-9b`'s shape: `INIT`, `CHECKS`, then successive `REVIEW_OPEN`/`REVIEW_RESULT`/`RESUBMIT` rounds. Round 1 (fresh same-family Claude subagent) found `AC-DECOMPOSITION` overclaimed — only one of the four example packets' commands had actually been run through the gate; fixed by a regression that runs all four (commit `f47a43d`). Round 2 (cross-family Codex) returned `REJECT_BOUNDED` on `AC-PROVENANCE` and `AC-ADVERSE`: `record_problems` accepted any nonblank `claim_verified` rather than one matching a declared assertion, and the revision/contract-hash binding lived only in the record-basis `status --evidence-dir` path, so the default attestation-only path could earn `VERIFIED_FACT` unbound. Fixed via ADR-060 (commit `29422ca`); post-fix checks passed cleanly (398 tests, `validate_project.py` OK, 0 payload diffs).

Round 3 remains open in the original ledger (12 events, ending at `REVIEW_OPEN`; three of three review openings used). The original `review-3/review-report.json`, absent at an earlier check, appeared during closeout and contains `REJECT_BOUNDED`. Its scope finding uses `failed_ref: "scope.allowed"` rather than an allowed/prohibited literal, so offline report verification rejects it. Its substantive `AC-ADVERSE` finding was reproduced: FAM-04 declares `LEGAL_PROPOSITION` and only `citation_linked` validation, yet contract validation returns no errors. No implementation fix was made at this checkpoint. ADR-061 is preserved; ADR-062 records the concurrent evidence and reconciles the next steps.

## 2026-09-18 checkpoint

The user expressly authorized the prepared Issue #10 maintenance exception and requested cleanup, a commented local commit, pickup instructions and a stop for the day. This does not activate the reusable template or change generated-project bootstrap gates: `config/bootstrap.json` remains absent and the ACTIVE gate fails.

Fresh local validation passed 398 tests in 205.068 seconds and 81 required project paths, using Python 3.12.14 with the existing `jsonschema` 4.26.0 installation. A clean tracked archive of `29422ca` passed the 81-path validator and reported zero skill-payload differences. Before checkpoint synchronization, the live checkout's sync check flagged only ignored `.claude/scheduled_tasks.lock` runtime state; that file is preserved and must not be copied into distribution payloads. Final checkpoint validation belongs to the committing session and must not be inferred from these earlier checks.

The initial local APPROVE report is preserved at `docs/reviews/ISSUE_10_ROUND_3.json` as superseded evidence and must not be ingested. The external rejection is preserved unchanged at `docs/reviews/ISSUE_10_ROUND_3_EXTERNAL.json`. The local reviewer's reconsidered report, `docs/reviews/ISSUE_10_ROUND_3_RECONCILED.json`, verifies as valid REJECT_BOUNDED, four of five criteria met, one failure, `recorded_in_ledger: false`, `acceptance_granted: false`. The passing 398-test suite does not cover the reproduced missing-rung condition. The original ledger remains unchanged at the pending third/final review (`reviews_used=3`, `max_review_attempts=3`). No new ledger, budget reset, waiver or external write was performed.

## Continuation

Stop at this checkpoint. On user resumption, follow `HANDOFF_CURRENT.md`: the architect first resolves the pending review, packet scope for required closeout documents and exhausted review budget, then defines the bounded `AC-ADVERSE` fix and regression work. A permitted runtime may consider ingesting the reconciled same-opening rejection only after verifying the pending ID and artifact binding and explicitly choosing the authoritative report while preserving the original. Do not ingest the superseded approval, overwrite conflicting evidence, reset the budget or open a fourth review. PR preparation and final-head Codex review follow acceptance; merge retains its explicit user-authorization requirement. Do not start #11. OL-016's packaging limitations and #12's model-performance calibration remain deferred. Do not edit the locked master or delete construction branches outside later authorized cleanup.
