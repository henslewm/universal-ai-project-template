# Changelog

## 2026-10-10 — First cloud worker launch (OL-036)

- Ran the worker launcher end to end on Windows against Mistral Devstral Medium through Cline: one attempt refused for brief tampering and abandoned, a fresh-task retry `REPORT_WRITTEN` and ingested; independent checks found the work not acceptable. OL-041 opened; SRC-040 and SRC-041 added; state and handoff updated.

## 2026-10-09 — Local models dropped (ADR-100)

- Owner direction after the first real Windows launch failed on a local 27B (attempt 1 killed for low memory; attempt 2 `TIMED_OUT` with no report): workers are cheaper cloud models only.
- `PROJECT_CHARTER.md`, `config/project.json` and `config/bootstrap.json` drop "or local models" from the goals; `AUTONOMY_CONTROL_PLANE.md` maps T0/T1 to cloud models; `MODEL_ROUTING.md` and `EXECUTION_HARNESS_PROTOCOL.md` say to bind cloud resources only; `prompts/PROVISION_LOCAL_MODEL.md` deleted; OL-011 and OL-015 closed.
- Code, tests and the disabled example configurations keep their LM Studio fixtures. The bootstrap package was re-reviewed and awaits the owner's `activate`.

## 2026-10-09 — Architect runs the worker launcher (ADR-099, OL-036)

- `MASTER_CLAUDE_CODE.md` → Delegation: the sentence keeping external-harness dispatch operator-run "until a separate decision (OL-036)" now says the architect session runs `scripts/worker_launcher.py` itself under ADR-099 and subagents do not. Owner-directed edit.
- `HANDOFF_CURRENT.md`: the #128 sentinel-store P2 is recorded as fixed by #132; the next action is the first real launch, after a local model server and harness are installed on the Mac; notes on the macOS `TMPDIR` symlink failure in the launcher tests and the missing `jsonschema`.

## 2026-10-08 — Stale PRs #118 and #119 closed (OL-040)

- The owner left OL-040 to Claude's judgement. PR #118 (`claude/workflow-skills`: claims ADR-096, outside the ADR-096 milestones, conflicts with `main`) and PR #119 (handoff draft superseded by PR #120's records) were closed unmerged with a comment each; both branches are kept.
- `OPEN_LOOPS.md` moves OL-040 to Closed; `PROJECT_STATE.md` drops it from the open items, and `HANDOFF_CURRENT.md` drops the "merge #127" next action.

## 2026-10-08 — Launcher keeps its one-launch marker (PR #124 post-merge Codex P1)

- `scripts/worker_launcher.py`: once the harness tree is stopped, `launch` checks that `launch.json` is unchanged; if the worker deleted or edited it, the launcher restores it and refuses the run for `abandon`, so the same reservation cannot be launched twice. Regression `test_a_harness_that_deletes_the_launch_marker_cannot_be_launched_again`, shown failing first.
- PR #126 Codex round 1: a worker that deleted `launch.json` and kept running still let a concurrent second `launch` start. The exclusive guard is now `<ledger>.launched/<dispatch_id>.json`, beside the ledger where the worker is never directed; `launch.json` stays as evidence. Regression `test_a_marker_deleted_by_a_running_harness_does_not_admit_a_second_launch`, shown failing first (the second launch started the harness). `EXECUTION_HARNESS_PROTOCOL.md` updated.
- PR #126 Codex round 2: the guard store is `.<ledger>.launch-guards/` beside the resolved ledger, so a symlinked ledger path names the same guard, and a directory there without the launcher's `LAUNCH_GUARD_STORE` file (such as another ledger) is refused, never written. The post-run check never opens a FIFO or other special file left as the marker. Any failure writing the marker removes the guard, so a launch that never started does not spend the reservation. Four regressions, each shown failing first. A marker replaced by a hard link is unlinked and recreated, never written through, so the linked file keeps its content (a later Codex finding on #126, regression shown failing first).
- PR #128 Codex: a guard store whose `LAUNCH_GUARD_STORE` file could not be written is removed again, so it no longer refuses every retry. Regression shown failing first.
- The P2 finding (an `abandon` from another session between the ledger recheck and process start) is declined: it needs two writers on one ledger (ADR-062), and a lock would change frozen `feedback.py` (ADR-098).

## 2026-10-08 — Worker launcher restored for the architect (ADR-099, OL-036)

