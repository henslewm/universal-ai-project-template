# Project State

- **Status:** TEMPLATE MAINTENANCE — #8 accepted and closed; #9 not yet started
- **Last verified:** 2026-09-13 UTC
- **Active branch:** main
- **Controlling scope:** [Locked master #14](https://github.com/henslewm/universal-ai-project-template/issues/14); title/body/order unchanged.
- **Next unblocked child:** [Issue #9](https://github.com/henslewm/universal-ai-project-template/issues/9) — complete software + hardware domain template. Not started.

## Verified foundation

Issues #2 through #8 are closed through merged PRs #15/#16/#17/#18/#19/#20/#21. The latest accepted state is merge `226353c6279fc36f11d4aa3b36801c82ea88f9ac` on `main`, which closed #8 and is confirmed to contain branch head `1df51617`. CI `validate` was green on both checks before the merge, and the maintainer explicitly authorized the merge after the session surfaced that the only reviews were agent-run.

#8 delivered the independent acceptance controller in the reserved gap between the feedback controller's `REVIEW_PENDING` and the packet's `REVIEW → ACCEPTED` transition. `ACCEPTANCE_PROTOCOL.md` is the contract; `scripts/acceptance.py` keeps one append-only hash-chained ledger per reviewed task, independently re-executes the contract's declared validation commands (the one deliberate exception to the metadata-only pattern, ADR-014), renders bounded minimal-context review packets from ledger records only, enforces the five reviewer verdicts with structural refusals, holds a hard cross-family gate with recorded waiver at high and critical risk, and grants acceptance only when every gate required by the risk floor has a current-submission passing record. Gate floors are assigned in the work packet and can only be tightened; contract repair can no longer change risk or the review block. Decisions are ADR-014 through ADR-017, and `docs/ISSUE_8_VALIDATION.md` holds the acceptance mapping, the two-round dogfood in which #8's own diff was rejected by a minimal-context reviewer for a real gate-bypass defect and accepted only after the regression-tested correction, and the environmental record. The 11-event dogfood ledger is preserved at `_acceptance-demo` beside the repository.

This is an unactivated reusable template under explicit maintenance authority. No real project registry, provider calls, credentials or permission changes are required. Generated projects should link their generated structured project-state index here and audit it against GitHub; task narration belongs in canonical issue comments.

## Continuation

Begin #9 from master #14 and #9 only, in a fresh session. Domain-specific rigor is #9's subject — the software/hardware template must distinguish simulated success from actual hardware-in-loop verification, which is exactly the distinction the acceptance controller's machine-runnable-versus-attested validation split now supports. Model-performance calibration remains #12 and should receive both #7's run-4 profile and #8's review-economics observations. The stray `prompts/PROVISION_LOCAL_MODEL.md` in the working tree is the maintainer's local-model-provisioning draft awaiting his deliberate commit (it looks like #12 input). Continue one child at a time. Do not edit the locked master or delete construction branches outside the later authorized cleanup.
