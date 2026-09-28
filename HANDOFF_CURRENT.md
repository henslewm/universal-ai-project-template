# Current Handoff

- **Prepared:** 2026-09-27 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `main`. PR #50 merged at `620fc9a`, PR #54 (#53, ADR-069) at `dff35e0`, PR #58 (lean worker startup, ADR-070) at `6c24d03`, PR #59 (#56) at `01cbcd9` and PR #60 (#23) at `dae4ab4` on 2026-09-27. Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** Issue #10 (the complete high-conflict NC family-law template) is **closed** through merged PR #50. The next child under master #14 is #11.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #11](https://github.com/henslewm/universal-ai-project-template/issues/11). #10's completion comment and `docs/ISSUE_10_VALIDATION.md` are its full record, and ADR-059 through ADR-062 and ADR-065 through ADR-068 hold the decisions.

## What merged on 2026-09-27

**PR #45: scope policy (ADR-063).** A review finding is actionable only when it names a concrete defect the change introduced or exposed, or a demonstrable failure of an explicit applicable requirement, with its behavior, trigger and evidence. `MASTER_INSTRUCTIONS.md` → "Review findings and merge discipline" is the single definition. Apply it to every later review round.

**PR #58: lean automatic worker startup (ADR-070).** Every new worker brief carries the bounded worker rules, only the instruction files the contract's `worker_instructions` names, and digest-only references to the governing documents. A governing document's text is never embedded, whether it is reached by name, alias, hard link or copy. It fits the example 16384-token local binding with 517 tokens of headroom (`docs/WORKER_STARTUP_VALIDATION.md`). Codex reviewed it over three rounds: two P2s, both fixed, then clean on `7f00ab6`. It supersedes PR #55, which the maintainer closed.

**PR #48: Mistral Vibe platform files.** These are restored but not yet wired in. [#46](https://github.com/henslewm/universal-ai-project-template/issues/46) tracks the authority order, `validate_project.py` required paths, README and bootstrapper. [#47](https://github.com/henslewm/universal-ai-project-template/issues/47) tracks verifying the product claims and the maintainer's master #14 scope decision. Neither blocks #11.

## Before doing anything else: check for another agent on this repo

On 2026-09-18 an unattended Codex CLI session worked #10 in this same checkout and collided with the control-file edits. Its commit was reverted (ADR-062). Before writing, run a process check (for example `Get-CimInstance Win32_Process | Where-Object CommandLine -match 'codex|claude'`) and confirm any running agent's working directory is elsewhere.

## Review state

- **`_acceptance-demo-10` (contract revision 1): provisional history.** Three rounds ran: AC-DECOMPOSITION fixed in `f47a43d`; AC-PROVENANCE and AC-ADVERSE fixed in `29422ca`; then round 3's AC-ADVERSE and scope findings, dispatched and not ingested (ADR-061). Both round-3 findings are resolved by ADR-065.
- **`_acceptance-demo-10b` (contract revision 2): ACCEPTED.** 5 events, head `472d2a60`, deterministic gate passed, and a cross-family Codex approval with no waiver.
- **PR #50, Codex round 1 on `e93271d`:**
  - P1 (actionable, fixed): the profile promises model review for elevated fact statuses, but a low-risk `LEGAL_PROPOSITION` packet was accepted on the deterministic gate alone. A packet asserting `DISPUTED_FACT` or `LEGAL_PROPOSITION` must now have `model_review` in its effective gates.
  - P2 (fixed): this handoff was stale.
- **PR #50, Codex round 2 on `7bb558e`:** two P1s in `family_law.status`, both fixed (ADR-067). A verified contradiction now outranks an unrelated record problem, and an `UNKNOWN` assertion can never be covered. 
- **PR #50, Codex round 3 on `8845668`:**
  - P1 (actionable, fixed, ADR-068): a source verification record was bound to its claim only by text, so a record of an unrelated source could verify a legal proposition. Assertions now declare `verified_by`, the sources whose review can verify them, and a legal proposition must list its own authority. Each record names its `source_id`. An undeclared source verifies nothing, and a record covers a claim only when its `source_id` is in that claim's `verified_by`.
  - P2 (fixed): stale current-state text, swept across all the control files.

- **PR #50, Codex round 4 on `7ff2158`** (the one extra round the maintainer authorized): one P1, actionable and **deferred to [#53](https://github.com/henslewm/universal-ai-project-template/issues/53)**. Coverage is keyed by assertion text, so two entries with identical text but different `verified_by` can share one supporting record. The maintainer chose to merge as is, and the thread reply points to #53.

## Exact next action

