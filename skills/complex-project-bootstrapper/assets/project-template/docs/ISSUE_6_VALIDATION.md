# Issue #6 validation and review

Issue: [GitHub durable autonomous execution ledger](https://github.com/henslewm/universal-ai-project-template/issues/6). #5 was closed through merged PR #18 before this child began. Locked master #14 title/body and order remain unchanged.

## Acceptance mapping

- One canonical task home: a registry binds validated packet identity to an existing GitHub issue; duplicate homes, master-as-task, reused branches/PRs and rebinding are rejected. Task and feedback history may only extend their prior prefixes.
- Reconstructable handoff: a pinned GitHub commit contains the complete packet and feedback events. Recovery validates and replays them into a new directory, preserving holds, pending reservations and cumulative evidence without granting execution authority.
- Closed-task evidence: closure requires a VERIFIED packet, committed verification/review references, accepted commit ancestry, matching merged PR where used, a verified completion comment, and separate homes for unrelated discoveries.
- Consistent project state: live audit checks issue/PR/receipt/accepted-commit consistency; an optional generated structured project-state index must match the exact current state snapshot. Optional packet/workspace checks identify local unpublished work.
- Drift detection: stale writers, overwritten history, missing/untrusted/edited/duplicate comments, uncertain publication, missing discovery issues, wrong checkout identity and stale status fail checks. Arbitrary prose and unseen local work are explicitly outside the validator's claims.

The six requested issue forms and linked PR conventions are delivered. They are intake/review views and do not replace canonical packet or domain validation.

## Validation — 2026-09-12 UTC

The generated-project integration suite passed all 15 tests in 67.647 seconds. It covers the nine combinations of three domain profiles and root/native/standalone distribution entrypoints; each now validates a full synthetic GitHub registry containing its completed feedback history through the delivered CLI. No network write or real-project activation is claimed by those fixtures.

All six YAML forms passed duplicate-key parsing and structural checks derived from GitHub's official form syntax. PR-template content checks and repository validation passed. PyYAML was isolated in a temporary validation environment and was not added as a runtime dependency.

A read-only smoke check through the actual GitHub adapter successfully fetched Issue #6, its comments, merged PR #18, accepted-commit ancestry and pinned Contents API data. This confirms current authenticated read compatibility, not a live mutation or production recovery test.

The full pre-connector-test suite passed all 157 tests in 121.100 seconds. Repository validation passed 57 required paths; generated payload consistency and whitespace checks passed. All 42 focused connector tests passed in 24.696 seconds. They exercise file-SHA conflicts, claimed publication ordering, lost commit/POST responses, complete pagination, receipt tampering, closure and live metadata, real synthetic approval gates, history preservation, portable recovery, local/structured-state drift and discovery issue homes. The initial PR head passed all 199 tests in GitHub Linux CI (105.019s), with both checks green. The GitHub review corrections below add four tests; the final suite contains 203. Current-head CI results remain in the PR/issue. GitHub acceptance remains in the child issue and PR.

## Independent review

A separate read-only reviewer examined the connector, configuration, issue forms and protocol. Corrected findings include Windows recovery name collisions, trailing-newline identifier acceptance, insufficient workspace repository identity checks, and publisher identity being checked after a comment write. Recovery directories now use task-identity digests, identifiers are matched strictly, workspace checks bind origin and published commit, and publication checks the authenticated account before claiming or posting. Independent targeted probes confirmed the recovery/identifier and publisher fixes. A final no-orphan check also requires every discovery to have its own issue before acceptance freezes the row. Final independent suite review is recorded when complete.

## Explicit boundaries

The connector is executable GitHub metadata tooling using the existing GitHub CLI authentication. It does not invoke models, create issues, merge PRs or substantively verify supplied evidence. Local examples remain disabled; all mutation tests use isolated deterministic fixtures. No real project registry, paid provider call, credential, permission or branch cleanup was needed.

The bounded registry holds at most 900,000 UTF-8 bytes and never truncates raw evidence. An unresolved claimed POST is not automatically retried; partial initialization or permanently uncertain publication requires evidence-based operational repair. Fixed approval anchors require an explicit continuity decision after material architecture changes. GitHub administrators can rewrite history; this is not a hostile-actor security boundary. See `GITHUB_LEDGER_PROTOCOL.md` for the supported recovery path and #7/#8 responsibilities.

After committed/pushed verification, independent review and PR acceptance, close #6 with evidence, then reread master #14 before #7. Continue through #13 strictly one child at a time.

## GitHub review corrections

The initial automatic review found three issues: registry validation omitted the complete cross-task dependency graph, implementation branch names could be invalid Git refs, and discovery mappings could reuse the master or another canonical task issue. Corrections validate the complete registered DAG on every read/write, use a restricted valid Git branch-name subset (including component rules), and keep every discovery target outside the master/canonical-home set in either registration order.

All 46 final ledger tests passed in 29.224 seconds. Added regressions cover missing/unverified/regressed prerequisites and cycles, invalid branch components before mutation, master/other-task discovery targets, and later task registration that would reuse a discovery home. Accepted branch examples were also checked with the actual Git ref validator. The [Git reference naming manual](https://git-scm.com/docs/git-check-ref-format) supplies the naming rules. Independent current-head review and final GitHub CI are required before acceptance.

### Second review round

The review of `b801103210400599d71d1e93a9d468ec4e9f2562` reported one remaining P2 finding: two distinct discovery digests could map to the same noncanonical issue, so separate follow-up records could be conflated and then frozen by acceptance. Registry validation now also requires every discovery home to be unique across the whole registry, in a single row and across tasks, in addition to the existing master/canonical exclusion. `GITHUB_LEDGER_PROTOCOL.md` states the rule.

A regression covers same-row duplicate mapping, refusal before any GitHub mutation, distinct homes accepted, a second task reusing another task's discovery home, and that task succeeding on its own home. All 47 ledger tests passed (19.980s Linux, 25.709s Windows) and the full suite passed all 204 tests (76.124s Linux, 155.719s Windows); repository validation passed 57 required paths and the bootstrap distribution check reported 0 differing files. Current-head GitHub CI and review results remain in PR #19 and issue #6.
