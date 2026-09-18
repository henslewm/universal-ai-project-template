# Current Handoff

- **Prepared:** 2026-09-18 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `issue-10-family-law-domain` (off `main` at `d2350ec25474816545b4418a4c8c5cd97516e2c6`, PR #35 / Issue #9 follow-up, ADR-058). Confirm the current head with `git log --oneline -1` rather than trusting a figure here. Working tree is clean; nothing pending to commit in the tracked repository.
- **Scope:** Issue #10 (complete high-conflict NC family-law template), session 2: ran the repeat-dogfood acceptance exercise. Two rounds found and fixed real defects; the third and last review this task's budget permits found a real defect that is **not yet fixed**, and the review budget is now exhausted. Stopped here for the day — do not treat this as closed.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10). Read `PROJECT_STATE.md`'s "Issue #10, session 2" section and ADR-060/ADR-061/ADR-062 in `DECISIONS.md` before continuing — they contain the full findings; this handoff only summarizes the exact next action.

## Before doing anything else: check for another agent on this repo

This session found a second, unattended Codex CLI process (`codex.exe --ask-for-approval never`) independently working Issue #10 in this same checkout, started earlier the same day in a separate conversation the user had with it. Its edits collided with this session's edits to the shared control files (`PROJECT_STATE.md`, `DECISIONS.md`, `OPEN_LOOPS.md`, `CHANGELOG.md`, `SOURCE_INDEX.md`, `HANDOFF_CURRENT.md`) and it committed a conflicting "checkpoint" (`d2c67dd`) before it could be stopped. The user had it terminated; that commit was discarded by `git revert` (`95446eb` — the branch is unpushed, so nothing external was affected). See ADR-062. **Before resuming work, run a process check** (e.g. `Get-CimInstance Win32_Process | Where-Object CommandLine -match 'codex|claude'`) to confirm no other unattended agent is currently writing to this checkout, especially if these files look inconsistent with what you expect.

## Exact state of the dogfood ledger

`_acceptance-demo-10` (outside this repository, at `C:\Users\hensl\Documents\GitHub\_acceptance-demo-10`) holds 12 ledger events:

1. `INIT`, `CHECKS` (baseline)
2. `REVIEW_OPEN`/`REVIEW_RESULT` round 1 (same-family Claude subagent) — `REJECT_BOUNDED` on `AC-DECOMPOSITION`
3. `RESUBMIT`, `CHECKS` — fixed (commit `f47a43d`)
4. `REVIEW_OPEN`/`REVIEW_RESULT` round 2 (cross-family Codex) — `REJECT_BOUNDED` on `AC-PROVENANCE`, `AC-ADVERSE`
5. `RESUBMIT`, `CHECKS` (first attempt failed on an unrelated workspace artifact, second passed clean) — fixed via ADR-060 (commit `29422ca`)
6. Event 12, `REVIEW_OPEN` — round 3 (cross-family Codex) dispatched. `reviews_used` is now **3 of `max_review_attempts=3`**.

Round 3's report exists at `_acceptance-demo-10\review-3\review-report.json` with verdict `REJECT_BOUNDED`, but **`ingest-review` refused it**: its `scope`-kind `contract_failures` entry has `failed_ref: "scope.allowed"`, which is not a literal string from `contract.scope.allowed`/`prohibited` as the controller requires (`acceptance.py` line ~161-167). The report is genuine, real, evidence-worthy findings — do not discard it — but it cannot be ingested as written, and the round-3 review event therefore has a dispatched review with **no recorded verdict**.

## The two real findings from round 3

1. **`AC-ADVERSE` (real code gap, must fix):** `scripts/family_law.py`'s `validate_contract_domain` requires nonempty `adverse_authority` whenever a `LEGAL_PROPOSITION` assertion is declared, but never requires a `primary_source_verified` validation to exist at all. `examples/family-law/packets/FAM-04-issue-brief.contract.json` declares a `LEGAL_PROPOSITION` with only `VAL-CITATION-LINKAGE` (`citation_linked`, command-bearing) and no primary-source rung, and it currently validates — contrary to the packet's own stated objective that a legal proposition needs both adverse authority *and* primary-source verification. Fix: require at least one command-free `primary_source_verified` validation whenever a contract declares `LEGAL_PROPOSITION`; add it to FAM-04; add a regression that a `LEGAL_PROPOSITION` packet omitting that rung (including a non-synthetic one) is refused.

2. **Scope-declaration mismatch (needs a decision, not obviously a code fix):** the reviewer flagged that this branch's changes to `CHANGELOG.md`, `DECISIONS.md`, `HANDOFF_CURRENT.md`, `OPEN_LOOPS.md`, `PROJECT_STATE.md`, `SOURCE_INDEX.md` fall outside the dogfood packet's declared `scope.allowed` (which only names the domain schema/module/tests/examples/registration/bootstrap-field/fixture changes). This is arguably not a real defect — `MASTER_INSTRUCTIONS.md`'s closeout protocol requires these updates every session — but the packet's own scope declaration didn't anticipate that. Decide either to widen `scope.allowed` on the next contract revision to admit standing closeout docs, or to exclude those files from the reviewed diff artifact when preparing the next review packet.

## Exact next action

1. Fix `AC-ADVERSE` in `scripts/family_law.py` and `examples/family-law/packets/FAM-04-issue-brief.contract.json`, plus regressions, and rerun the full suite.
2. Resolve the scope question above (widen `scope.allowed` via a contract revision, or narrow the next reviewed diff).
3. `reviews_used` is already at `max_review_attempts` (3) — a fourth review dispatch needs either a contract revision (which can raise the budget) or a recorded architect decision under the existing budget. Check `ACCEPTANCE_PROTOCOL.md` and `scripts/acceptance.py`'s `decide`/`waive-cross-family` commands for the supported path; do not simply re-run `prepare-review` without resolving this first, since `_acceptance-demo-10`'s config currently refuses it.
4. Once a further review is obtained and returns `APPROVE`, run `accept`, write `docs/ISSUE_10_VALIDATION.md` (does not exist yet — no analog to `docs/ISSUE_9_VALIDATION.md` has been created for #10), then open the PR and run the Codex review loop to a clean result before asking for merge authorization.

## What #9 and PR #35 left you (background, unchanged)

`docs/ISSUE_9_VALIDATION.md` is the full record of #9's own acceptance and 23-round Codex review (ADR-041–ADR-055). Its lessons — evidence-binding is several checks, not one, and R-012 (stop for diagnosis when a review class recurs) — are exactly what round 3 is: the third recurrence of a real gap in this domain's provenance/scope machinery, following rounds 1 and 2. Expect this pattern to continue; look for the actual invariant rather than patching only what round 3 found.

## Verified state

398 tests pass on Windows (`unittest discover -s tests -p "test_*.py"` from the repo root via `%TEMP%\uaipt-venv\Scripts\python.exe`). `python scripts/validate_project.py` passes 81 required paths. `python scripts/sync_skills.py --check` reports 0 differing files (a drift in the gitignored `.claude/settings.local.json` mirror under `skills/complex-project-bootstrapper/assets/project-template/` was found and fixed this session by rerunning `sync_skills.py`; nothing tracked changed). Git working tree is clean; nothing has been pushed, and no PR exists yet for this branch.

## Limitations carried forward (outside #9/#10; maintainer's call under master #14)

OL-016 (template-packaging defects) remains open from #8's closure, unaddressed by #9 or #10.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; the working interpreter with `jsonschema==4.26.0` is at `%TEMP%\uaipt-venv\Scripts\python.exe`. Run the Windows suite with `unittest discover -s tests -p "test_*.py"` from the repository root — plain `discover` finds nothing. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

The Codex CLI (`codex exec`) is available locally and was used directly for round 2's and round 3's cross-family review, run non-interactively with `-C <review-dir> -s read-only --skip-git-repo-check` and the prompt on stdin — this is a genuinely independent model, not a simulated one. Do not confuse a one-shot `codex exec` review dispatch with a persistent unattended `codex.exe --ask-for-approval never` session — check for the latter before assuming sole ownership of this working tree (see above).

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them. A source verification record is an operator's declaration the controller cannot authenticate; the digest makes it auditable, not true. Acceptance justifies but does not perform merge, publication, or closure. No credential, restricted case fact, or real party/case identity belongs in this repository's examples, fixtures, configuration, packets, reports, ledgers or logs — every family-law example in this template is deliberately fictional and declares `domain.synthetic: true`. Model-performance calibration remains #12. Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
