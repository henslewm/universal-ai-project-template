# Project State

- **Status:** TEMPLATE MAINTENANCE — Issue #7 validated; review, merge and closure pending
- **Last verified:** 2026-09-13 UTC
- **Active branch:** issue-7-cline-harness
- **Controlling scope:** [Locked master #14](https://github.com/henslewm/universal-ai-project-template/issues/14); title/body/order unchanged.
- **Sole active child:** [Issue #7](https://github.com/henslewm/universal-ai-project-template/issues/7), with [PR #20](https://github.com/henslewm/universal-ai-project-template/pull/20) open.

## Verified foundation and current work

Issues #2 through #6 are closed through merged PRs #15/#16/#17/#18/#19. The latest accepted foundation is PR #19 at `5e0a28c62ff9fdaa9c9764713742e97f12061040`, which closed #6 after five automatic review rounds and one independent review. Exact completion records are in child/master comments.

#7 delivers a bounded, replaceable worker harness occupying one gap only: between the reservation the feedback controller grants and the result it records. `EXECUTION_HARNESS_PROTOCOL.md` is the contract. `scripts/execution_harness.py` prepares and ingests; it never invokes a model and never runs the harness command. Routing, attempt budgets and scope rules stay outside it, so Cline never becomes the architect. Decisions are ADR-010, ADR-011 and ADR-012.

All five acceptance criteria are now met, including the live one: an operator run on 2026-09-13 executed a bounded packet through Cline on a local LM Studio model and produced a report the validator accepts, whose central claim was then verified independently against the filesystem. It took four runs; the three that failed each produced a correction, and `docs/ISSUE_7_VALIDATION.md` records all four with the acceptance mapping and the limitations carried forward. Validation/review/PR status belongs in live #7; these local documents do not establish merge acceptance.

This is an unactivated reusable template under explicit maintenance authority. No real project registry, provider calls, credentials or permission changes are required. Generated projects should link their generated structured project-state index here and audit it against GitHub; task narration belongs in canonical issue comments.

## Continuation

Complete the review of PR #20, answer findings in place, merge, and close #7 with evidence before rereading master #14 and starting #8. Continue through #13 strictly one child at a time under the user's standing instruction. Independent acceptance machinery remains #8 and model-performance calibration remains #12; detailed domain and canonical legal-branch work remain #9/#10/#11; the automatic first task-graph demonstration and final integration remain #13. Do not edit the locked master or delete construction branches outside the later authorized cleanup.
