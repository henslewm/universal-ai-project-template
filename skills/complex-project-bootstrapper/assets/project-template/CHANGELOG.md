# Changelog

## 2026-09-23 — Scope policy: review findings must be concrete defects (ADR-063)

- Agents were treating broad project guidance, review suggestions and nearby weaknesses as authorization to expand a task; reviews generated additional requirements, implementation expanded to satisfy them, and repeated rounds kept growing the work. The instruction sources said "answer every finding" with no test for what counts as one, so an optional suggestion carried the same force as a genuine defect.
- `MASTER_INSTRUCTIONS.md` now states that the requested task and its accepted contract define authorized scope, and that a finding is actionable only when it names a concrete defect the change introduced or exposed, or a demonstrable failure of an explicit requirement applicable to the task under review. Optional improvements, speculative hardening, refactors and pre-existing conditions get a reasoned decline and a separate record instead of entering the task.
- `MASTER_CLAUDE_CODE.md`, `.claude/rules/02-git-and-change-control.md` and the `.claude/agents/reviewer.md` brief are aligned to the same classification; the `sync_skills.py` payload mirror carries it so newly generated projects inherit the boundary.
- Instruction text only, no code changed. Also ported to `esp32-ble-motors` and `shopmonkey_pricefileupdate_landNsea`.

## 2026-09-15 — Issue #9 follow-up: PR #35 P2 answered (ADR-058)

- P2: ADR-057 made a zero-timeout `receive()`'s body read unconditional, fixing a fully-buffered frame but reopening the ADR-042 hazard from the other direction (a body that only became available after the poll instant could still be returned as received in time), and never fixed a pre-existing bug where a port handing back an already-fully-buffered frame in small chunks timed out on data that had been sitting there from the start. `receive(0)` now samples `Port.available()` once before touching the port and never draws more than that many bytes across the whole call; a trickling but fully-buffered frame now assembles complete, and a body that arrives only after the poll instant still times out and closes the port.
- Found by a follow-up review of PR #35 (Codex plus an independent review), posted on the PR itself.

## 2026-09-15 — Issue #9 follow-up: post-merge independent review answered (ADR-056, ADR-057)

- P1: the printed hardware-evidence lines omitted `validation_id`, so a schema-valid record made for one hardware-rung check could be appended unchanged for a different check in the same submission -- level, device, firmware, observed_at, outcome, operator, dispatch_id and artifact_sha256 can all legitimately match across two checks. Reproduced with a room-temperature record attested against a maximum-temperature check; default status wrongly reported `VERIFIED_ON_HARDWARE`. A hardware-rung attestation now also carries `validation_id`, checked against the attestation's own target at append time and against the record on the record basis.
- P2: ADR-042 made a receive() body read's first contact conditional on remaining time regardless of the requested timeout, so `receive(0)` against a port with the whole frame already buffered read the header, then refused to look at the already-buffered body and raised a timeout for a complete frame that was there from the start. The body read now earns the same unconditional first contact the header gets, exactly when the whole call is itself a zero-timeout poll; a positive timeout keeps ADR-042's protection unchanged.
- Both findings and their reproduction steps came from an independent review of `main` after PR #34's merge, posted through the maintainer's own GitHub account.

## 2026-09-15 — Issue #9 PR #34: Codex round 23 answered (ADR-055)

- P2: `templates/software-hardware/PROFILE.md` and its identical `DOMAIN_PROFILE.md` copy still said acceptance plus full attestation earns `VERIFIED_ON_HARDWARE` unconditionally, contradicting `status()`'s actual behavior (ADR-050) for every worked example packet, all six of which declare `synthetic: true`. Both now state the ceiling explicitly.

## 2026-09-15 — Issue #9 PR #34: Codex round 22 answered (ADR-054)

- P1: `checked_artifact` permits empty content for a reference-kind artifact, so its sha256 is then the fixed empty-content digest regardless of what `reference` names -- a resubmission could change the referenced commit while sha256 (and dispatch_id) both stay the same, and an old hardware evidence record would still verify against the new reference on either basis. `acceptance.artifact_identity(artifact)` combines `reference` and `sha256` into one digest; every place a hardware record binds to the current artifact now uses this identity instead of `sha256` alone. Regression: two reference-kind artifacts sharing one empty-content digest still produce two different identities.

