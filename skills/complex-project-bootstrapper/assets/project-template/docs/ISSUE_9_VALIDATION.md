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

## Correction — 2026-09-14, against the merged gate

`origin/main` (PR #22 merged at `494587cf`; #8 closed again) was merged into the branch with a merge commit (`4b2b579`), so the acceptance controller the repeat dogfood runs through is the corrected one. The branch's two risk rows became R-013 and R-014 because `main`'s R-012 is #8's patch/review-loop risk. Two #8 regressions from PR #22 that append a second validation without a rung were refused by the #9 domain rules, correctly, and now map it.

The corrections this record called for, each with a regression (ADR-026 to ADR-028):

- **`AC-SAMPLE`.** `test_adapter.py` imports only `synth_bridge.adapter` and `synth_bridge.transport` and speaks raw SYNTH-FRAME-1 bytes; the device-through-adapter case moved to `test_integration.py`, which the workflow packet owns; `SHB-06-workflow` now declares `SHB-01-codec` as a dependency and names `synth_bridge.codec` and `synth_bridge.fake_device` among its consumed interfaces. `test_example_packets_form_a_dag_with_component_scoped_context` parses every file each packet names with `ast` and refuses an import the declared scope does not admit or a consumed interface whose owner is not a declared dependency, with a negative control for both. The sample suite is 28 tests.
- **Attested versus record-verified.** `status` reports `evidence_basis` (`attestation` without `--evidence-dir`, `record` with it); the `VERIFIED_ON_HARDWARE` reason without a directory says the digests are attested, not record-verified. `evidence_path` is present on every entry. A CLI regression covers both forms.
- **Operator under `--evidence-dir`.** A record found by digest must also have been recorded by the attesting operator; the regression binds another operator's record with the attester's name copied into the `operator=` line and shows `status --evidence-dir` refusing it.
- **No `profile=None`.** `validate_contract(contract, profile)` requires a registered profile; `None` is refused; every caller in the scripts and tests names one.
- **Closed block.** `contract_domain` has `additionalProperties: false` (`synthetic` and `template_child_issue` declared) and the literal `VERIFIED_ON_HARDWARE` is refused in any string the block carries, as a whole word so the declared `UNVERIFIED_ON_HARDWARE` is not a claim. The example contract's undeclared `fixture_protocol` key was removed.

## Repeat dogfood — `_acceptance-demo-9b`, 2026-09-14, against the merged gate

Fresh ledger beside the repository; packet `ISSUE-9-ACCEPTANCE` revision 1, contract hash `9e50f9bb…`, `high` risk (gates deterministic, model review, cross-family), domain block `NOT_HARDWARE_FACING` under the closed schema; artifact the root-scope diff of `3fb5964` against `main` `f4f709f` (sha256 `237b6df0…`); implementer declared as `claude`.

- **Deterministic gate.** `run-checks` re-executed the declared command and recorded `VAL-SUITE` PASSED (336 tests, 81 paths, 0 drift, exit 0), workspace digest `9cdb482d…`, agreeing with the supplied claim.
- **Round 1 — same-family, minimal context, APPROVE.** Reviewer "Claude Fable 5.1 (fresh minimal-context subagent reviewer, round 1)", family `claude`, tier 3, given the rules, the 16,435-character packet and the diff. All five criteria `met`. The report was refused once on shape (`criteria[].evidence` must be an array; the rendered `review_contract` names fields but not their types — an observation on #8's renderer) and re-issued unchanged. `accept` by this reviewer was refused by the cross-family gate, as designed.
- **Round 2 — cross-family, REJECT_BOUNDED.** Reviewer "Codex (OpenAI, cross-family reviewer, round 2)", family `openai`, tier 3 (review id `3855e712…`), run by the maintainer through the Codex CLI on the same three inputs. Four criteria `met`; `AC-EXTENSIONS` `not_met`: `status --evidence-dir` treated any dictionary with a matching canonical digest as a verified record without validating it against `$defs/hardware_evidence`, and never compared the record's `device_identity`, `firmware_version` and `observed_at` with the attested lines, so a five-field stub bound by digest, with those lines typed by hand, earned record-basis `VERIFIED_ON_HARDWARE`. A static code-path finding the same-family round did not make. Corrective action inside scope: validate the found record with the existing `validate_hardware_evidence` and compare every attested line, with regressions.
- **Correction (ADR-029).** `record_problems` in `scripts/software_hardware.py` owns verification of a found record: schema validity, task, validation, rung, `pass`, attesting operator, and agreement of each attested line with the record's field, each disagreement named in the reason with `evidence_path` still set. Regressions: the five-field stub, a mismatch in each of device, firmware and observed time, the other-operator record, and the consistent record still verifying on the `record` basis. The suite is 337 tests.

## What must happen before this record becomes evidence

1. ~~PR #22 (reopened #8) merges~~ — merged 2026-09-15 at `494587cf` and merged into this branch.
2. ~~The `AC-SAMPLE` correction and the residual observations are applied~~ — applied 2026-09-14, see Correction above.
3. The dogfood is repeated from a fresh ledger against the corrected gate: `init`, `run-checks`, a fresh minimal-context review, the cross-family approving review, `accept` — in progress at `_acceptance-demo-9b`; after the round-2 correction the resubmission needs the cross-family approving review (the third and last review slot).
4. Only then are this document's provisional markers removed and #9's acceptance criteria mapped to evidence.

## Discovery outside this issue

Codex's four findings on PR #21 (two P1, two P2) were handled by reopening #8, per the maintainer's decision, not by a follow-up issue. The standing rules that resulted are in `MASTER_INSTRUCTIONS.md`.