- `scripts/worker_launcher.py` and `tests/test_worker_launcher.py` restored from `53de2db^`; only wording changed. The 27 tests pass unchanged against the current harness, and no frozen file (ADR-098) changed.
- `EXECUTION_HARNESS_PROTOCOL.md` regains the launcher section: the architect session may run `launch`, paid resources included, within the per-packet budget and attempt limits; a wrapper path for harnesses that need more environment; an automated caller runs `launch` as a background task or with `--timeout-seconds` below its own timeout.
- `.claude/rules/04-permissions.md` and `AGENTS.md`: a metered launch within those limits needs no further prompt only where `DECISIONS.md` records the owner's direction. `docs/REFERENCE.md` regains the launcher's exit-code row; `SOURCE_INDEX.md` SRC-033 points at the renamed section.
- ADR-099; R-019 to R-021 are live; R-022 added.

## 2026-10-08 — Freeze shipped milestones (ADR-098)

- `DECISIONS.md` ADR-098: Records current and Unknown-cost state are frozen, and Auto-closeout joins them when PR #116 merges. Frozen work takes reproduced-defect fixes only; other review findings on it are declined.
- `AGENTS.md` gains "Review guidelines" for Codex's reviewer: report only findings that pass the ADR-063 actionable test, and only defects on frozen work.

## 2026-10-08 — Automatic closeout (ADR-094)