The maintainer approved an open-issue triage on 2026-09-27, ranked by value per cost.
- **Done:**
  - #56 was fixed through PR #59 (`01cbcd9`).
  - #23 was fixed through PR #60 (`dae4ab4`); worker reports are now schema-checked in both entrypoints, after a credential scan.
  - #33 and #42 were closed as not planned.
  - Overlapping wants were cross-linked: #31/#32; #38/#43 under #12; #36, #37, #40 and #41 blocked on #25.
  - Refresh comments went onto #11, #13, #28, #29, #39, #44 and #49.
  - #49 (packaging defects, ADR-071) was fixed through [PR #61](https://github.com/henslewm/universal-ai-project-template/pull/61). The maintainer chose one workflow file whose payload check runs only where the payload folder exists. If PR #61 is still open, finish its Codex review and merge it before starting #11.
- **Next, in order:**
  1. **Decisions recorded 2026-09-27 (OL-022):** ADR-072 fixes the exit-code policy for #32/#31, and ADR-073 fixes the #25 execution boundary (an operator-run `launch` only; `dispatch` stays preparation-only). #36, #37, #40 and #41 are unblocked for design against ADR-073.
  2. **Quick closures that need no further decision:** #47, #26, #29, #27, #46.
  3. **#11** under master #14, on a normal branch from `main` (OL-021), then #12 → #13. Pull #43 and #38 into #12 as local-tier calibration runs.

If PR #61 (#49) is still open when you read this, finish its Codex review rounds and merge before starting #11.

PR #52 (the ESP32 rules) merged at `6c3c0ee`; its open Codex finding was #56, now fixed. #46 and #47 (Mistral) remain open.

## Branches (audited 2026-09-27, after the PR #60 merge)

- The pre-rewrite branch cleanup is done, and PR #1 is closed.
- **Keep:** `main`.
- **To delete** (the maintainer authorized cleanup; the permission guard blocked this session's delete). Five of these have 0 commits outside `main`. `codex/automatic-worker-startup` has one: PR #55's superseded rescue commit, which stays reachable as `refs/pull/55/head`.
  ```
  git push origin --delete codex/automatic-worker-startup esp014-skip-in-place-when-generated issue-23-report-schema issue-51-modular-platformio-rules issue-56-platformio-snippet worker-startup-lean
  git fetch --prune
  ```
- **`platformio.ini`:** resolved 2026-09-27. The maintainer's root ESP32-S3 config now ships as `templates/software-hardware/platformio.example.ini`, conformed to `docs/PLATFORMIO.md`'s rules, through PR #63 (merged at `fd4c20d` after a CodeRabbit review under ADR-074). The untracked root file is gone, so `sync_skills.py` no longer copies it into the payload. Add `platformio-example` to the branch cleanup.

## What #9 and PR #35 left you (background, unchanged)

`docs/ISSUE_9_VALIDATION.md` is the full record of #9's own acceptance and 23-round Codex review (ADR-041–ADR-055). Its lessons — evidence-binding is several checks, not one, and R-012 (stop for diagnosis when a review class recurs) — applied throughout #10: each recurrence in its record-provenance class (ADR-060, ADR-067, ADR-068, and #53) was answered by stating the invariant first. Expect the same in #11's legal domain.

## Verified state

420 tests pass on Windows on `main` after the PR #60 merge (`unittest discover -s tests -p "test_*.py"` from the repo root, system `python` 3.12.8). `python scripts/validate_project.py` passes 81 required paths. `python scripts/sync_skills.py --check` reports 0 differing files (a drift in the gitignored `.claude/settings.local.json` mirror under `skills/complex-project-bootstrapper/assets/project-template/` was found and fixed this session by rerunning `sync_skills.py`; nothing tracked changed). `main` is pushed. Confirm with `git status -sb` and `gh pr list`.

## Limitations carried forward (outside #9/#10; maintainer's call under master #14)

OL-016 (template-packaging defects) is now tracked as [#49](https://github.com/henslewm/universal-ai-project-template/issues/49) (maintainer decision 2026-09-27); it is outside #10.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; `%TEMP%\uaipt-venv` has lost its `pyvenv.cfg` and no longer runs (as of 2026-09-27); the system `python` (3.12.8) has `jsonschema==4.26.0` and runs the suite. Run the Windows suite with `unittest discover -s tests -p "test_*.py"` from the repository root — plain `discover` finds nothing. Under WSL, discover each suite individually (`discover -s tests -p test_acceptance.py`, etc.); importing by dotted module name fails because `tests/` is not a package. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

The Codex CLI (`codex exec`) is available locally and was used directly for round 2's and round 3's cross-family review, run non-interactively with `-C <review-dir> -s read-only --skip-git-repo-check` and the prompt on stdin — this is a genuinely independent model, not a simulated one. Do not confuse a one-shot `codex exec` review dispatch with a persistent unattended `codex.exe --ask-for-approval never` session — check for the latter before assuming sole ownership of this working tree (see above).

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them. A source verification record is an operator's declaration the controller cannot authenticate; the digest makes it auditable, not true. Acceptance justifies but does not perform merge, publication, or closure. No credential, restricted case fact, or real party/case identity belongs in this repository's examples, fixtures, configuration, packets, reports, ledgers or logs — every family-law example in this template is deliberately fictional and declares `domain.synthetic: true`. Model-performance calibration remains #12. Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
