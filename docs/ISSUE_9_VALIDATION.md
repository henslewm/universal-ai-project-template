# Issue #9 validation and review — PROVISIONAL

Issue: [Complete software + hardware domain template and hardware-in-loop discipline](https://github.com/henslewm/universal-ai-project-template/issues/9). Design approved by the maintainer as proposed on 2026-09-13 and recorded in the issue. Implementation is on `issue-9-software-hardware-domain` at `27ebdf3` (records drafted at `d0fdc05`). Locked master #14 title/body and order remain unchanged.

## Status of this record

**Nothing in this document is acceptance evidence yet.** The dogfood acceptance run described below was made through the acceptance controller as merged at `226353c6` (#8), in which two P1 defects found by Codex on PR #21 were unfixed at the time: an acceptance decision was not bound to its feedback task, and the reviewer tier was not enforced at `REVIEW_OPEN`. #8 was reopened on 2026-09-13 to fix them (PR #22). Until that PR is merged and the #9 run is repeated against the corrected gate, the run below establishes only that the deterministic gate observed the suite pass and that a minimal-context reviewer found a real defect. It does not establish that #9's acceptance would be sound, and #9 is not advanced until #8 is correct.

## Delivered on the branch

- `config/domains/software-hardware.schema.json` and `scripts/software_hardware.py`: the software-hardware `domain` block is structural — one named component, hardware assumptions each citing a contract source, protocol references, every validation mapped to one rung of the ladder, and a declared status limited to `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING`. Machine rungs must declare a command; hardware rungs must not. `VERIFIED_ON_HARDWARE` is refused in a contract and derived from the ledger by `status`.
- Hooks: `work_packet.DOMAIN_MODULES` applied inside `validate_contract` on packet validation, feedback contract repair and acceptance init; the acceptance ATTESTATION event delegates to the profile rule, which requires a hardware-rung attestation to bind a validated hardware evidence record by digest with a `pass` outcome recorded by the attesting operator.
- Bootstrap: nine required orientation fields for the profile; `config/bootstrap.example.json` updated; placeholder answers refused before review.
- Documents: `templates/software-hardware/PROFILE.md` and `DOMAIN_PROFILE.md` rewritten and identical; cross-references in `WORK_PACKET_PROTOCOL.md`, `ACCEPTANCE_PROTOCOL.md`, `BOOTSTRAP_PROTOCOL.md`, `prompts/INTERACTIVE_BOOTSTRAP.md`.
- Example: `examples/software-hardware/` — a fictional synthetic sensor bridge with 27 runnable tests, six component-scoped packets, a hardware evidence example and an operator procedure.
- Tests: `tests/test_software_hardware.py`, 25 tests; 309 total; 81 required paths; 0 payload drift. Decisions ADR-018 to ADR-020.

## Offline validation — 2026-09-13 UTC

309 tests pass on Windows with the maintainer's working interpreter. Repository validation passes 81 required paths; `scripts/sync_skills.py --check` reports 0 differing files. The 25 domain tests cover every contract refusal, hook propagation to packet validation and acceptance init, the attestation rule with and without a bound record, status derivation including the machine-only never-upgrades case, the six example packets validating and forming a DAG, the sample commands executing through `run-checks`, and the bootstrap field set. CI on Linux has not yet run for this branch because no pull request has been opened; that is deliberate while #8 is open.

## Dogfood — provisional

Ledger `_acceptance-demo-9` beside the repository, packet `ISSUE-9-ACCEPTANCE` at `high` risk (gates: deterministic, model review, cross-family), `domain` block declared `NOT_HARDWARE_FACING` under the rules the diff introduces.

- **Deterministic gate.** `run-checks` executed the declared command (full suite, repository validation, payload sync) and recorded `VAL-SUITE` PASSED with workspace digest `8764bcd9…`. The observation agreed with the implementer's supplied claim.
- **Round 1 model review — REJECT_BOUNDED.** A fresh same-family (claude) subagent reviewed from the 15,638-character packet, the rules and the diff only. Four criteria met; `AC-SAMPLE` not met: the adapter packet declares only the transport interface and dependency yet its own tests import the codec and drive `SensorDevice` through the adapter, the workflow packet's declared interfaces omit the codec and fake device its integration test imports, and the scoping test checks path shape rather than comparing imports to declared interfaces. Corrective action, inside scope: make the declared scopes true (have the adapter tests consume only transport-level byte vectors and move the device-through-adapter case to the workflow packet, or declare the missing dependencies) and strengthen the test to parse imports against declared interfaces. The report was refused once for exceeding the summary bound and re-issued by the same reviewer; it is recorded and the ledger is `REJECTED`.
- **Residual observations from the reviewer, not contract failures, to be addressed with the correction:** `status` without `--evidence-dir` reports `VERIFIED_ON_HARDWARE` on attested digests alone and should say it is attested, not record-verified, status; `status --evidence-dir` does not compare the record's operator to the attestation; `validate_contract` keeps a `profile=None` default that skips domain rules for any caller not passing the profile; `additionalProperties: true` lets the literal `VERIFIED_ON_HARDWARE` appear in free-text domain fields.
- **Cross-family gate.** Unsatisfied. The round-1 reviewer is same-family and says so. The maintainer intends to provide the approving review from a different strong model family after the correction, rather than record a waiver.

## What must happen before this record becomes evidence

1. PR #22 (reopened #8) merges after its Codex review of the current head is answered, on the maintainer's go-ahead.
2. The `AC-SAMPLE` correction and the residual observations are applied on the #9 branch with regressions.
3. The dogfood is repeated from a fresh ledger against the corrected gate: `init`, `run-checks`, a fresh minimal-context review, the cross-family approving review, `accept`.
4. Only then are this document's provisional markers removed and #9's acceptance criteria mapped to evidence.

## Discovery outside this issue

Codex's four findings on PR #21 (two P1, two P2) were handled by reopening #8, per the maintainer's decision, not by a follow-up issue. The standing rules that resulted are in `MASTER_INSTRUCTIONS.md`.