- `scripts/closeout.py`: `push`, `ready`, `merge`, `issue`, `sync-loops` (from the 2026-10-07 WIP on PR #116); `ready` now also counts a clean Codex round from its Completed summary row. PR #116 review round 1: the cap is enforced even on a reviewed head and counts every round; more than 100 threads, a changes-requested review of the head, or a cross-repository pull request refuse; git, gh and test calls time out; `sync-loops` creates a missing Closed table; an issue URL is matched rather than assumed. Round 2: `merge` deletes the branch only after GitHub reports the pull request merged, so a queued merge keeps its branch. Round 3: rerun after a queued merge lands, `merge` only cleans up, and keeps a branch that moved past the merged head; `validate_closeout` checks all 19 force-push, hard-reset and recursive-delete denies, and treats a Bash or PowerShell rule as a gate when its `*` wildcards, trailing `:*` or bare tool name match a closeout command. Also fixed: a review bot's thread reply, filed as an empty COMMENTED review on the then head, no longer counts as a review round or as a review of that head. An independent review of `4dae8f2` found two defects, fixed: the cleanup never deletes a protected head branch, and a rule naming a closeout command gates it whatever arguments it pins. Round 4: `ready` runs the validator and the suite with stdin closed, so an inherited pipe or terminal cannot stall a CLI test into a false failure; the branch-delete race finding was declined with the owner's agreement.
- `MASTER_INSTRUCTIONS.md` gains "Automatic closeout (ADR-094)"; closeout step 9 and the merge rule point at it; `.claude/rules/02`, `.claude/rules/04` and `AGENTS.md` point at it too.
- `OPEN_LOOPS.md` mirrors issues from OL-041; generated projects from OL-004. `validate_project.py` gains `validate_closeout`; `docs/REFERENCE.md` gains the exit-code row; `tests/test_closeout.py` (26 tests).
- `.claude/settings.json`: the ADR-091 `ask` block is removed by the owner on `main` (`fcfecf8`; an agent may not edit its own permissions); every deny stays.

## 2026-10-08 — Unknown-cost state (ADR-097)

- `scripts/execution_harness.py` and `scripts/feedback.py`: `abandon` writes a distinct `ABANDON` event recording `api_cost_usd: null` (unknown) when the routed resource was metered at dispatch, 0 when it was not; `complete` and worker reports refuse `null` (PR #122 Codex round 1); an `ABANDON` event must have the fixed no-report shape, so it can never pass (round 2).
- `scripts/model_router.py` and `scripts/feedback.py`: only known costs are summed; an unknown cost on a metered resource bars every metered candidate (`PRIOR_API_COST_UNKNOWN`), across contract repairs too; zero-priced resources stay eligible; a past attempt is never re-classified from current prices.
- `config/feedback.schema.json`, `config/model-router.schema.json`: `api_cost_usd` accepts `null`. Protocol docs updated (`EXECUTION_HARNESS_PROTOCOL.md`, `FEEDBACK_PROTOCOL.md`, `MODEL_ROUTING.md`). Regressions shown failing on the earlier code.

## 2026-10-08 — Template activated; records current (ADR-096)

- PR #120 merged to `main` at `7f04c75`; the owner activated the bootstrap package (commit `72ff167`, approved_at 2026-10-08T14:29:43Z) and `validate_bootstrap.py config/bootstrap.json --require-active` passes.
- `PROJECT_STATE.md`: new current section for the activated template; the 2026-10-07 retrofit section is now history with its Status marked as history.
- `OPEN_LOOPS.md`: OL-038 closed; OL-040 opened for PR #118 (ADR number collision, conflicts, outside the approved milestones) and PR #119 (superseded).
- `HANDOFF_CURRENT.md` rewritten; next milestone is Unknown-cost state.

## 2026-10-07 — Bootstrap retrofit of the template (ADR-096)

- `config/bootstrap.json` and `BOOTSTRAP_REVIEW.md` added; `bootstrap_gate.py review` reached `AWAITING_APPROVAL`. Autonomy stays OFF until the owner runs `bootstrap_gate.py activate`.
- `scripts/bootstrap_project.py`: a repository created from the GitHub template inherits the template's `config/bootstrap.json`; in-place tailoring of a `template_mode` copy replaces it only with the new `--replace-template-state` opt-in (Codex round 1 P1), and the in-place commands in `docs/GITHUB_PUBLISH.md`, `prompts/BOOTSTRAP_NEW_PROJECT.md`, `prompts/INTERACTIVE_BOOTSTRAP.md`, `BOOTSTRAP_PROTOCOL.md`, `START_HERE.md` and the bootstrapper `SKILL.md` say so (Codex round 2 P2 found `START_HERE.md` missed). Every other existing bootstrap state is still refused. Regressions `test_bootstrap_state_outside_template_root_still_refused` and `test_in_place_without_opt_in_keeps_template_state` (shown failing on the earlier code) added.
- `config/project.json`: template placeholders replaced with the template's own values; `template_mode` stays true.
- `PROJECT_CHARTER.md`: risk low, sensitivity public, and the ADR-096 owner decisions (OL-036 yes, finish ADR-094, unknown-cost fix, #12/#13 deferred, no features beyond requirements).
- `scripts/bootstrap_gate.py`: `update_project_status` now changes only the `## Current` section's Status line (whole file if there is none), so activation updates the startup view and never rewrites history; `PROJECT_STATE.md`'s current section gains the Status line it updates (Codex round 3 P2). Regressions in `tests/test_bootstrap_gate.py`, shown failing on the earlier code.
- `PROJECT_STATE.md`: the current section's Gate, Verified and Open lines and its heading no longer restate the pre-activation state, so the Status line is the only live gate field and activation leaves no contradiction (Codex round 4 P2). Regression `test_activation_leaves_no_stale_gate_state_in_template_view`, shown failing on the earlier text.
- Records: ADR-096; OL-036 closed; OL-037 (fresh-clone payload) and OL-038 (activation) opened; R-019 to R-021; stale "PR #117 pending" and "next ADR 095" corrected. The review command's rewrite of the historical `Status` line in `PROJECT_STATE.md` was reverted.

## 2026-10-07 — Records after the PR #110 merge (ADR-093); record-keeper gets Bash (ADR-095)

- `.claude/agents/record-keeper.md`: `Bash` added to its tools, on the owner's instruction, so it runs `validate_project.py` and `git diff --stat` before reporting; its instructions limit the shell to those checks and read-only git commands. ADR-095 records it; ADR-094 is skipped because unmerged branch `claude/auto-closeout` has claimed it.
- `PROJECT_STATE.md` current section: the active-branch bullet now records PR #110 merged by the owner at `ed30f33` (head `0fb220d`) after five Codex rounds, the fifth unintended and past the ADR-089 cap, with PR #115 following; the verified bullet points at this date's changelog entry.
- `DECISIONS.md`: the full ADR-093 row's status now states the five rounds and the merge with head `0fb220d` unreviewed. No other row changed.
- `HANDOFF_CURRENT.md`: merge recorded, no queued work, and two notes: never quote the Codex trigger phrase in a PR comment, and branch `claude/auto-closeout` holds unfinished ADR-094 work, so the next decision takes ADR-095 or later.

## 2026-10-07 — Require docs/REFERENCE.md in the validator (ADR-092 follow-up)

- PR #114 moved the reference material to `docs/REFERENCE.md`; `scripts/validate_project.py` (with its `.agents`, `.claude` and payload copies, converged by `sync_skills.py`) now lists `docs/REFERENCE.md` in `REQUIRED`, so a checkout or generated project missing the moved reference fails validation. Regression added in `tests/test_validate_project.py`. No new ADR: this enforces the ADR-092 layout.

## 2026-10-07 — Unfreeze for startup views and delegation (ADR-093)

- Authored 2026-10-06 as ADR-091 and renumbered ADR-093 when main was merged in, because main had taken ADR-091 (ask rules, PR #111) and ADR-092 (fewer copy/pastes, PRs #113 and #114).
- Owner direction: unfreeze the template to reduce drift and auto-delegate tasks. The startup protocol now reads validator-checked views: the `## Current (date)` section of `PROJECT_STATE.md`, the `## Open` table of `OPEN_LOOPS.md` and the `## Index` of `DECISIONS.md`. `validate_project.py` gains `validate_record_views` (current date not older than the changelog, no closed loop in the open table, unique IDs, index and full rows agree), with eight regression tests. Its first run caught the state section a day behind the changelog.
- Full rows ADR-070 to ADR-090 archived verbatim to `archive/DECISIONS_ARCHIVE_ADR-070-090.md`; `OPEN_LOOPS.md` split into open and closed tables; `bootstrap_project.py` writes the same formats into generated projects.
- Duplicated rule text replaced by pointers in `CLAUDE.md`, `MASTER_CLAUDE_CODE.md`, `AGENTS.md` and `.claude/rules/02`; the work-packet, connector and skill sections of `MASTER_INSTRUCTIONS.md` now point at their protocol files; the web and Mistral masters name the views.
- Delegation: `.claude/agents/` carry model tiers (sonnet for researcher, operator and record-keeper; the reviewer inherits the architect tier) and bounded-outcome reports; `MASTER_CLAUDE_CODE.md` → Delegation makes delegation the default for bounded work. External harness dispatch stays operator-run pending OL-036.
- Records: ADR-093; charter definition of done and decision F updated; OL-036 opened; R-001 updated, R-017 and R-018 added; SRC-038 and SRC-039.
- Codex round 1 on `2c019e2` (three P2 findings, all fixed): the generated project's status, last-verified, branch and objective fields now sit inside the `## Current` view; a view heading that appears twice is rejected instead of silently replacing the earlier section; every row in a decision archive must have its index pointer (reverse check). Regressions added for each.
- Codex round 2 on `995e1c4` (two P2 findings, both fixed): the startup protocol now runs `validate_project.py` before trusting the views (step 2), and a duplicated full or archived ADR row is an error instead of collapsing into a set. Regressions added.
- Codex round 3 on `aae2067` (three P2 findings, all fixed): the delegation default in `MASTER_INSTRUCTIONS.md` is scoped to platforms whose master defines it (today Claude Code only; ADR-089 item F stands elsewhere); a second `## Current (date)` section is an error; an empty decision archive no longer skips the indexed-row check. Regressions added.
- Codex round 5 on `1fa6e78` (one P2, fixed; the round was triggered unintentionally by a comment that quoted the trigger phrase, beyond the ADR-089 cap): the Current and changelog dates are parsed as calendar dates, so an impossible or far-future Current heading fails instead of sorting after every real entry. Regressions added.
- Verified: `validate_project.py` passes with 81 required paths and the record-view checks; `sync_skills.py --check` clean; 449 unit tests pass (3 skipped) on Linux before the merge of `main`, 459 after, 462 after round 5.

## 2026-10-07 — Layperson README (ADR-092, part 2)

- `README.md` rewritten as a short plain-language guide: create the project, say "finish the bootstrap" in Claude Code or Codex, approve with `bootstrap_gate.py activate`, and `web_setup.py` for web chats.
- Reference material moved without loss to `docs/REFERENCE.md` (feature list, work packets, native entrypoints, repository map, CLI exit codes, operating rule, security default, template status); every "CLI exit codes" reference now points there.
- `START_HERE.md` follows the same steps; `docs/GITHUB_PUBLISH.md` drops the now-default `--interactive`.

## 2026-10-06 — Fewer copy/pastes (ADR-092)

- `bootstrap_project.py --destination <dir>` alone runs the intake; its next steps say to open Claude Code or Codex and say "finish the bootstrap", then run `bootstrap_gate.py activate`.
- New `scripts/web_setup.py --client chatgpt|claude|mistral`: one zip of the files to upload and the Project instructions on the clipboard. `docs/WEBUI_SETUP.md` and `docs/PLATFORM_SETUP.md` use it.

## 2026-10-06 — Ask rules for merges and GitHub writes (ADR-091)

- `.claude/settings.json` gains `permissions.ask` rules (Bash and PowerShell) that prompt before merging PRs, editing or commenting on issues, deleting releases or remote branches, and `gh api` writes with an explicit method. The Bash denies gain `PowerShell(...)` mirrors, including recursive `Remove-Item`, and the force-push deny also covers `--force-with-lease`, `-f` and `+refspec`. Ask rules do not apply in `bypassPermissions` mode. Auto-mode classifier rules moved to the owner's user settings, because the classifier ignores `autoMode` in project settings (Codex P1 on PR #111).

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
