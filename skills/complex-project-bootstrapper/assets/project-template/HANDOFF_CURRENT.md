# Current Handoff

- **Prepared:** 2026-09-27 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `issue-10-family-law-domain`, open as [PR #50](https://github.com/henslewm/universal-ai-project-template/pull/50) against `main`. `main` (PRs #45 and #48; ADR-063 and ADR-064) was merged in at `a638098`. Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** Issue #10 (complete high-conflict NC family-law template) is accepted through its dogfood at `_acceptance-demo-10b` and is in PR review. It is not merged or closed.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10) and PR #50. `docs/ISSUE_10_VALIDATION.md` is the full record, and ADR-059 through ADR-062 and ADR-065 through ADR-068 hold the decisions.

## What merged on 2026-09-27

**PR #45: scope policy (ADR-063).** A review finding is actionable only when it names a concrete defect the change introduced or exposed, or a demonstrable failure of an explicit applicable requirement, with its behavior, trigger and evidence. `MASTER_INSTRUCTIONS.md` → "Review findings and merge discipline" is the single definition. Apply it to every later review round, including #10's.

**PR #48: Mistral Vibe platform files.** These are restored but not yet wired in. [#46](https://github.com/henslewm/universal-ai-project-template/issues/46) tracks the authority order, `validate_project.py` required paths, README and bootstrapper. [#47](https://github.com/henslewm/universal-ai-project-template/issues/47) tracks verifying the product claims and the maintainer's master #14 scope decision. Neither blocks #10.

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

## Exact next action

Read Codex round 4 on PR #50's current head. The maintainer authorized this one round and no more. If it is clean, ask the maintainer for the merge go-ahead. If it has actionable findings (ADR-063), do not start round 5. Instead ask the maintainer to merge as is, and open a detailed GitHub issue for each remaining finding, with its file and line, trigger, evidence and classification. After merge, close #10 with a completion comment and continue master #14.

## What #9 and PR #35 left you (background, unchanged)

`docs/ISSUE_9_VALIDATION.md` is the full record of #9's own acceptance and 23-round Codex review (ADR-041–ADR-055). Its lessons — evidence-binding is several checks, not one, and R-012 (stop for diagnosis when a review class recurs) — are exactly what round 3 is: the third recurrence of a real gap in this domain's provenance/scope machinery, following rounds 1 and 2. Expect this pattern to continue; look for the actual invariant rather than patching only what round 3 found.

## Verified state

406 tests pass on Windows after PR #50 round 3 (`unittest discover -s tests -p "test_*.py"` from the repo root, system `python` 3.12.8). `python scripts/validate_project.py` passes 81 required paths. `python scripts/sync_skills.py --check` reports 0 differing files (a drift in the gitignored `.claude/settings.local.json` mirror under `skills/complex-project-bootstrapper/assets/project-template/` was found and fixed this session by rerunning `sync_skills.py`; nothing tracked changed). The branch is pushed and open as PR #50. Confirm the head and CI with `gh pr view 50`.

## Limitations carried forward (outside #9/#10; maintainer's call under master #14)

OL-016 (template-packaging defects) is now tracked as [#49](https://github.com/henslewm/universal-ai-project-template/issues/49) (maintainer decision 2026-09-27); it is outside #10.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; `%TEMP%\uaipt-venv` has lost its `pyvenv.cfg` and no longer runs (as of 2026-09-27); the system `python` (3.12.8) has `jsonschema==4.26.0` and runs the suite. Run the Windows suite with `unittest discover -s tests -p "test_*.py"` from the repository root — plain `discover` finds nothing. Under WSL, discover each suite individually (`discover -s tests -p test_acceptance.py`, etc.); importing by dotted module name fails because `tests/` is not a package. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

The Codex CLI (`codex exec`) is available locally and was used directly for round 2's and round 3's cross-family review, run non-interactively with `-C <review-dir> -s read-only --skip-git-repo-check` and the prompt on stdin — this is a genuinely independent model, not a simulated one. Do not confuse a one-shot `codex exec` review dispatch with a persistent unattended `codex.exe --ask-for-approval never` session — check for the latter before assuming sole ownership of this working tree (see above).

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them. A source verification record is an operator's declaration the controller cannot authenticate; the digest makes it auditable, not true. Acceptance justifies but does not perform merge, publication, or closure. No credential, restricted case fact, or real party/case identity belongs in this repository's examples, fixtures, configuration, packets, reports, ledgers or logs — every family-law example in this template is deliberately fictional and declares `domain.synthetic: true`. Model-performance calibration remains #12. Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
