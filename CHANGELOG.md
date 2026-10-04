# Changelog

## 2026-10-04 — Master issue #14 status section (ADR-090)

- With the owner's interactive approval, a dated status section was prepended to the body of the locked master issue #14: ADR-089 freeze, legal variants archived (ADR-083), all twelve children closed, the shipped items from the "not yet complete" list, the two-track definition of done, and the standing review rules. Original text, title and order unchanged. A ledger comment records the #11, #12 and #13 closures.
- Records: ADR-090; OL-004, OL-005 and OL-024 closed; SRC-002 re-verified; the stale active-#11 lines in `PROJECT_STATE.md` retired (Codex finding on PR #109).

## 2026-10-03 — Freeze at the software and hardware tracks (ADR-089)

- Owner decisions: review cap of 4 (rule added to `MASTER_INSTRUCTIONS.md`), worker-attempt default 2 (recorded only), approvals unchanged, no combined ledger, no automatic delegation, savings telemetry deferred. ADR-084 to ADR-088 withdrawn. The charter's decision sections are rewritten accordingly. No project is activated, so nothing needs re-approval.
- The generated charter now says "business choices" and labels the field "Version".

## 2026-10-03 — Draft ADR-084 to ADR-088 for charter decisions A-D and F

- Proposed, not in force: review cap (A), worker attempts (B), approvals and action ledger (C), single ledger and settings file (D), automatic delegation (F). Each awaits owner sign-off; the current rules still apply. Open owner questions are listed in each row, including question 2 for D.

## 2026-10-03 — Trim to software and hardware tracks (ADR-083)

