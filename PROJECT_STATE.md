# Project State

## Current (2026-10-03): frozen at the software and hardware tracks (ADR-089)

- **Scope:** the software and hardware tracks are complete: bootstrap (including `--no-hardware`), work packets, acceptance, feedback, model routing and the hardware verification ladder. Legal profiles are archived under `archive/legal/`; `worker_launcher` and `github_ledger` are removed (ADR-083). Further work only on a new owner request.
- **Decisions (ADR-089):** review cap of 4 per PR, worker-attempt default 2 (recorded only), approvals unchanged, no combined ledger, no automatic delegation, savings telemetry (#12, #13) deferred. ADR-084 to ADR-088 withdrawn.
- **Verified:** `validate_project.py` passes with 81 required paths; `sync_skills.py --check` clean.
- **Open:** OL-034 (hardware track depends on acceptance, feedback, router and harness) is a standing note; no activated project exists, so nothing needs re-approval.
- **Master issue (2026-10-04, ADR-090):** [#14](https://github.com/henslewm/universal-ai-project-template/issues/14) now carries an owner-approved status section above its unchanged original text, and a ledger comment recording the #11, #12 and #13 closures. It stays open as the historical index; all twelve children are closed.

- **Status:** TEMPLATE FROZEN (ADR-089); no active child. Earlier state, kept as history: records pass on `claude/relaxed-heisenberg-94d1yp` (2026-09-29) for PRs merged since the last handoff: #67 (`cli_colors`, ADR-078), #70 (operator launcher, ADR-077), #71, #83 (civil-rights-nc module, ADR-079, merged with no automated review), #88 (evidence-gap form, ADR-076), #89 and #90 (charter requirements); #91 and #92 merged empty. #84 is fixed on this branch (ADR-080). There are no open PRs on `main` at `6ab49c8`; the branch's draft PR is the records pass. #11 was then the active child with post-merge review, the repeat-dogfood acceptance run and merge outstanding; it was closed as not planned on 2026-10-03 (ADR-089). Earlier state: #9 and #10 closed (PRs #34, #35, #50, #54), lean worker startup (ADR-070, PR #58), ADR-071 to ADR-076 decided
- **Last verified:** 2026-10-04 UTC
- **Active branch:** `claude/relaxed-mayer-f2lqhf` (records for ADR-090)
- **Controlling scope:** [Locked master #14](https://github.com/henslewm/universal-ai-project-template/issues/14); title and order unchanged; status section prepended 2026-10-04 (ADR-090), original text unchanged.
- **Active child:** none. All twelve children of master #14 are closed: #2 to #10 completed; #11 closed as not planned on 2026-10-03 under ADR-089 (legal variants archived, ADR-083; its MVP had merged through PR #83 at `c8a7145`, see OL-024); #12 and #13 deferred under ADR-089. **Last closed:** #11, #12 and #13 on 2026-10-03. #10 (family-law) and earlier have their history in the sections below.

## Verified foundation

Issues #2 through #9 are closed through merged PRs #15 to #34. #9 (complete software + hardware domain template and hardware-in-loop discipline) was accepted through its dogfood at `_acceptance-demo-9b` on 2026-09-14 (11 events, cross-family approval, no waiver, after ADR-026 to ADR-029), then its PR #34 went through 23 rounds of Codex review before a clean result and merge on 2026-09-15 at `d873ec5cd1be503a19880eacbaf9cfba764d9fa5`. Decisions ADR-041 through ADR-055 record every round; `archive/docs/ISSUE_9_VALIDATION.md` holds the full mapping.

#9 delivered the software-hardware domain module (`scripts/software_hardware.py`, `config/domains/software-hardware.schema.json`) that structurally distinguishes a simulated pass (`command`, re-executed by the deterministic gate) from hardware-in-loop or field verification (an operator attestation binding a structured evidence record by digest, never a contract-declared claim). The 23-round review closed a class of gap in the generic acceptance controller that later domain modules should expect too: binding an operator's evidence to exactly the submission it was observed against is several independent checks, not one — the contract's revision and hash, the submitted result's dispatch identity, the artifact's actual identity (not merely a hash a reference-kind artifact can leave at a fixed empty-content value), and the observation's own timestamp bounded on both sides by the current submission and the attestation event. `acceptable()` also now distinguishes replaying an already-accepted ledger's history from justifying a brand-new acceptance today, so a stored decision that rested on since-invalidated evidence keeps replaying as history without letting a *new* decision rest on the same thing.

This is an unactivated reusable template under explicit maintenance authority. No real project registry, provider calls, credentials or permission changes are required. Generated projects should link their generated structured project-state index here and audit it against GitHub; task narration belongs in canonical issue comments.

## Post-#9 follow-up (PR #35, ADR-058)

An independent review of merged `main` after PR #34 found two real defects (ADR-056, ADR-057). PR #35's own review found ADR-057's zero-timeout `receive()` fix incomplete — it reopened the ADR-042 late-arrival hazard from the other direction and left a pre-existing chunked-frame bug unfixed, because no wall-clock/deadline measurement can distinguish "already-buffered data trickling in" from "data that arrived after the poll instant." The fix (ADR-058) adds `Port.available()`, sampled once per zero-timeout `receive()` as a fixed byte budget. A second review round found the sample itself ran outside the `_wire()` close-on-failure guard; both that and a stale documented test count were fixed. Merged 2026-09-16 at `d2350ec` after Codex and an independent reviewer both reported the final head clean.

## Issue #10, session 1 (family-law domain mechanism)

`scripts/family_law.py` and `config/domains/family-law.schema.json` apply the exact
acceptance-controller split #9 built (machine-runnable command vs. non-implementer attestation
bound to a digest-referenced evidence record), registered generically through
`work_packet.DOMAIN_MODULES` with no controller change required. The charter's six fact
categories (VERIFIED FACT, ALLEGATION, DISPUTED FACT, INFERENCE, LEGAL PROPOSITION, UNKNOWN) map
onto `fact_basis`/`fact_assertions` the same way #9's hardware status does: `VERIFIED_FACT` is
earned in the ledger, never authored in a contract. `adverse_authority` (required for any
`LEGAL_PROPOSITION` assertion) has no software-hardware precedent. One genuine addition beyond
the hardware mirror: `status` reports a third earned outcome, `CONTRADICTED_BY_SOURCE`, because
unlike a hardware pass/fail a primary source can legitimately contradict the claim it was
consulted to check — surfaced ahead of every other reason rather than read as merely unverified.
`DOMAIN_FIELDS["family-law"]` was expanded from 3 thin fields to the 10 the charter requires, kept
synchronized across the validator, `config/bootstrap.schema.json`, and the intake reference from
the start (applying #9's ADR-040 lesson proactively rather than discovering the drift later). See
ADR-059 and the design comment on Issue #10 for the full mechanism.

## Issue #10, session 2 (repeat-dogfood acceptance run)

Ran the repeat-dogfood exercise on `_acceptance-demo-10` (outside this repository), matching `_acceptance-demo-9b`'s shape: `INIT`, `CHECKS`, then successive `REVIEW_OPEN`/`REVIEW_RESULT`/`RESUBMIT` rounds. Round 1 (fresh same-family Claude subagent) found `AC-DECOMPOSITION` overclaimed — only one of the four example packets' commands had actually been run through the gate; fixed by a regression that runs all four (commit `f47a43d`). Round 2 (cross-family Codex) returned `REJECT_BOUNDED` on `AC-PROVENANCE` and `AC-ADVERSE`: `record_problems` accepted any nonblank `claim_verified` rather than one matching a declared assertion, and the revision/contract-hash binding lived only in the record-basis `status --evidence-dir` path, so the default attestation-only path could earn `VERIFIED_FACT` unbound. Fixed via ADR-060 (commit `29422ca`); post-fix checks passed cleanly (398 tests, `validate_project.py` OK, 0 payload diffs).

Round 3 (cross-family Codex, the third and last review `max_review_attempts=3` permits) returned `REJECT_BOUNDED` again — this time genuinely unresolved and not yet corrected. See ADR-061 for the full finding: `AC-ADVERSE` is still unmet because a `LEGAL_PROPOSITION` assertion requires nonempty `adverse_authority` but never requires a `primary_source_verified` validation to exist, so FAM-04-issue-brief validates with only a citation-linked check; separately, the reviewer flagged that this session's own closeout-document updates fall outside the dogfood packet's declared `scope.allowed`. The report's `scope`-kind finding could not be ingested as written (`failed_ref` must be a literal string from `contract.scope`, not the reviewer's shorthand), so `_acceptance-demo-10`'s ledger stops at event 12 — a dispatched round-3 review with no recorded verdict — and `reviews_used` is already at `max_review_attempts`.

Separately, this session discovered a second, unattended Codex CLI session (`--ask-for-approval never`) independently working Issue #10 in the same checkout; its edits collided with this session's, it briefly wrote a draft `APPROVE` report before correctly reconciling to the same `AC-ADVERSE` rejection, and it committed a "checkpoint" (`d2c67dd`) before it could be stopped. That commit was discarded by revert (`95446eb`, unpushed branch); see ADR-062. Also fixed this session: `scripts/sync_skills.py --check` was found failing (drift in the gitignored `skills/complex-project-bootstrapper/assets/project-template/.claude/settings.local.json` mirror) and fixed by rerunning `sync_skills.py`; no tracked file changed.

## Issue #10, session 3 (2026-09-27)

After `main` was merged into the branch (`a638098`), round 3's AC-ADVERSE gap was fixed in `cecd714` (ADR-065). A packet declaring a `LEGAL_PROPOSITION` must now also map a validation to `primary_source_verified`, and FAM-04 declares one. With 399 tests passing, the dogfood contract was revised to revision 2, which adds the standing closeout records to `scope.allowed`. It is reviewed on a fresh ledger, `_acceptance-demo-10b`, because the acceptance ledger has no revision event and `-10`'s budget is spent. `-10` stays preserved as provisional.

**Accepted 2026-09-27:** `_acceptance-demo-10b` is `ACCEPTED` in 5 events (head `472d2a60`). The deterministic gate passed (399 tests), and round 1 (cross-family Codex, tier 3) approved every criterion, with no waiver. `docs/ISSUE_10_VALIDATION.md` holds the full record.

**PR #50:**
- Codex round 1: fixed, ADR-066.
- Codex round 2: fixed, ADR-067.
- Codex round 3: two findings.
  - P1: a source verification record was not bound to a declared contract source. Fixed by ADR-068: assertions declare `verified_by` sources, and each record names its `source_id`.
  - P2: stale records, swept across the control files.
- Round 4 (on `7ff2158`, the one extra round the maintainer authorized) found one P1: coverage is keyed by assertion text, so duplicate-text entries share one record. The maintainer merged as is, and it was then fixed under [#53](https://github.com/henslewm/universal-ai-project-template/issues/53) by ADR-069 (PR #54, merged at `dff35e0` after a clean Codex review).

**Merged 2026-09-27** at `620fc9a` (pinned to the reviewed head `7ff2158`; CI passed). #10 closed with a completion comment, and master #14 was noted.

## Merged 2026-09-27: PR #48 and PR #45

- **PR #48** (merged at `59f194e`) restores the Mistral Vibe platform files (`MASTER_MISTRAL.md`, `.mistral/*`, `instructions/profiles/mistral_high_synthesis_INSTRUCTIONS.md`, plus payload mirrors), which were lost when `main` was rewritten. Codex round 1 found that the offline knowledge set and startup reads omitted `FACTS_AND_ASSUMPTIONS.md`/`RISK_REGISTER.md`; this was fixed in `059ff61`. Round 2 asked for `RISK_REGISTER.md` in the startup reads; this was declined under ADR-063 because the canonical startup protocol does not require it. The files are present but not yet wired in; follow-ups are [#46](https://github.com/henslewm/universal-ai-project-template/issues/46) (authority order, validator, README, bootstrapper) and [#47](https://github.com/henslewm/universal-ai-project-template/issues/47) (verify product claims; master #14 scope decision).
- **PR #45** (merged at `a35b89d`) adds the scope policy (ADR-063): a review finding is actionable only when it names a concrete defect the change introduced or exposed, or a demonstrable failure of an explicit applicable requirement. It merged after a clean Codex review of head `5647fa9` with all 8 inline findings answered.
- On the combined `main`, 361 tests pass and `validate_project.py` passes with 81 required paths.

## Continuation

#9 is closed; its completion comment (and `HANDOFF_CURRENT.md`) name the limitations carried forward (OL-016's template-packaging defects remain open from #8's closure, unaddressed by #9). #10 is closed through merged PR #50, and its one known gap is fixed by #53 (PR #54). Next, a new session takes the rescued worker-startup work in draft PR #55, then returns to master #14 to select #11. The post-merge branch audit is in `HANDOFF_CURRENT.md`: one unreviewed branch (`codex/automatic-worker-startup`) was preserved from uncommitted work, and the pre-rewrite branches await the maintainer's cleanup decision. Do not run a second unattended agent against this same branch/task concurrently with an interactive session (ADR-062); if another automated session may be working this repo, check running processes before assuming sole ownership of the working tree. Model-performance calibration remains #12 and should receive #7's run-4 profile, #8's review-economics observations, and #9's 23-round review-economics figures once gathered. Continue one child at a time. Do not edit the locked master or delete construction branches outside the later authorized cleanup.

## Records pass (2026-09-29)

- **Verified on this branch:** 621 tests pass (3 skipped), `validate_project.py` passes (84 required paths), `sync_skills.py --check` reports 0 differing files. The bootstrap gate is intentionally inactive here (template-maintenance mode).
- **#84 fixed (ADR-080):** `scripts/family_law.py` now refuses a legal proposition whose `verified_by` is not exactly its own authority, and an allegation that lists its own filing. Two regressions failed on the previous code first. It closes when its PR merges after an automated review of the exact head (ADR-074).
- **civil-rights-nc (#11):** the module merged at `c8a7145` with CI green and no automated review (ADR-079). `templates/civil-rights-nc/PROFILE.md` now documents the mechanism. Still open: an automated review of the merged code scoped to high-impact bugs, the repeat-dogfood acceptance run with a non-Claude reviewer (this repository cannot supply one), and the maintainer's merge go-ahead. Nothing here claims #11 is accepted.
- **Charter:** items A-D and F, gaps E and G, and question 2 stay open (OL-028). The owner said on 2026-09-29 that the combined ledger was decided in an earlier session, but no record in this repository states that decision.
- **Not done in this pass:** #12 and #13 (telemetry, dry runs), the stale forward-reference sweep (OL-027) and the review of PR #67's last two commits (OL-026).
