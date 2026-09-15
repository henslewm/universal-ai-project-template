# Current Handoff

- **Prepared:** 2026-09-15 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** main
- **Latest accepted merge:** `d873ec5cd1be503a19880eacbaf9cfba764d9fa5` (PR #34, closed #9). Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** #9 closed. Next unblocked child per master #14's ordered list is #10 (complete high-conflict NC family-law template).

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10). Issues #2 through #9 are closed through merged PRs #15 to #34. Read each child's completion comment for the limitations it carried forward rather than assuming a closed issue left nothing behind.

## What #9 left you

`docs/ISSUE_9_VALIDATION.md` is the full record. The repeat dogfood at `_acceptance-demo-9b` was accepted 2026-09-14 (11 events, cross-family approval, no waiver) after ADR-026 to ADR-029. PR #34's Codex review then ran 23 rounds before a clean result ("Didn't find any major issues") and the merge above; decisions ADR-041 through ADR-055 record every round.

Three things there matter beyond #9 specifically, all in the generic acceptance controller rather than the software-hardware domain module:

First, binding an operator attestation to "the evidence it describes" is not one check but several, and each one the review found was a real gap, not a false positive: the contract revision and exact hash (ADR-043/044), the submitted result's `dispatch_id` and the artifact's identity (ADR-047/049/054 — a reference-kind artifact can carry a fixed empty-content digest regardless of what it references, so identity has to bind the reference itself, not only `sha256`), and the observation's own timestamp bounded on both sides by the ledger's current submission and the attestation event (ADR-046/052). A resubmission clearing prior attestations is necessary but not sufficient; each of these dimensions can be forgotten independently, and each was.

Second, "a stored record replays marked, not raised" (ADR-032, from #8) needed one more corollary: replaying a shortfall-marked attestation as satisfying the deterministic gate is right for preserving an *already-accepted* ledger's history, but wrong for justifying a *new* acceptance decision today (ADR-053). `acceptable()` now distinguishes the two by the existing `stored` flag `apply()` already threads through every event.

Third, R-012 (stop for diagnosis when a review class recurs) held again: the submission-binding class above surfaced across five separate rounds (16, 18, 20, 21, 22) before every dimension was closed, each time because the fix answered the specific finding rather than the general shape of "what does this evidence actually prove." When #10's domain rules add their own evidence-binding logic, ask up front what a resubmission, a stale timestamp, and a not-yet-decided acceptance can each independently forge, rather than waiting for each to surface separately.

## Verified state

360 tests pass on Windows; the acceptance (68, 3 Windows-only skips), work-packet (41), software-hardware (50) and feedback (47) suites pass under WSL Linux. Repository validation passes 81 required paths and `scripts/sync_skills.py --check` reports 0 differing files. CI `validate` was green on the merged head.

## Exact next action

Start #10 (complete high-conflict NC family-law template) from master #14 and #10 only, plus these durable documents, following the same interactive-bootstrap-then-decompose pattern used for #9. The construction branch `issue-9-software-hardware-domain` remains until the later authorized cleanup; do not delete it outside that cleanup.

## Limitations carried forward (outside #9; maintainer's call under master #14)

OL-016 (template-packaging defects: generated projects inherit a payload-drift CI check they cannot pass; `sync_skills.py` never detects an obsolete payload file; development decision history ships into fresh projects) remains open from #8's closure, unaddressed by #9.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; the working interpreter with `jsonschema==4.26.0` is at `%TEMP%\uaipt-venv\Scripts\python.exe`. Run the Windows suite with `unittest discover -s tests -p "test_*.py"` from the repository root — plain `discover` finds nothing. Under WSL, discover each suite individually (`discover -s tests -p test_acceptance.py`, etc.); importing by dotted module name fails because `tests/` is not a package. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them: a project that must withstand an adversarial declared command runs the gate inside an isolation primitive of its own. Whether the declared commands genuinely exercise the criteria is an architect-quality question. Acceptance justifies but does not perform merge, publication, or closure — this handoff records that #9's merge was the maintainer's own explicit decision, not one the acceptance ledger made for them. No credential belongs in configuration, packets, reports, ledgers or logs. Model-performance calibration remains #12. Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
