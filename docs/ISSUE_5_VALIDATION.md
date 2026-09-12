# Issue #5 validation and review

Issue: [bounded feedback, escalation and anti-loop controls](https://github.com/henslewm/universal-ai-project-template/issues/5). #4 was closed through merged PR #17 before this child began. Locked master #14 title/body and ordered scope remain unchanged.

## Delivered behavior

- Exclusive, synchronized dispatch reservations precede worker intent; immutable event replay recovers state and refuses gaps, corruption, duplicate resolution and concurrent/pending duplicate dispatch.
- Frozen task/tier limits, repeated-failure detection and finite repair/recovery/diagnosis limits retain cumulative usage and evidence across contract revisions and provider replacement/recovery.
- Complete reported objective checks are necessary to reach independent review; contradictory PASS, scope violations, architecture conflicts and expired deadlines cannot pass.
- Focused context preserves the current contract and bounded failure/architect evidence. Comment previews reference immutable originals; unrelated discoveries remain separate issue proposals.
- Architect repairs require unchanged current approval, preserved protected fields and remaining budgets. Confirmed architecture changes and changed/unavailable approval create sticky human-decision holds. Terminal stop recording remains possible after the nonterminal diagnosis allowance is exhausted.

## Local validation — 2026-09-12 UTC

Python 3.12.8 with `requirements-work-packets.txt` in an isolated temporary environment:

```text
python -m unittest discover -s tests -p 'test_feedback.py'
38 tests — passed (test author: 13.764s; independent reviewer: 13.866s)

python -m unittest discover -s tests -p 'test_*.py'
148 tests, 87.051s — OK

python -m unittest discover -s tests -p 'test_work_packet.py'
40 tests, 7.152s — OK

python scripts/validate_project.py
VALIDATION PASSED — 46 required paths

python scripts/sync_skills.py --check
Bootstrap payloads verified — 0 files differed

git diff --check
Passed
```

The full local run began before the additional per-tier contract-boundary test was added. The final 40-test packet suite includes that test. The initial PR head then passed all 149 tests in GitHub's Linux run (69.242s). The directory-durability correction below adds eight more tests, bringing the current suite to 157. Final full-suite GitHub results are linked from the PR/issue rather than inferred from earlier counts.

The generated-project integration test exercises all nine combinations of three domain profiles and root/native/standalone entrypoints. Each creates a synthetic approved project, packet and router decision, initializes its delivered feedback controller, reserves a synthetic intent, records supplied passing validation, replays `REVIEW_PENDING` and renders its evidence. No real model or validator execution is claimed by these fixtures.

Focused tests cover per-tier/total limits, repeated failure versus meaningful diagnostic differences, schema-valid integral-float tiers, concurrency/CAS, crash/pending state, corrupted/partial ledgers, exact result binding, scope and architecture dominance, actual temporary approval/document/profile checks, repair invariants/cumulative API usage, bounded blocker/provider recovery, finite diagnosis deferrals, deadline boundaries and safe bounded comment output. The final contract test rejects unauthorized/empty/malformed/excessive per-tier caps while accepting valid overrides.

## Independent review

A separate read-only reviewer examined runtime, schemas, protocol and tests, ran concurrency/replay/recovery probes, and independently passed all 38 final feedback tests. Findings were corrected before acceptance:

1. Integral-valued float tiers used inconsistent repeated-failure counter keys; normalize tier keys before grouping and lookup.
2. A blocked diagnosis could downgrade a stronger architecture/scope hold; deferral now preserves the original hold class.
3. Exhausting nonterminal diagnoses prevented a confirmed architecture-change stop; terminal stop recording remains available and immediately creates an unreleasable ordinary-work hold.

The reviewer reported no remaining blockers after the final targeted reproduction, replay/hold checks and suite rerun. Documentation was clarified to distinguish post-revocation result recording from timeout failure and saved dependency snapshots from live freshness.

## GitHub durability finding and correction

PR #18's automatic review identified a POSIX persistence gap: file synchronization alone does not guarantee the new directory entry. `append` now closes the synchronized event file and synchronizes the containing directory before returning an intent. Initialization requires an existing parent and synchronizes that parent after creating the ledger directory. Failures return no intent; existing records remain for reconciliation. The [Linux fsync manual](https://man7.org/linux/man-pages/man2/fsync.2.html) supports the directory-synchronization requirement.

Eight added portable regressions cover ordering, no returned intent on failed directory synchronization, retained pending reservations, parent/ledger initialization order, missing-parent refusal, POSIX descriptor cleanup and the non-POSIX path. All 46 final feedback tests passed for the author (13.965s) and independent reviewer (13.917s). Independent fault injection also verified failure recovery and prevention of duplicate dispatch. No runtime blockers remained. Windows file synchronization remains; namespace persistence across power loss is unverified and explicitly documented. These tests verify the implementation/protocol and failure handling, not physical power-loss behavior.

## Boundaries and actual acceptance

This is local feedback orchestration with supplied evidence. No live model calls, paid usage, credentials, permission changes or real-project activation were used. #6 must publish/reconstruct authoritative GitHub state; #7 must enforce live dependency/permission checks, actual validators, deadlines/cancellation and usage accounting; #8 must enforce independent acceptance. Local identity/fingerprint/counter checks are not authentication, semantic architecture proof, a hostile-code sandbox or a global billing boundary. Preserve one managed ledger and its original evidence. See `FEEDBACK_PROTOCOL.md`.

Commit/push, GitHub checks/review, PR merge and child closure are verified in #5 and its linked PR. This local document is not a merge record. After acceptance/closure, return to master #14 before #6 and continue through #13 strictly one child at a time.