## 2026-09-15 — Issue #9 PR #34: Codex round 21 answered (ADR-053)

- P1: `deterministic_status` counts a domain-shortfall-marked attestation as ATTESTED so a ledger already accepted on one keeps replaying as accepted, but a ledger that had only reached GATES_PENDING before the rule existed could still be freshly accepted today, using evidence the current rules explicitly reject. `acceptable` now refuses a new (not-yet-stored) ACCEPT that would rest on a shortfall-marked attestation, while a stored ACCEPT over the same shortfall still replays accepted, preserving history per ADR-032. Regression covers both: a new accept is refused and requires a fresh attestation; a stored accept keeps replaying.

## 2026-09-15 — Issue #9 PR #34: Codex round 20 answered (ADR-052)

- P2: checking dispatch_id/artifact_sha256 alone still let a record carry a stale `observed_at` copied from an earlier submission -- an operator who updated the two identifiers as instructed but left the timestamp could earn `VERIFIED_ON_HARDWARE` for an observation that predated the resubmission. The acceptance ledger now tracks `submitted_at` (the INIT event's timestamp, refreshed by RESUBMIT), and `validate_attestation` refuses a declared `observed_at` earlier than it, alongside the existing upper bound at the attestation event itself. Test fixtures across tests/test_acceptance.py and tests/test_software_hardware.py that used a fixed illustrative `observed_at` now compute one live, since a real ledger's submission always postdates a value fixed at test-file import time.

## 2026-09-15 — Issue #9 PR #34: Codex round 19 answered (ADR-051)

- P2: `ACCEPTANCE_PROTOCOL.md`'s normative description of the software-hardware domain rule predated ADR-049 and ADR-050 -- it omitted the now-required `dispatch_id` and artifact digest attestation lines and still said every fully attested accepted task earns `VERIFIED_ON_HARDWARE`, ignoring the `synthetic: true` cap. Updated to state both.

## 2026-09-15 — Issue #9 PR #34: Codex round 18 answered (ADR-049, ADR-050)

- P1: ADR-047 closed the record-basis gap for a resubmitted result and artifact, but the attestation-basis path (no `--evidence-dir`) still trusted an operator's re-attested, unchanged record after a resubmission and reported it VERIFIED_ON_HARDWARE without the ADR-047 comparison ever running. A hardware-rung attestation now also carries `dispatch_id` and `artifact_sha256` (extending ADR-038's line count from six to eight recognized lines), and `validate_attestation` refuses one that does not match the ledger's current result and artifact at append time, on either basis (ADR-049).
- P1: every canonical SHB example and dogfood packet declares `synthetic: true`, but nothing checked that flag, so an attested illustrative record could be reported VERIFIED_ON_HARDWARE, misrepresenting fictional dogfood as physical verification. `status` now refuses to derive VERIFIED_ON_HARDWARE for a synthetic contract regardless of attestation or acceptance state, and excludes an attested hardware rung on one from `highest_level_satisfied` (ADR-050).

## 2026-09-15 — Issue #9 PR #34: Codex round 17 answered (ADR-048)

- P2: `device_identity`, `firmware_version` and `operator` were unbounded, so a schema-valid record could still be refused at attestation once `evidence_lines()` added a key prefix and the value exceeded acceptance's own 2000-character `bounded_text` element limit. `single_line` now caps at 1991 characters, leaving room for the longest key (`firmware=` / `operator=`).
- P2: `identifier` and `sha256`'s `$`-anchored patterns admitted a trailing newline (the same class ADR-039 found for `single_line`), so `task_id`, `contract_hash`, `dispatch_id` and `artifact_sha256` could carry one and validate while differing from the strictly compared ledger binding. Both now use the strict end assertion `(?![\s\S])`, matching `config/acceptance.schema.json`'s own idiom.

## 2026-09-15 — Issue #9 PR #34: Codex round 16 answered (ADR-047)

