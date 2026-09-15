# Project State

- **Status:** TEMPLATE MAINTENANCE — #9 closed 2026-09-15 through merged PR #34; #10 not yet started
- **Last verified:** 2026-09-15 UTC
- **Active branch:** main, at `d873ec5cd1be503a19880eacbaf9cfba764d9fa5`
- **Controlling scope:** [Locked master #14](https://github.com/henslewm/universal-ai-project-template/issues/14); title/body/order unchanged.
- **Active child:** [Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10) — complete high-conflict NC family-law evidence/research template. Not yet started; begin with the interactive-bootstrap-then-decompose pattern used for #9.

## Verified foundation

Issues #2 through #9 are closed through merged PRs #15 to #34. #9 (complete software + hardware domain template and hardware-in-loop discipline) was accepted through its dogfood at `_acceptance-demo-9b` on 2026-09-14 (11 events, cross-family approval, no waiver, after ADR-026 to ADR-029), then its PR #34 went through 23 rounds of Codex review before a clean result and merge on 2026-09-15 at `d873ec5cd1be503a19880eacbaf9cfba764d9fa5`. Decisions ADR-041 through ADR-055 record every round; `docs/ISSUE_9_VALIDATION.md` holds the full mapping.

#9 delivered the software-hardware domain module (`scripts/software_hardware.py`, `config/domains/software-hardware.schema.json`) that structurally distinguishes a simulated pass (`command`, re-executed by the deterministic gate) from hardware-in-loop or field verification (an operator attestation binding a structured evidence record by digest, never a contract-declared claim). The 23-round review closed a class of gap in the generic acceptance controller that later domain modules should expect too: binding an operator's evidence to exactly the submission it was observed against is several independent checks, not one — the contract's revision and hash, the submitted result's dispatch identity, the artifact's actual identity (not merely a hash a reference-kind artifact can leave at a fixed empty-content value), and the observation's own timestamp bounded on both sides by the current submission and the attestation event. `acceptable()` also now distinguishes replaying an already-accepted ledger's history from justifying a brand-new acceptance today, so a stored decision that rested on since-invalidated evidence keeps replaying as history without letting a *new* decision rest on the same thing.

This is an unactivated reusable template under explicit maintenance authority. No real project registry, provider calls, credentials or permission changes are required. Generated projects should link their generated structured project-state index here and audit it against GitHub; task narration belongs in canonical issue comments.

## Continuation

#9 is closed; its completion comment (and `HANDOFF_CURRENT.md`) name the limitations carried forward (OL-016's template-packaging defects remain open from #8's closure, unaddressed by #9). Begin #10 from master #14 and #10 only, in a fresh session. #10 is a different domain (evidence-first legal research, not software/hardware), but the acceptance-controller lessons above are domain-independent and apply to whatever evidence-binding rules #10 adds. Model-performance calibration remains #12 and should receive #7's run-4 profile, #8's review-economics observations, and #9's 23-round review-economics figures once gathered. Continue one child at a time. Do not edit the locked master or delete construction branches outside the later authorized cleanup.
