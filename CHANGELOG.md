# Changelog

## 2026-09-13 — Issue #8 reopened: answer the Codex findings on PR #21

- Bind every acceptance decision to its task id, revision, contract hash and reviewed result `dispatch_id`; the feedback ledger's REVIEW event and `sync-feedback` refuse a mismatch (Codex P1).
- Refuse opening a review whose declared reviewer tier is below the contract's `routing.reviewer_tier` (Codex P1).
- Inspect every workspace entry, including directory symlinks, before building the deterministic-gate digest (Codex P2).
- Stream check output into bounded buffers while hashing the complete stream, and kill a runaway check at its timeout with a bounded record (Codex P2). Round 2 on PR #22: terminate the whole process tree and bound the pipe drain so a descendant cannot defeat the timeout (P1); refuse a symlinked workspace root before resolving it (P2). Round 3: scan the workspace for symlinks before any command runs as well as after (P1); kill the tree, via a Windows job object or the POSIX process group, whenever the drain is abandoned after a normal exit (P1); replay pre-binding REVIEW events in existing ledgers under the legacy shape while refusing new decisions without the binding (P1, ADR-022). Round 4: save the process group at creation so it can be killed after the leader is reaped (P1); scan before each declared command, not once before the loop (P1); end whatever is left in the tree when the check is over even if it closed its pipes (P1); read pipes with `os.read` so partial output is captured while a descendant holds them, which was the Linux CI failure. Round 5: create the Windows check suspended and assign it to its job before it runs (P1); state in the protocol that declared commands are not sandboxed and that a daemonizing or transient-symlink command is beyond the gate, with isolation as a deployment control (two P1s answered as a boundary, not a fix). Round 6: walk the workspace incrementally with an entry bound as well as the file bound, so a tree of many directories is refused rather than materialized (P2). Round 7: refuse the run on Windows when the job object cannot be created or assigned instead of resuming the check unisolated (P1); traverse with `os.scandir` so a wide directory is not buffered before the bound applies (P2). Round 8: after ending the tree, wait bounded until the process group or job reports no live member and refuse the run otherwise, so a dying descendant cannot race the digest (P1). Round 9: on POSIX, count only non-zombie members of the group from `/proc`, so a container whose PID 1 does not reap orphans does not make a clean run refuse (P1). Round 10: an unreadable or unparseable `/proc` record counts as alive, only a vanished pid is skipped (P1); a Windows check that cannot be resumed is killed and the run refused immediately (P2). Round 11: refuse an NTFS junction or any other reparse point at the workspace root and during traversal, since `is_symlink()` does not report them and `resolve()` follows them (P2); probe the process group before counting `/proc` records, so a vanished group is stopped even where a `hidepid` mount hides unrelated processes, while a group that remains still fails closed on unreadable records (P2). Round 12: inspect every existing component of the supplied workspace path, not only its final one, so a linked ancestor is refused before `resolve()` follows it (P2). Round 13: refuse a `..` component in the supplied path outright, since lexical normalization collapses `link/../x` while the filesystem follows the link (P2); the test helper treats an orphaned zombie as dead so the descendant regressions hold in a container without a reaping PID 1 (P2).
- Record the standing review rules in the repository instructions: no merge without a Codex review of the current head SHA, no next child while findings are open, GitHub via `gh api` as the only source of findings.

## 2026-09-13 — Issue #8 independent acceptance gates

- Add the acceptance controller: one append-only hash-chained ledger per reviewed task, filling the gap between the feedback controller's REVIEW_PENDING and the packet's REVIEW → ACCEPTED transition.
- Independently re-execute the contract's declared validation commands as the deterministic gate — the single deliberate exception to the metadata-only pattern — recording observed exit codes, bounded output and a workspace digest, and failing closed to non-implementer attestation for checks without a command.
- Assign risk-tier gate floors in the work-packet layer (low deterministic; medium + model review; high + cross-family; critical + architect review and user decision); packets and configuration can only tighten, and contract repair can no longer change risk or the review block.
- Render bounded, credential-scanned minimal-context review packets from ledger records only, separating worker-supplied claims from independently observed results; enforce five reviewer verdicts with structural refusals, submission-bound gate satisfaction, and a hard cross-family gate with recorded waiver.
- Return bounded rejections to the worker inside the same frozen budget with the contract failures in the next brief, escalate repeated identical rejections, and let acceptance — never a lone approval — close the task ledger.
- Dogfood the machinery on Issue #8's own diff: a Gate D failure contradicting the implementer's clean-run claim, a real gate-bypass finding from a minimal-context reviewer, the regression-tested correction, and acceptance only after re-review; record in `docs/ISSUE_8_VALIDATION.md`.

