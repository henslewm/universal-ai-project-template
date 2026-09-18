# Issue #10 validation checkpoint

Verified 2026-09-18. This is an end-of-day checkpoint, not acceptance. The user requested a local commit with comments and pickup instructions, then a stop. Resume only on user return.

## Implementation and checks

- Branch: `issue-10-family-law-domain`; implementation reviewed at `29422ca`.
- `f47a43d` fixes round 1's `AC-DECOMPOSITION` gap by running all four example packets' commands through the gate.
- `29422ca` implements ADR-060's record verification and coverage of every declared assertion after round 2's `AC-PROVENANCE`/`AC-ADVERSE` rejection.
- Fresh full local suite: 398 tests passed in 205.068 seconds. `validate_project.py` passed 81 required paths.
- Clean tracked archive of `29422ca`, extracted under ignored `build/issue-10-29422ca-review3/source`: 81 required paths passed and `sync_skills.py --check` reported zero differences.
- After selectively synchronizing the 12 checkpoint documents/reports and their 12 payload copies, both the root and the snapshot including those checkpoint files passed all 81 required paths. The checkpoint snapshot's payload check reported zero differences; `git diff --check` passed.
- The final live-checkout sync check still flags only ignored `.claude/scheduled_tasks.lock`. Preserve this runtime file; do not distribute it. This environmental difference is absent from the reviewed tracked-content snapshot. Verify the eventual commit with Git rather than treating these pre-commit checks as a commit receipt.

The preserved Python 3.12.14 launcher is `$env:USERPROFILE\.local\bin\python3.12.exe`. Its actual executable is `C:\Users\hensl\Documents\GitHub\_acceptance-demo-10\review-2\.python-runtime\cpython-3.12-windows-x86_64-none\python.exe`. Preserve that external review runtime and the temporary virtualenv's site-packages; the old temporary virtualenv launcher cannot find its base Python. The successful test command used the existing dependency installation (`jsonschema` 4.26.0):

```powershell
$env:PYTHONPATH = Join-Path $env:TEMP 'uaipt-venv\Lib\site-packages'
& "$env:USERPROFILE\.local\bin\python3.12.exe" -B -m unittest discover -s tests -p 'test_*.py'
& "$env:USERPROFILE\.local\bin\python3.12.exe" -B scripts/validate_project.py
```

No repository virtualenv, dependency installation or persistent environment change was made. The bootstrap gate still rejects absent `config/bootstrap.json`; explicit Issue #10 maintenance authority is not ACTIVE status or an activation receipt.

The authorized checkpoint commit was attempted, but Git staging failed on `.git/index.lock` with permission denied. Nothing was staged or committed by that attempt. `build/issue-10-29422ca-review3/commit-checkpoint.ps1` is the guarded host-terminal handoff; it verifies the reviewed content before staging only the listed checkpoint files and committing, without pushing.

## Original ledger and review binding

- Authoritative ledger: `C:\Users\hensl\Documents\GitHub\_acceptance-demo-10\ledger` (outside this session's writable root).
- Latest event: 12, `REVIEW_OPEN`; `reviews_used=3`, `max_review_attempts=3`. The original ledger was not changed this session.
- Pending review: `c759b8ec0ee9f2b8c34e7144f0fe449274619fe053b3ab3009ae52a814e792ca`.
- Reviewer declaration: `Codex (OpenAI, cross-family reviewer, round 3)`, family `openai`, tier 3; implementer family `claude`.
- Reviewed artifact: diff of `29422ca` against `3eeba90`, SHA-256 `966aafb7441ca28fa737b22019b8d61a4829f6723521b56105f3debf4bc8ef81`.
- Original expected report: `C:\Users\hensl\Documents\GitHub\_acceptance-demo-10\review-3\review-report.json`. It was absent at an earlier check and appeared during closeout. Preserve it and recheck current contents before any later action.
- Historical `CHECKS` event 11 records 398 tests, 81 paths and zero payload drift; the fresh local checks above are separate observations.

## Preserved reports and unresolved finding

| Report | Verified result | How to use it |
|---|---|---|
| `reviews/ISSUE_10_ROUND_3.json` | Initial local APPROVE, 5/5; offline-valid but later withdrawn by its reviewer | Historical evidence only; never ingest this superseded approval |
| `reviews/ISSUE_10_ROUND_3_EXTERNAL.json` | Unchanged external REJECT_BOUNDED; offline verification refuses scope failure `failed_ref: "scope.allowed"` because it is not a literal allowed/prohibited entry | Preserve original wording; its substantive adverse-authority finding was reproduced, while the scope/report contract requires architect/reviewer resolution |
| `reviews/ISSUE_10_ROUND_3_RECONCILED.json` | Reviewer's reconsidered REJECT_BOUNDED; offline-valid, 4/5 criteria, one failure; `recorded_in_ledger: false`, `acceptance_granted: false` | Reconciles the local review to the reproduced defect for the same pending opening; not a new review slot or a ledger verdict |

The reproduced failure is concrete: `work_packet.validate_contract` accepts FAM-04 with `fact_statuses=[LEGAL_PROPOSITION]`, `validation_levels={VAL-CITATION-LINKAGE: citation_linked}` and `validation_errors=[]`. Nonempty `adverse_authority` is required, but existence of a `primary_source_verified` validation is not. The passing 398-test suite therefore does not demonstrate the full `AC-ADVERSE` criterion. No fix or new regression was implemented at this checkpoint.

The original report also disputes whether required closeout-document changes fit the dogfood packet's declared scope. Its invalid shorthand reference does not resolve that scope question. ADR-061 preserves the earlier rejection narrative; ADR-062 records the fresh corroboration and reviewer reconsideration without rewriting prior history.

## Resume constraints

On user resumption, the architect first resolves pending-review handling, closeout scope and exhausted review budget. A runtime permitted to write the original evidence directory may consider ingesting the reconciled same-opening rejection only after checking the pending ID and artifact binding and explicitly selecting the authoritative report without overwriting conflicting evidence. No report was ingested here; no acceptance, duplicate ledger, budget reset, fourth review, waiver or external write occurred.

Then define bounded work for the mandatory primary-source rung and meaningful regressions. Any changed implementation needs a new binding assessment and a budget-aware architect path before renewed review. Only after acceptance should the session prepare the PR and final-head automated Codex review. Merge still requires user authority. Issue #10 is open with no PR for this branch; do not start #11. All examples remain fictional and establish no real case facts or legal authority.