- P1: contract identity does not identify which implementation was tested. `RESUBMIT` replaces the result and artifact under the same contract and revision and clears prior attestations, but nothing stopped an operator from re-attesting the same unchanged evidence file after a rejection, silently verifying the resubmission it was never observed against. The schema now also requires `dispatch_id` and `artifact_sha256` on every record, and `record_problems` checks both against the acceptance ledger's current result and artifact. Regression rejects an attested submission, resubmits with a different result and artifact, and shows the unchanged evidence refused against the resubmission while a record made against the new submission verifies.

## 2026-09-15 — Issue #9 PR #34: Codex round 15 answered (ADR-046)

- P2: nothing compared a hardware evidence record's declared `observed_at` to when it was attested, so an observation dated after its own attestation (or arbitrarily in the future) passed both the attestation-basis and record-basis checks, letting an accepted ledger report `VERIFIED_ON_HARDWARE` for an observation that had not yet occurred. `validate_attestation` now takes the ATTESTATION event's own timestamp and refuses a declared `observed_at` later than it, using a `parse_timestamp` helper factored out of the existing date-time format checker. Regression appends an attestation dated after the event and shows it refused.

## 2026-09-15 — Issue #9 PR #34: Codex round 14 answered (ADR-045)

- P2: the example hardware evidence record's `contract_hash` was fictional-but-valid, not the actual fingerprint of the SHB-04-adapter packet it documents, so the standalone `hardware-evidence` command passed while `status --evidence-dir` would refuse it against a real ledger -- the canonical example could not demonstrate the flow the README describes. The record now carries revision 1's real `work_packet.fingerprint`; a regression checks it directly against the packet file.

## 2026-09-15 — Issue #9 PR #34: Codex round 13 answered (ADR-044)

- P1: revision numbers are lineage-local -- two independently revised variants of the same task can both be "revision 2" with different content, so binding a hardware evidence record by revision number alone let a record from one variant verify a ledger bound to the other. The schema now also requires `contract_hash` (sha256), and `record_problems` checks it against the acceptance ledger's binding alongside `revision`. Regression revises the same base packet twice with different content, both landing on revision 2, and shows a record bound to one variant refused against the other's ledger.

## 2026-09-15 — Issue #9 PR #34: Codex round 12 answered (ADR-043)

- P1: a hardware evidence record carried no contract revision, so record verification checked only task and validation identity; a revision that keeps the same task, validation ID and rung let hardware evidence from a changed, earlier revision verify a later one. The schema now requires `revision` on every record and `record_problems` refuses one that does not match the acceptance ledger's `binding.revision`. Regression revises the packet to revision 2 and shows a revision-1 record refused while a matching-revision record still verifies.

## 2026-09-15 — Issue #9 PR #34: Codex round 11 answered (ADR-042)

- P2: the one-poll allowance in `SerialAdapter.receive` belongs to the call, not to each `_read_within` — the header read is the call's first port contact and the body read is not, so a header that arrived in time whose body did not is a started frame that closes the port rather than a frame returned late (ADR-042, completing ADR-031). Regression delivers the body after the deadline and shows the port not polled again. 39 sample tests.

## 2026-09-15 — Issue #9 PR #34: Codex round 10 and the independent review answered (ADR-041)

- P1 (Codex round 10 and the independent review): the feedback ledger's stored `REPAIR_CONTRACT` diagnosis replays with its shortfall recorded in `domain_shortfall` (in `summary`), `work_packet.revise` takes `domain_rules` so a stored repair's revision is not re-judged, and a new repair that fails the rules is refused; every contract-validating path now threads `stored` to the domain rules (ADR-041). Regression writes a legacy repair on the chain by hand.
- P2 (Codex round 10): `SerialAdapter._read_within` makes the first read unconditionally (a zero timeout polls what has arrived) and never asks the port again once the deadline has passed, so bytes arriving late are not returned as a frame received in time (ADR-031 completed).
- P2 (independent review): `SensorDevice.read()` keeps the SHB-03 promise that it returns a Reading or raises `DeviceError` — a port that raises on send or receive (a disconnect) or a short write is translated at the device boundary as `transport failure` with the cause chained, instead of escaping as `OSError` or `RuntimeError` past the workflow's `except DeviceError`. Regressions at the device (each cause, on send and on receive; a negative timeout stays a `ValueError`) and through the real adapter into the workflow (each failure logs an ERROR, closes the adapter, and the next read reports the closed adapter). 38 sample tests.

