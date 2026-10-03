# Issue #10 validation and review

Issue: [Complete high-conflict NC family-law evidence/research template](https://github.com/henslewm/universal-ai-project-template/issues/10). The design was approved by the maintainer and posted as a comment on the issue before implementation (ADR-059). Implementation is on `issue-10-family-law-domain`.

## Status of this record

**Accepted 2026-09-27** through the acceptance controller at `_acceptance-demo-10b` beside the repository. This is a 5-event hash-chained ledger (`INIT`, `CHECKS`, `REVIEW_OPEN`, `REVIEW_RESULT`, `ACCEPT`, head `472d2a60…`) for task `ISSUE-10-ACCEPTANCE`, contract revision 2. The deterministic gate passed, and one cross-family (openai) review approved, so no waiver was needed.

`_acceptance-demo-10` (revision 1) is preserved as **provisional** history. It stopped at event 12 with round 3 dispatched and not ingested (ADR-061); see the next section. Acceptance justifies, but does not perform, the PR, merge and closure. Those remain the maintainer's.

## Acceptance criteria of Issue #10 mapped to evidence

| # | Criterion (issue #10) | Dogfood criterion | Evidence |
|---|---|---|---|
| 1 | A fresh family-law project can be bootstrapped interactively | `AC-BOOTSTRAP` | `validate_bootstrap.DOMAIN_FIELDS["family-law"]` requires ten orientation fields: case identity, controlling orders, objectives and deadlines, discovery, evidence, financial support, parenting/custody, adverse facts, appellate preservation, and reserved actions. They are kept identical in `config/bootstrap.schema.json` and the intake reference, and a placeholder answer is refused. |
| 2 | Evidence provenance and fact-status rules are mechanically represented | `AC-PROVENANCE` | `config/domains/family-law.schema.json` and `scripts/family_law.py`. Assertions are declared `ALLEGATION`, `DISPUTED_FACT`, `INFERENCE`, `LEGAL_PROPOSITION` or `UNKNOWN`, each citing a contract source. `VERIFIED_FACT` is refused anywhere in a contract. It is earned only from an accepted ledger whose primary-source rung was attested against a digest-bound source record, re-verified, and covering every declared assertion (ADR-060). A record covers an assertion only when it reviewed a source that assertion names in `verified_by` (ADR-068). A contradicting or inconclusive record never earns it. |
| 3 | Legal issue packets require adverse authority and primary-source verification | `AC-ADVERSE` | A packet declaring a `LEGAL_PROPOSITION` is refused without non-empty `adverse_authority`, and (ADR-065) without at least one `primary_source_verified` validation. That rung must not declare a command; it is satisfied only by a non-implementer attestation binding the record by digest, revision, contract hash, dispatch identity, artifact identity, validation id and a bounded observation time. `FAM-04-issue-brief` declares both. |
| 4 | The project can progress task-by-task through GitHub without relying on chat memory | `AC-DECOMPOSITION` | `examples/family-law/`: four fictional, component-scoped packets (docket, support, custody, issue brief) validate under the closed schema, declare `synthetic: true`, and have their declared commands executed through the deterministic gate. |

The fifth dogfood criterion, `AC-SPLIT`, was met in every round. It requires reusing the existing command-versus-attestation split rather than a parallel mechanism, registering through `work_packet.DOMAIN_MODULES`, loosening no controller refusal, floor or gate, and preserving stored-versus-new replay.

## Review history

**`_acceptance-demo-10`, contract revision 1 (2026-09-18, provisional):**
- **Round 1** (same-family) rejected `AC-DECOMPOSITION`: only one of the four example packets' commands ran through the gate. Fixed in `f47a43d`.
- **Round 2** (cross-family Codex) rejected `AC-PROVENANCE` and `AC-ADVERSE` on record binding and coverage. Fixed in `29422ca` (ADR-060).
- **Round 3** (cross-family Codex, the last of `max_review_attempts=3`) rejected on two points. `AC-ADVERSE` was still unmet: a `LEGAL_PROPOSITION` could validate with no primary-source rung. The scope finding was that the required closeout-record edits fell outside `scope.allowed`. The report could not be ingested because its scope `failed_ref` was a shorthand rather than a literal scope string (ADR-061).

**Session 3 (2026-09-27):**
- `main` was merged in (`a638098`).
- `AC-ADVERSE` was fixed in `cecd714`, and the dogfood contract was revised to revision 2, which admits the standing closeout records (ADR-065).
- Review moved to `_acceptance-demo-10b`, because the acceptance ledger has no revision event and `-10`'s budget was spent. This follows #9's `-9`/`-9b` precedent.

**`_acceptance-demo-10b`, contract revision 2:**
- The deterministic gate re-executed `VAL-SUITE`: 399 tests OK, 81 required paths, 0 payload drift.
- Round 1 (cross-family Codex, tier 3) returned `APPROVE`, finding every criterion met and both round-3 findings resolved. `accept` was recorded by the approving reviewer.

## Pull request #50 — Codex review rounds

- **Round 1 on `e93271d`:**
  - P1 (actionable, fixed): `PROFILE.md` promised independent model review for elevated fact statuses, but a low-risk `LEGAL_PROPOSITION` packet was accepted on the deterministic gate alone. A packet asserting `DISPUTED_FACT` or `LEGAL_PROPOSITION` now needs `model_review` in its effective gates (ADR-066).
  - P2 (fixed): `HANDOFF_CURRENT.md` still described the session-2 state.
- **Round 2 on `7bb558e`**, two P1s (both actionable, fixed, ADR-067):
  - A missing record on one check masked a re-verified contradiction on another.
  - A supporting record for an `UNKNOWN` assertion earned `VERIFIED_FACT`.

  Both are in the earned-status derivation dogfood round 2 had corrected, so under R-012 the precedence was stated as one rule before patching.
- **Round 3 on `8845668`:**
  - P1 (actionable, fixed, ADR-068): a record was bound to its claim only by text, so a record of an unrelated source could verify a legal proposition. Assertions now declare `verified_by`, and a legal proposition must list its own authority. Each record names its `source_id`: an undeclared source verifies nothing, and a record covers a claim only when its source is in that claim's `verified_by`.
  - P2 (fixed): stale current-state text, swept across all the control files.
  - This was the third finding on what a source record proves, so under R-012 the invariant was written as ADR-068 before the code.
- **Round 4 on `7ff2158`** (the one extra round the maintainer authorized): one P1, actionable. Coverage is keyed by assertion text, so two entries with identical text but different `verified_by` share one supporting record. It is deferred to [#53](https://github.com/henslewm/universal-ai-project-template/issues/53) at the maintainer's decision, and fixed there by ADR-069 (duplicate assertion text is refused).

**Merged 2026-09-27** at `620fc9a`, pinned to the reviewed head `7ff2158`, with CI passing. #10 closed with a completion comment.

## Offline validation — 2026-09-27

On Windows with system Python 3.12.8 and `jsonschema==4.26.0`: `unittest discover -s tests -p "test_*.py"` ran 406 tests OK, 45 of them family-law, after PR #50 round 3 (399 at `-10b`'s acceptance); `scripts/validate_project.py` checked 81 required paths; `scripts/sync_skills.py --check` found 0 differing files.

## Boundaries

The examples are fictional and synthetic. No real case, party, court, docket or legal authority is established anywhere in them. Reviewer, implementer and operator identities are recorded declarations the controller cannot authenticate.
