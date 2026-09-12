# Issue #4 validation and review

Issue: [capability-tier router and economic governor](https://github.com/henslewm/universal-ai-project-template/issues/4). Scope remains locked master #14's child issue #4; the master title/body is unchanged. #3 was closed through merged PR #16 before #4 began.

## Delivered behavior

The canonical packet supplies allowed tiers, effort, risk, complexity and worker retry budget. `scripts/model_router.py` validates provider-independent configuration and a revision/role-bound request, selects by estimated total cost per accepted result, supports finite provider fallback and authorized escalation, and saves a replayable local decision with its original inputs. Reviewer tier and role budgets are separate. Schema and disabled fictional examples cover all intended provider families without provider names in work contracts.

## Reproducible checks — 2026-09-12 UTC

Python 3.12.8 in an isolated temporary environment with `requirements-work-packets.txt` installed:

```text
python -m unittest discover -s tests -p 'test_model_router.py'
39 tests, 5.440s — OK

python -m unittest discover -s tests -p 'test_bootstrap_integration.py'
15 tests, 41.738s — OK

python -m unittest discover -s tests -p 'test_*.py'
110 tests, 57.340s — OK

python scripts/validate_project.py
VALIDATION PASSED — 42 required paths

python scripts/sync_skills.py --check
Bootstrap payloads verified — 0 files differed

git diff --check
Passed
```

Router tests cover zero-API versus total accepted-result costs, risk/complexity and exact effort, authorized/empty paths, independent reviewer tiers and budgets, monotonic escalation, same-tier outage fallback, spent/estimated API caps, terminal states, invalid/bound histories, configuration swaps, supplied observation blending, numerical extremes, deterministic ties, replay tampering and exclusive output creation. Integration tests create and replay positive offline decisions in all nine combinations of three domain profiles and root/native/standalone bootstrap entrypoints.

## Independent review

A separate read-only reviewer inspected the runtime, schema, disabled examples, protocol and tests. The review identified a supported numeric-extreme case that raised `decimal.InvalidOperation` during output rounding. Decimal precision was increased to accommodate schema-bounded costs and smoothed probabilities, CLI failure handling was retained, and an extreme-value regression was added. The reviewer independently reran all 39 router tests (5.616s, OK) and the original saved-record replay reproduction, then reported no remaining blockers.

The bounded test author also caught an early CLI serialization error before acceptance. The final CLI tests verify successful record creation/replay and preservation of existing inputs/output on refusal.

## Boundaries and acceptance record

All model examples and tests are synthetic; no provider credentials, live model calls, paid usage, permission changes or real project activation were needed. Offline selection and supplied-history replay do not authenticate outcomes, establish complete usage, enforce actual billing or bypass bootstrap/dependency/review gates. See `MODEL_ROUTING.md` for exact policy, formulas, exit codes and later executor/ledger/telemetry integration boundaries.

Actual commit, push, GitHub checks/review, PR merge and issue closure are recorded in Issue #4 and its linked PR. This document records local validation, not a claim that unpublished or unmerged work is accepted. After live acceptance and closure, return to locked master #14 before selecting #5; continue through #13 one child at a time.