## 2026-09-15 — Issue #9 PR #34: Codex round 9 answered

- P2: `single_line` states its prohibition as `not: {pattern: "[\r\n]"}` instead of an anchored pattern, because `$` matches before a trailing newline; a record whose `device_identity`, `firmware_version` or `operator` ends in a line break is now refused at the record rather than accepted there and refused at attestation (ADR-039 completed). Regression for trailing and leading CR, LF and CRLF.

## 2026-09-15 — Issue #9 PR #34: Codex round 8 answered (ADR-039, ADR-040)

- P1: `device_identity`, `firmware_version` and `operator` are `single_line` by schema and `validate_attestation` refuses any element carrying CR or LF, so ADR-038's seven lines are seven physical lines (ADR-039).
- P2: the bootstrapper's `references/intake-schema.md` names the nine software-hardware orientation fields, and a regression checks every profile's `DOMAIN_FIELDS` against the reference and its two copies; with the round-1 schema test, every published listing is bound to the validator (ADR-040).
- A stale payload mirror of the domain test file (one edit after the last sync) failed CI on `b0f3ca1`; resynchronized.

## 2026-09-15 — Issue #9 PR #34: Codex round 7 answered after a third stop-for-diagnosis (ADR-038)

- P1: a hardware-rung attestation is exactly the digest line and the six `key=value` lines `hardware-evidence` prints; `parsed_evidence_strict` returns every other line and `validate_attestation` refuses any, whitespace variants included, so no attested line goes unverified. The #8-era fixture that mixed a narrative line with the record lines is corrected; regression covers leading-space, spaced, upper-cased, free-text, unknown-key and empty lines.

## 2026-09-15 — Issue #9 PR #34: Codex round 6 answered

- P2: the packet layer's stored-revision shortfall is never silent: `validate` and `graph` print a `DOMAIN SHORTFALL` line naming the failing revisions after their verdict, `render` carries it in the issue view, and `WORK_PACKET_PROTOCOL.md` describes the split (ADR-037 completed). Regression covers `render`, `validate` and `graph`.

## 2026-09-15 — Issue #9 PR #34: Codex round 5 answered (ADR-036, ADR-037)

- P1: the work-packet layer gets the ADR-032 boundary: `validate` checks stored revisions against the common contract only, `domain_shortfall` names revisions that fail the profile's rules, and `create`/`revise` refuse a new contract that fails them, so a packet authored before the rules can be transitioned and revised into compliance instead of being stranded (ADR-037).
- P2: `close` forgets the port before asking the driver to close it, and `_wire` propagates the original wire failure with a failing close attached as its cause, so a driver whose `close()` raises cannot leave the adapter open (ADR-036; 34 sample tests).
- P2: `load_record` refuses `NaN`/`Infinity` and overflowing literals, and `_find_record` treats a digest failure as a refused file, so one bad file never aborts `status --evidence-dir` (ADR-037).

## 2026-09-15 — Issue #9 PR #34: Codex round 4 answered (ADR-035)

- The adapter class recurred a fourth time (a write that raised after a partial transmission left the port open), so the ADR-033 owner is widened from `receive` to every port call: `_wire` closes the port on any exception leaving contact with the port; only a receive that timed out having consumed nothing leaves it open (ADR-035). Regression: a raising read before or after the header, and a raising write, each close the port.
- P2: `status` counts a hardware rung toward `highest_level_satisfied` only when its record verified on the record basis; an attested rung whose record is missing, invalid or inconsistent is not a satisfied rung.

## 2026-09-15 — Issue #9 PR #34: Codex round 3 answered after a second stop-for-diagnosis (ADR-033, ADR-034)

