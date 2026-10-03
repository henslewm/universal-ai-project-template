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

A regression covers same-row duplicate mapping, refusal before any GitHub mutation, distinct homes accepted, a second task reusing another task's discovery home, and that task succeeding on its own home. All 47 ledger tests passed (19.980s Linux, 25.709s Windows) and the full suite passed all 204 tests (76.124s Linux, 155.719s Windows); repository validation passed 57 required paths and the bootstrap distribution check reported 0 differing files. Both GitHub checks passed on that head.

### Third review round

The review of `11765765d8dccde11ec7e0bcdfb6148ce019cb57` reported one P2 finding: the ledger's write gate called `feedback.active_anchor` without an expected profile, so a packet from another domain profile could be registered under an unrelated project's approval and then frozen by immutable packet identity. `authority` now takes the expected profile and passes it to `active_anchor`; registration supplies the packet's own profile, and publication and closure supply the registry's profile. Registry validation additionally requires every registered packet to share one domain profile, so a mixed registry is rejected on every read and write. `GITHUB_LEDGER_PROTOCOL.md` states the rule.

Regressions cover a mismatched packet refused before any GitHub mutation, the matching packet registering and publishing normally, and a mixed-profile registry failing validation. All 49 ledger tests passed in 19.399 seconds and the full suite passed all 206 tests in 75.059 seconds; repository validation passed 57 required paths and the bootstrap distribution check reported 0 differing files. Current-head GitHub CI and review results remain in PR #19 and issue #6.

### Fourth review round

The review of `346fc860541d1ae356b95835d63f2a753f4dcf72` reported one P2 finding: branch names were validated only in isolation and for equality, so an accepted branch `main` and a task branch `main/task` both passed while Git cannot hold `refs/heads/main` and `refs/heads/main/task` at the same time. Because a non-null branch binding is immutable, such a task would be permanently stranded, and the same collision can block initialization when the configured state and accepted branches have that prefix relationship. A shared `ref_conflict` check now rejects any configured or registered branch that is a path-component prefix of another, on every read and write. `GITHUB_LEDGER_PROTOCOL.md` states the rule.

Regressions cover a task branch nested under the accepted branch, under the state branch and under another task's branch; a later shallow branch that would contain an existing nested one; both configured-branch prefix directions; and refusal before any GitHub mutation. The test also confirms the underlying constraint with the real `git update-ref`, which reports `'refs/heads/main' exists; cannot create 'refs/heads/main/task'`. All 50 ledger tests passed in 19.842 seconds and the full suite passed all 207 tests in 75.179 seconds; repository validation passed 57 required paths and the bootstrap distribution check reported 0 differing files. Current-head GitHub CI and review results remain in PR #19 and issue #6.

## Independent review remediation

Codex returned no review on `a74a980` within the usual window, so the independent pass was run by a separate reviewer with no implementation context. **Limitation: that reviewer is the same model family as the implementer, not a different strong model as master #14 prefers, and it had no live GitHub access — every remote-semantics question rests on documentation and the synthetic fake.** A Codex pass is still wanted. The full findings are recorded in issue #6. Six were accepted and corrected here; none were dismissed.

### P1 — a PR closed without merging no longer strands the task

`live_row` required the bound PR to be open while `validate` refused to rebind or clear it, so an ordinary rejected-review outcome froze the row, its issue and its audit result with no remedy. A PR binding is now replaced through supersession: the outgoing number is appended to the new `superseded_prs` list in the same write that changes or clears `pr`, one per change, never on an accepted row, and `live_row` requires every superseded number to be a live PR that is closed and was not merged. A merged PR therefore cannot be hidden by superseding it, the list can only grow, and no other task may adopt a superseded number. Regressions walk the whole path: open PR published and audited clean, PR closed unmerged making audit fail, a rebind refused without the record, the recorded supersession accepted and audited clean, a merged supersession failing audit, an attempt to erase the record refused, clearing the binding after the replacement also closes, and a second task refused the superseded number.

### P1 — a stranded publication claim can be released on positive evidence

If the Contents write that records the exclusive claim landed but its response was lost, the comment provably never posted, yet no state transition could express the repair. A new `release` operation retires such a claim only after reading every comment page and finding no matching comment. The retired claim is appended permanently to the entry's `released` list, cannot be reused or removed, and the entry returns to unpublished so exactly one later publication completes it. A claim whose comment is visible is never releasable, and `release` requires the same approval, bound configuration and allowed publisher identity as publication. The regression injects the lost claim write, confirms no comment was posted, confirms neither publish nor reconcile retries the uncertain POST, releases, republishes, and asserts exactly one comment exists and that release history cannot be dropped.

