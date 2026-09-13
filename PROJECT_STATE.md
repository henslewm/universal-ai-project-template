# Project State

- **Status:** TEMPLATE MAINTENANCE — #7 accepted and closed; #8 not yet started
- **Last verified:** 2026-09-13 UTC
- **Active branch:** main
- **Controlling scope:** [Locked master #14](https://github.com/henslewm/universal-ai-project-template/issues/14); title/body/order unchanged.
- **Next unblocked child:** [Issue #8](https://github.com/henslewm/universal-ai-project-template/issues/8) — independent review, acceptance gates and minimal-context review packets. Not started.

## Verified foundation

Issues #2 through #7 are closed through merged PRs #15/#16/#17/#18/#19/#20. The latest accepted state is merge `b326dca1674ae858eacb83cda7cf67c96c2d0e12` on `main`, which closed #7 and is confirmed to contain branch head `bd26e4c64de0d06ed02d06ebfba2575da0e8a06c`. CI `validate` was green before merge. Exact completion records and the limitations carried forward are in the child and master comments.

#7 delivered a bounded, replaceable worker harness occupying one gap only: between the reservation the feedback controller grants and the result it records. `EXECUTION_HARNESS_PROTOCOL.md` is the contract. `scripts/execution_harness.py` prepares and ingests; it never invokes a model and never runs the harness command. Its live criterion was met by an operator run that was then rechecked independently against the filesystem rather than accepted from the worker's report. Decisions are ADR-010 through ADR-013, and `docs/ISSUE_7_VALIDATION.md` holds the acceptance mapping, all four operator runs and the review round.

This is an unactivated reusable template under explicit maintenance authority. No real project registry, provider calls, credentials or permission changes are required. Generated projects should link their generated structured project-state index here and audit it against GitHub; task narration belongs in canonical issue comments.

## Continuation

Begin #8 from master #14 and #8 only, in a fresh session. Independent acceptance machinery is #8's subject, and #7's own review was same-family by the implementer, so #8 is where that weakness is meant to be addressed structurally rather than by promising to try harder. Model-performance calibration remains #12 and should receive #7's run-4 profile. Detailed domain work remains #9/#10/#11; the automatic first task-graph demonstration and final integration remain #13. Continue one child at a time. Do not edit the locked master or delete construction branches outside the later authorized cleanup.