- The adapter class recurred a third time (a body read that raises left the port open with a started frame), so the ADR-031 invariant now has one owner: everything after the first consumed byte runs under a single guard that closes the port on any exception (ADR-033). Regression: a port that raises after the header closes the adapter; before any byte, it stays open (33 sample tests).
- P1: hardware evidence records enter through one loader, `load_record`, which refuses a duplicate key at any depth; `_find_record` names a refused file in `status --evidence-dir`'s reason instead of skipping it; the `hardware-evidence` command uses the same loader (ADR-034).
- P2: `observed_at` is a `date-time` format validated by a format checker on the domain validator, so `2026-99-99T99:99:99Z` and `2026-02-30` are refused, not only malformed shapes (ADR-034).

## 2026-09-15 — Issue #9 PR #34: Codex round 2 answered after stop-for-diagnosis (ADR-031, ADR-032)

- R-012 applied: the sample adapter's framing/timeout class recurred across rounds 1 and 2, so the invariant was written first. `Port.read(size, timeout_s)` carries the deadline and `SerialAdapter.receive` hands each read the time remaining; a frame started but not finished closes the port before `TransportTimeout`; a timeout that consumed nothing leaves it open (ADR-031). SHB-04's port contract, host rules and hardware assumption say so; sample tests add a blocking port bounded by the remaining time and a partial-frame closure (32 sample tests).
- P1: a stored INIT whose contract fails the profile's domain rules replays marked with `domain_shortfall` instead of refusing the ledger (the #8 dogfood ledger replays again); a new INIT is refused as before. `validate_contract` gains `domain_rules=False` for that replay and `work_packet.domain_errors` exposes the profile's errors (ADR-032).
- P2: a stored attestation the profile rule would now refuse replays marked; `status` reports it unverified and refuses to derive a hardware status from a marked contract; new events are refused as before (ADR-032). `summary` and the review packet carry both marks.
- P2: record verification compares device, firmware, observation time, level and outcome exactly and case-folds only the operator (ADR-032).

## 2026-09-15 — Issue #9 PR #34: Codex round 1 answered (ADR-030)

- P1: `parsed_evidence` refuses a recognized attestation key that appears more than once instead of keeping the first; `status` reports a stored attestation that no longer parses as unverified. Regressions at parse, at `attest`, and in the digest-lines test.
- P2: the sample `SerialAdapter.receive` assembles a frame across partial port reads until the declared length arrives or the caller's `timeout_s` expires, and refuses an oversized frame by declared length before reading its body. Sample tests add a trickling port and a timeout-governance check (30 sample tests).
- P2: `config/bootstrap.schema.json` requires the same nine software-hardware orientation fields as `validate_bootstrap.DOMAIN_FIELDS`; a regression binds the schema to the validator.

## 2026-09-14 — Issue #9 corrections after the provisional dogfood