### P2 — a publication must project the row that was committed

`validate` bound an outbox entry only to its own digest, so a writer could append a projection claiming `VERIFIED` with a fabricated acceptance commit, publish it as the canonical issue comment, and still pass audit — including onto a closed task. The newest entry for a task must now equal that task's current projection, and any entry appended in a write must be the projection of the row that write commits. The regression confirms the forgery is refused with and without prior state, that no mutation occurs, and that a superseded-but-genuine projection cannot be replayed after the current one.

### P2 — nested branch names address path-shaped refs

Every ref and compare endpoint used `quote(branch, safe="")`, percent-encoding the separator that makes a nested branch name a ref path, so `team/task` addressed a ref that cannot exist. The tests could not catch it because the synthetic fake called `unquote()` on ref paths and defaulted compare to `ahead`. The fake now refuses an encoded separator the way GitHub would, and a regression initializes a project whose state and accepted branches are both nested, registers nested implementation branches, and asserts the recorded endpoints carry literal separators.

### P3 corrections

Only the identity-bearing configuration — schema version, repository, state branch, accepted branch and master issue — is frozen into the registry, so the protocol's own publisher-rotation step no longer makes an existing registry unreadable; a regression rotates publishers, disables writes, and still reads and audits, while a changed master issue or repository is refused. `reconcile` now runs the publisher-allowlist preflight, because it commits registry writes too. `recover` validates a fetched payload against the operator's configuration rather than the copy embedded in it, and `read` measures the decoded payload instead of trusting the size GitHub reports — the read regression now injects an understated size over an oversized body.

### Test-design correction

The reviewer noted that `LedgerTests` patches `authority` wholesale, so the approval gate was never exercised on `publish` or `close`. A new test in `AuthorityAndAdapterTests` drives `publish`, `reconcile`, `release` and `close` through the real `authority` against a synthetic approved project, then revokes the bound GitHub project-write permission and deactivates the bootstrap, asserting every mutating operation refuses with no GitHub mutation while read-only audit still succeeds.

### Verification

All 57 ledger tests passed in 29.018 seconds and the full suite passed all 214 tests in 105.656 seconds. Repository validation passed 57 required paths and the bootstrap distribution check reported 0 differing files. Current-head GitHub CI and review results remain in PR #19 and issue #6.

### Fifth review round

Codex returned on `5c6e01496e446184557f289d06cbb17de4b8407b` with one P1 and two P2 findings, all against the remediation above. All three are corrected; the P1 reversed part of ADR-008 and is recorded as **ADR-009**.

**P1 — a released claim could double-publish.** `release` treated "no comment visible across every page" as proof that the POST never took effect. Full pagination proves only present absence: a comment GitHub accepted before a timeout can become visible later, after the claim was retired, and the next publication would then post a second copy. The fix removes `release` entirely and makes the pre-POST state resumable instead. Publication now moves through three committed phases — `claimed` takes the exclusive claim, `posting` records that a POST is about to be attempted, `done` records the receipt — and the comment is posted only from `posting`. A `claimed` entry is therefore durable proof that no POST was attempted, so any publisher may resume it and the original dead end disappears without any evidence-free retirement. A `posting` entry with no visible comment stays uncertain indefinitely, is never resumed or retried, and has no command that retires it. The regression confirms the lost claim write leaves `claimed` with zero comments posted, resumes to exactly one comment and a clean audit, and that an attempted publication refuses both publish and reconcile and cannot be rewound to `claimed` or `new`.

**P2 — publisher rotation invalidated historical receipts.** Relaxing the frozen configuration let `publishers` change while `matches` still validated every historical comment against the current allowlist, so rotating out an author made immutable, previously valid receipts read as untrusted. Each completed receipt now records its own author, which is immutable once written and is what validates that comment; the rotated allowlist applies only to new publications. The regression rotates publishers, confirms audit still trusts the existing receipt, confirms the recorded author cannot be changed, and confirms a comment rewritten by a different account still fails.

**P2 — seeded supersession history.** The prior-state loop never inspected newly added tasks, so a first registration could assert an arbitrary `superseded_prs` list, permanently reserving PR numbers against their real tasks and fabricating append-only history without ever performing a replacement. A task's first registration must now carry an empty list, refused before any GitHub mutation.

All 59 ledger tests passed in 31.653 seconds and the full suite passed all 216 tests in 106.056 seconds. Repository validation passed 57 required paths and the bootstrap distribution check reported 0 differing files.