- Legal profiles archived to `archive/legal/` and no longer served. `scripts/worker_launcher.py` and `scripts/github_ledger.py` removed (supersedes ADR-077, the launcher part of ADR-073, and the GitHub-ledger ADRs).
- The payload mirror `skills/complex-project-bootstrapper/assets/project-template` is no longer tracked; `scripts/sync_skills.py` and CI build it before tests.
- Software-only projects use the `software-hardware` profile, with `--no-hardware` selecting the `web-ui` track (satisfies ADR-082's web-ui bootstrap item).
- Bound documents changed, so an activated project needs re-approval. PLATFORMIO and profile cleanup.
- Commits on `claude/trim-to-sw-hw-tracks`: `53de2db`, `ac371d3`, `0bfd28a`, `d58473a`, `3b63fe6`.
- Verified: 434 tests with 2 expected Windows-only failures (exec-bit tests in `tests/test_sync_skills.py`); `validate_project.py` passes with 81 required paths; tracked lines about 43k, down from about 92k.

## 2026-10-01 — Mistral Vibe CLI settings

- `.vibe/config.toml` sets `default_agent = "default"` and `[tools.bash] permission = "ask"`; `MASTER_MISTRAL.md` gains a Vibe CLI section; `validate_project.py` requires the file. Keys are from the official configuration page; nothing beyond them is set.

## 2026-09-30 — Four tracks, first slice (ADR-082)

- `instructions/tracks/` holds `hardware`, `family-law`, `civil-suit` and `web-ui`. A generated project's `CLAUDE.md` now imports its own track only (hardware for `software-hardware`, civil-suit for `civil-rights-nc`). `validate_project.py` requires the four files.
- `.claude/rules/05-modular-code.md` and `06-platformio.md` load only when firmware paths are touched.
- Not done: charter and `MASTER_INSTRUCTIONS.md` slimming (bound documents), a `web-ui` bootstrap profile, non-Claude platform track loading, SatLink3 content. See ADR-082's Status.

## 2026-09-30 — Archive old decisions and changelog entries (ADR-081)

- ADR-000 to ADR-069 (except ADR-006, ADR-062, ADR-063) moved verbatim to `archive/DECISIONS_ARCHIVE_ADR-000-069.md`; `DECISIONS.md` now opens with an index of all 82 ADRs. Changelog entries before 2026-09-27 moved verbatim to `archive/CHANGELOG_ARCHIVE_2026-08-29_to_2026-09-23.md`.
- `scripts/validate_project.py` requires both archive files. No content edited; the track split is not part of this change.
- PR #99 merged at `7329030` at the maintainer's instruction with no Codex review on its final head `ce05374` and CI still running; see ADR-081's Status. Codex's P1 (generated projects must not carry template archives), P2 (empty archives) and P2 (truncated `SECURITY.md`, restored in the root file) were answered in `ebfc631`, `0156187` and `ce05374`.

## 2026-09-29 — Records pass for PRs #67, #70, #83 and #88 to #92; #84 fixed (ADR-077 to ADR-080)

- ADR-077 (launcher, PR #70), ADR-078 (`cli_colors`, PR #67) and ADR-079 (civil-rights-nc, PR #83) are recorded from their PR descriptions and the #11 comment, with SRC-033 to SRC-036. PR #83 merged without an automated review; that is stated in ADR-079, and its post-merge review is still open.
- #84 (ADR-080): a `family_law` legal proposition's `verified_by` must be exactly its own authority, and an allegation may not list its own filing. Two regressions were shown failing first; the four family-law example packets already comply. Only new contracts are refused.
- `templates/civil-rights-nc/PROFILE.md` gains an appended mechanism, verification-ladder and known-limits section.
- PRs #91 and #92 ("[WIP] Copilot Request") merged with only "Initial plan" commits and no file changes. PRs #72 and #78 were closed unmerged.
- 621 tests pass (3 skipped); `validate_project.py` passes with 84 required paths; `sync_skills.py --check` reports 0 differing files.

## 2026-09-28 — #87: evidence-gap issue form hardened against placeholder reports (ADR-076)

- `.github/ISSUE_TEMPLATE/evidence-gap.yml` now tells a reporter to stop and open or update a blocker instead if they cannot yet identify the canonical task, master issue, packet binding, and blocked criterion.
- The form explicitly rejects placeholder text such as `Blocker`, `unknown`, or “I am not sure what the problem is,” and now ships concrete placeholders for the packet binding, provenance/search history, verification requirement, and next owner.
- `tests/test_validate_project.py` adds a regression that locks in the new anti-placeholder guidance; `sync_skills.py` propagated the same update into the generated-project payload mirror.

## 2026-09-28 — PR #71: CLI exit codes and Ctrl+C → 130 (#32, #31; ADR-075)

- README "CLI exit codes" lists every command's 0/1/2 outcomes and the 130 behavior; the protocols point to it. No existing outcome changed code (ADR-072).
- Every `scripts/*.py` command line routes through `scripts/cli_exit.py`: Ctrl+C exits 130 with no traceback, including while a command is still loading.
- `acceptance.py run-checks` stops the check's whole process tree before reporting an interrupt, and refuses (exit 1) if it cannot confirm the tree stopped.
- Ledger creation, ledger events and new output files are written whole under Ctrl+C.
- Merged at `bb0e629` after seven Codex rounds (five with findings, each fixed with a regression; the last clean). 491 tests pass.

## 2026-09-27 — PR #63: PlatformIO example shipped with the software-hardware template

- `templates/software-hardware/platformio.example.ini` is an Arduino-ESP32 2.0.x (espressif32 6.9.0) variant for the ESP32-S3-DevKitC-1 N16R8. It conforms to `docs/PLATFORMIO.md`: an exact pin, an app-partition `maximum_size`, quiet `dev`/verbose `debug`/silent `release` environments, and the arduino-cli equivalent. It replaces the untracked root `platformio.ini`.
- Merged at `fd4c20d`. Codex was out of credits, so CodeRabbit reviewed under ADR-074; its one finding (the missing arduino-cli equivalent) was fixed in `c01cf10` and verified by CodeRabbit.

## 2026-09-27 — Merge rule accepts Codex or CodeRabbit reviews (ADR-074)

- Codex's review quota ran out during PR #61. The merge rule now accepts an automated review by Codex or by CodeRabbit on the exact head; request one with `@codex review` or `@coderabbitai review`. ADR-063's actionability test applies unchanged.

## 2026-09-27 — #49: template packaging fixes (ADR-071)

- The CI workflow runs the payload-drift check only when `skills/complex-project-bootstrapper/assets/project-template` exists. Generated projects, which inherit the workflow but have no payload, skip it and still run validation and tests.
- `sync_skills.py --check` reports mirror files that no longer have a source, and a sync removes them. It excludes `.git` and the other excluded names as files too, so a worktree's `.git` pointer is never copied into the payload.
- A generated project gets a fresh `DECISIONS.md` (ADR-000 only), and the template's own `docs/ISSUE_*_VALIDATION.md` and `docs/WORKER_STARTUP_VALIDATION.md` are not copied into it. The other records were already regenerated. In-place generation also removes the payload folder.
- Scope: the sync keeps mirrors equal to their sources for regular files and directories. It removes links without following them and refuses to run through a linked destination. It never reads a wrong-type or linked entry at a target, and writes each file with a temporary file plus `os.replace`, so hard links are replaced rather than written through (#62).

## 2026-09-27 — Triage decisions: exit codes (ADR-072) and launcher boundary (ADR-073)

- ADR-072 (#32): exit codes are 0 OK, 1 handled refusal, 2 not-OK outcome (usage error, domain stop/hold, or unreadable bootstrap file, told apart by the JSON `status`), 130 interrupted. Nothing is reclassified; implementation stays under #32 and #31.
- ADR-073 (#25): the only launcher is an operator-run `launch` command for one reserved attempt, with a scoped runtime credential environment. `dispatch` stays preparation-only and no controller launches. This unblocks #36, #37, #40 and #41.
- #49's CI decision stands as ADR-071 (one workflow; the payload check skips without a payload), recorded in PR #61.

## 2026-09-27 — #23: worker reports are schema-checked in both entrypoints

- `report_valid` now applies the controller's own result schema (`feedback.shape("result", ...)`) before it reads any nested field. `verify-report` therefore refuses what `ingest` already did: string Booleans, invalid outcomes, negative costs, and missing or extra nested fields. A refused report leaves the attempt pending.

## 2026-09-27 — #56: PlatformIO firmware snippet compiles as a `.cpp` module

- The build-identity snippet in `docs/PLATFORMIO.md` now includes `Arduino.h` and `esp_arduino_version.h`. It is now split into a `build_identity.h`/`.cpp` module plus the `.ino` caller that includes the header. Arduino's `.ino` preprocessing (includes and prototypes) does not reach a `.cpp` file, so `Serial` and `ESP_ARDUINO_VERSION_STR` are declared explicitly, and `setup()` can see `printBuildIdentity()`.

## 2026-09-27 — PR #58 merged (ADR-070); PR #55 closed

- PR #58 merged at `6c24d03`. Codex round 1 found a governing document could be listed in `worker_instructions`, and round 2 found a hard link or copy could reach the same text. Both were fixed by refusing any instruction whose content digest matches a governing document. Round 3 was clean. 419 tests pass.
- PR #55 was closed unmerged with a pointer to #58 (OL-020 closed).

## 2026-09-27 — Lean automatic worker startup (ADR-070)

- Every new worker brief (schema `1.1`) embeds the bounded worker rules and only the instruction files its contract's new optional `worker_instructions` names, capped by `limits.startup_max_chars` (default 12000). Governing documents travel as path-plus-digest references, not text.
- Missing, unsafe, credential-like or oversized sources refuse dispatch before an attempt is reserved. The rules are counted once in the capacity check, and the example Cline argv passes only `{brief}`. Exact legacy `1.0` briefs remain verifiable.
- This supersedes draft PR #55, whose full governance bundle (~71k characters) would have refused every local-model dispatch. A regression now checks that the real rules fit the example 16384-token local binding.

## 2026-09-27 — Post-#10 housekeeping

- PR #54 (#53, ADR-069) merged at `dff35e0` after a clean Codex review.
- The rescued worker-startup work is in draft PR #55, and its worktree moved to `../uapt-worker-startup`.
- Obsolete branches were identified for deletion. The command is in the handoff for the maintainer to run.

## 2026-09-27 — #53: family-law assertion text is unique per contract (ADR-069)

- `validate_contract_domain` refuses two `fact_assertions` entries with the same text. Coverage is keyed by claim text, so duplicates let one record cover an entry whose verifying source was never read (PR #50 round-4 finding).

## 2026-09-27 — Issue #10 closed: PR #50 merged

- PR #50 merged at `620fc9a` after 4 Codex rounds. Round 4's one finding (coverage keyed by assertion text) was deferred to #53 at the maintainer's decision. #10 closed with a completion comment.
- Post-merge branch audit: uncommitted Codex work in the `codex/automatic-worker-startup` worktree was committed as-is and pushed so it is not lost (unreviewed; OL-020). The pre-rewrite branches were recorded for cleanup (OL-021). No branch was deleted.

## 2026-09-27 — Issue #10 session 3: AC-ADVERSE fixed; repeat review at contract revision 2 (ADR-065)

- A family-law packet declaring a `LEGAL_PROPOSITION` must now map at least one validation to `primary_source_verified`; adverse authority alone no longer suffices. FAM-04 declares the rung, `PROFILE.md` states the rule, and a regression covers it (399 tests).
- The dogfood contract's `scope.allowed` now admits the standing closeout records required by the closeout protocol. It is re-reviewed on a fresh ledger, `_acceptance-demo-10b`, and `_acceptance-demo-10` is preserved as provisional.
- `_acceptance-demo-10b` was accepted: the deterministic gate passed, and a cross-family Codex review approved all five criteria. `docs/ISSUE_10_VALIDATION.md` records the whole review history.
- PR #50 Codex round 1: a packet asserting `DISPUTED_FACT` or `LEGAL_PROPOSITION` must now have `model_review` in its acceptance floor, as `PROFILE.md` already stated (ADR-066). The handoff is updated to the accepted state.
- PR #50 Codex round 3 (ADR-068): each family-law fact assertion now declares `verified_by`, the sources whose review can verify it, and a legal proposition must list its own authority. A source verification record names the declared `source_id` it reviewed. A record of an undeclared source verifies nothing, and a record covers its claim only when its source is in that claim's `verified_by`. The stale current-state text was swept across the control files.
- PR #50 Codex round 2 (ADR-067): a re-verified `CONTRADICTED_BY_SOURCE` now outranks an unrelated check's record problem, which stays in the reason, and an `UNKNOWN` assertion can never be covered into `VERIFIED_FACT`. The earned-status precedence is recorded as one rule.

## 2026-09-27 — Mistral Vibe platform files restored (PR #48); scope policy merged (PR #45)

- Restored the additive Mistral Vibe (Le Chat) platform files lost when `main` was rewritten: `MASTER_MISTRAL.md`, `.mistral/PROJECT_INSTRUCTIONS.md`, `.mistral/PROJECT_KNOWLEDGE.md` and `instructions/profiles/mistral_high_synthesis_INSTRUCTIONS.md`, with their payload mirrors. Their startup and offline lists now include `FACTS_AND_ASSUMPTIONS.md`, and the offline set includes `RISK_REGISTER.md`. They are not yet wired into the authority order, validator, README or bootstrapper (#46), and their product claims are unverified (#47).
- Merged the 2026-09-23 scope policy (ADR-063, entry below) through PR #45.
- ADR-064: Mistral Vibe support is in scope under master #14. OL-016's packaging defects are now issue #49, with a fourth defect added: `sync_skills.py` treats a worktree's `.git` file as payload.

Older entries (2026-08-29 to 2026-09-23) are archived verbatim in `archive/CHANGELOG_ARCHIVE_2026-08-29_to_2026-09-23.md`.