- Merge `origin/main` (PR #22, #8 closed again) into `issue-9-software-hardware-domain` with a merge commit; the branch's hardware-evidence and merge-before-review risks are renumbered R-013 and R-014 because `main`'s R-012 is #8's patch/review-loop risk; state records now say #9 started 2026-09-13 with an approved design rather than "not started".
- `AC-SAMPLE` (ADR-028): the adapter's sample tests consume only the transport interface and speak raw bytes; the device-through-adapter case moves to the workflow packet; `SHB-06-workflow` declares the codec and the device packet's test double it consumes; the scoping test parses every named file's `synth_bridge` imports with `ast` and compares them to the declared scope and dependencies, with a negative control. The sample suite is 28 tests.
- `validate_contract(contract, profile)` requires a registered profile — no default, `None` refused — and every caller names one (ADR-026).
- The `software-hardware` domain block is closed (`additionalProperties: false`, `template_child_issue` declared for the template's dogfood packets) and the literal `VERIFIED_ON_HARDWARE` is refused in any string it carries; the example contract loses its undeclared `fixture_protocol` key (ADR-026).
- `software_hardware.py status` reports `evidence_basis` (`attestation` or `record`), says in its reason when digests are attested but not record-verified, emits `evidence_path` on every entry, and under `--evidence-dir` refuses a record recorded by an operator other than the attesting one (ADR-027). Regressions for each, including a CLI test of `status` with and without `--evidence-dir`.
- Two #8 regressions from PR #22 that append a second validation now map it to a rung, as the #9 rules require.
- Repeat dogfood at `_acceptance-demo-9b`: deterministic gate PASSED; round 1 (same-family, minimal context) APPROVE; round 2 (Codex, cross-family) REJECT_BOUNDED on `AC-EXTENSIONS` — a digest-matched object was verified without schema validation or comparison of the attested device, firmware and time lines. `status --evidence-dir` now validates the found record against `$defs/hardware_evidence` and compares every attested line with it, naming each disagreement (ADR-029); regressions cover the five-field stub, each metadata mismatch and the consistent record. Resubmission PASSED the gate again; round 3 (Codex, cross-family) APPROVE; `accept` recorded `ACCEPTED` with no waiver — 11-event ledger preserved at `_acceptance-demo-9b`. `docs/ISSUE_9_VALIDATION.md` loses its provisional markers and maps #9's four criteria to evidence.

## 2026-09-15 — Issue #8 closed again through merged PR #22

- PR #22 merged at `494587cfae01f9dde442a5d0e5fbe50cdfb6b257` (merge commit; parents `0c8fc8c` and `3a4e92b`) after a clean Codex review of the head, CI green and explicit maintainer authorization; #8 closed with its completion comment and master #14 noted. State records updated on `main` with the merge SHA and dates; OL-012 closed, OL-014 unblocked.

## 2026-09-13 — Issue #8 reopened: answer the Codex findings on PR #21

- 2026-09-14: `PROJECT_STATE.md`, `HANDOFF_CURRENT.md`, `OPEN_LOOPS.md` and `docs/ISSUE_8_VALIDATION.md` now say #8 is reopened with PR #22 in flight and #9 blocked, replacing the closure wording that Codex found still directing a fresh session into #9 (P2); `RISK_REGISTER.md` adds R-012 for the patch/review loop.

- Bind every acceptance decision to its task id, revision, contract hash and reviewed result `dispatch_id`; the feedback ledger's REVIEW event and `sync-feedback` refuse a mismatch (Codex P1).
- Refuse opening a review whose declared reviewer tier is below the contract's `routing.reviewer_tier` (Codex P1).
- Inspect every workspace entry, including directory symlinks, before building the deterministic-gate digest (Codex P2).
- Stream check output into bounded buffers while hashing the complete stream, and kill a runaway check at its timeout with a bounded record (Codex P2). Round 2 on PR #22: terminate the whole process tree and bound the pipe drain so a descendant cannot defeat the timeout (P1); refuse a symlinked workspace root before resolving it (P2). Round 3: scan the workspace for symlinks before any command runs as well as after (P1); kill the tree, via a Windows job object or the POSIX process group, whenever the drain is abandoned after a normal exit (P1); replay pre-binding REVIEW events in existing ledgers under the legacy shape while refusing new decisions without the binding (P1, ADR-022). Round 4: save the process group at creation so it can be killed after the leader is reaped (P1); scan before each declared command, not once before the loop (P1); end whatever is left in the tree when the check is over even if it closed its pipes (P1); read pipes with `os.read` so partial output is captured while a descendant holds them, which was the Linux CI failure. Round 5: create the Windows check suspended and assign it to its job before it runs (P1); state in the protocol that declared commands are not sandboxed and that a daemonizing or transient-symlink command is beyond the gate, with isolation as a deployment control (two P1s answered as a boundary, not a fix). Round 6: walk the workspace incrementally with an entry bound as well as the file bound, so a tree of many directories is refused rather than materialized (P2). Round 7: refuse the run on Windows when the job object cannot be created or assigned instead of resuming the check unisolated (P1); traverse with `os.scandir` so a wide directory is not buffered before the bound applies (P2). Round 8: after ending the tree, wait bounded until the process group or job reports no live member and refuse the run otherwise, so a dying descendant cannot race the digest (P1). Round 9: on POSIX, count only non-zombie members of the group from `/proc`, so a container whose PID 1 does not reap orphans does not make a clean run refuse (P1). Round 10: an unreadable or unparseable `/proc` record counts as alive, only a vanished pid is skipped (P1); a Windows check that cannot be resumed is killed and the run refused immediately (P2). Round 11: refuse an NTFS junction or any other reparse point at the workspace root and during traversal, since `is_symlink()` does not report them and `resolve()` follows them (P2); probe the process group before counting `/proc` records, so a vanished group is stopped even where a `hidepid` mount hides unrelated processes, while a group that remains still fails closed on unreadable records (P2). Round 12: inspect every existing component of the supplied workspace path, not only its final one, so a linked ancestor is refused before `resolve()` follows it (P2). Round 13: refuse a `..` component in the supplied path outright, since lexical normalization collapses `link/../x` while the filesystem follows the link (P2); the test helper treats an orphaned zombie as dead so the descendant regressions hold in a container without a reaping PID 1 (P2). Round 14: replay a stored `REVIEW_OPEN` below the contract's reviewer tier marked with `tier_shortfall` instead of refusing the ledger, keep a stored acceptance on it as history, and refuse a new acceptance resting on it (P1, ADR-023). Round 15: a marked legacy opening does not count against `max_review_attempts`, so a ledger that had spent its budget before the tier was enforced keeps a slot for the compliant replacement (P1). Round 15 (ADR-024, stop-for-diagnosis): the lifetime and trust classes are made invariants instead of point checks — `ProcessTree.run` owns a check from launch to confirmed-stopped and ends the tree on every exit including a controller exception; `trusted_workspace`/`check_cwd`/`linked_component` establish trust before any command and inspect every `cwd` component before resolution — with one regression per invariant; the ingest-review result reports the legacy-aware `reviews_used` (P2). ADR-025: the GitHub ledger accepts a feedback ledger at `ACCEPTED` (the status `sync-feedback` leaves) as the base for reviewer/integrator extension and final publication, closing the seam Codex reproduced in which accepted work could not be published (P1). Round 16: only a launch failure is converted into a failed-check record; an OSError from owning or tearing down the check propagates and refuses the run, since the previous handler wrapped the whole owned block and would have digested over a tree never confirmed stopped (P1). Round 17: an unreadable `/proc` record was excluded from the liveness count when owned by another user (P2). Round 18: that inference was fail-open — a setuid helper changes owner without leaving the group — so membership is now established by the kernel's `getpgid`, which needs no `/proc` permission: another group or a vanished pid is skipped, our own group or any other failure still counts as alive (P1).
- Record the standing review rules in the repository instructions: no merge without a Codex review of the current head SHA, no next child while findings are open, GitHub via `gh api` as the only source of findings.

## 2026-09-13 — Issue #9 software + hardware domain template

- Add `config/domains/software-hardware.schema.json` and `scripts/software_hardware.py`: the software-hardware `domain` block becomes structural — one named component, hardware assumptions citing contract sources, protocol references, every validation mapped to one rung of the verification ladder, and a declared hardware status limited to `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING`.
- Register per-profile domain rules in `work_packet.DOMAIN_MODULES`, applied inside `validate_contract` on every contract-validation path and at the acceptance ATTESTATION event; no existing refusal, floor or gate is loosened.
- Bind the ladder to the acceptance split: machine rungs must declare a command the deterministic gate re-executes; hardware rungs must not, and their attestation must bind a validated hardware evidence record by digest with a `pass` outcome recorded by the attesting operator.
- Derive the earned hardware status from the acceptance ledger (`software_hardware.py status`): `VERIFIED_ON_HARDWARE` only for an accepted task whose hardware rungs were all attested; a machine-only acceptance never earns it.
- Extend the software-hardware bootstrap intake to nine required orientation fields; rewrite `templates/software-hardware/PROFILE.md` and `DOMAIN_PROFILE.md`; cross-reference the work-packet, acceptance and bootstrap protocols.
- Ship `examples/software-hardware/`: a fictional synthetic sensor bridge with 27 runnable tests decomposed into six component-scoped packets (one hardware-in-loop and one field attested check), a hardware evidence example and an operator procedure; update the software-hardware example contract.
- Add 25 tests (309 total); register 14 new required paths (81 total).

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