## 2026-09-13 — Issue #7 bounded execution harness

- Add a preparation-and-ingestion adapter that renders only packet-permitted context into a worker brief, emits the exact harness invocation, and never invokes a model or runs the harness command.
- Refuse a worker report that invents or omits a validation id, grades itself, widens scope, carries credential-like material or exceeds its bound; close an unreported attempt only through an explicit `abandon` with a stated reason.
- Refuse a dispatch whose brief, rules, declared harness overhead and reserved output cannot fit the window the routed resource is actually served in, closing the spent reservation with the arithmetic as evidence.
- Bind routed resources to harnesses by configuration with credentials named only by environment variable, and declare a non-Cline adapter so replaceability is demonstrated rather than asserted.
- Record four operator-executed live runs, including the passing one, with each failure's correction and the limitations carried forward in `docs/ISSUE_7_VALIDATION.md`.

## 2026-09-12 — Issue #6 GitHub task ledger

- Add canonical task/issue registration, complete packet and feedback publication, exclusive comment claims and pinned recovery.
- Detect live issue/PR/accepted-commit drift, unpublished records, untracked discoveries and stale structured project status.
- Deliver six issue forms and linked PR conventions; preserve explicit authority and metadata-only acceptance boundaries.

## 2026-09-12 — Issue #5 bounded feedback controller

- Reserve worker intents durably before dispatch and replay immutable events to recover task state and cumulative usage.
- Enforce total/per-tier limits, stable repeated-failure escalation, focused context, finite repair/recovery/diagnosis allowances and sticky architecture/approval holds.
- Require complete objective-check reports before moving to independent review; preserve raw failures, explicit provider recovery and bounded comment evidence views.
- Validate concurrency, crash/refusal paths and generated-profile delivery with synthetic records; retain actual acceptance in #5 and its PR.

## 2026-09-12 — Issue #4 capability router and economic governor

- Add provider-independent configuration with disabled fictional examples for LM Studio, Mistral, Claude and OpenAI/Codex.
- Select within exact effort and authorized tier paths using risk/complexity floors, accepted-result cost estimates, supplied performance observations and bounded retry/fallback policy.
- Save immutable local routing decisions with original inputs, reasons, exclusions, cost components and deterministic replay; retain explicit offline and execution-authority boundaries.
- Cover routing failure paths and delivery through generated projects; retain actual checks/review/acceptance in #4 and its PR.

## 2026-09-12 — Issue #3 work-packet contract foundation

- Add a shared JSON Schema contract and complete synthetic examples for all three domains.
- Generate GitHub issue views from canonical packets; preserve versioned snapshots and validate recorded lifecycle, roles, evidence references and dependency graphs.
- Keep packet tools local and optional to bootstrap; document their trust boundary and future executor/review responsibilities.
- Cover packet failure paths and generated root/native/standalone delivery; retain actual validation/review and acceptance evidence in Issue #3 and its PR.

## 2026-09-12 — Issue #2 bootstrap activation foundation

- Integrate inactive project generation, staged profile intake, complete review packets and explicit fingerprint-bound activation.
- Reject incomplete/malformed setup, stale configuration/documents, domain/workflow changes, cyclic dependencies and initialized-project rebootstrap.
- Apply the gate to every model startup and synchronize root/native/standalone payloads with a CI consistency check.
- Verify 32 tests, including all three profiles and Windows Git commit/clone approval portability; record independent review and remaining limitations in `docs/ISSUE_2_VALIDATION.md`.


## 2026-08-29 — v1.0.0

- Created universal multi-model project structure.
- Added native entrypoints for Codex, Claude Code, ChatGPT web, Claude web, and GitHub Copilot.
- Added bootstrap, validation, connector selection, skill selection, handoff, and source-ledger workflows.
