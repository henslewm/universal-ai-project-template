# Current Handoff

- **Prepared:** 2026-09-14 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `issue-8-codex-findings` (PR #22). `main` is at `0c8fc8c` and still carries the bypassable gate. Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** Issue #8, reopened by ADR-021. Nothing else is active; #9 has not been started.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #8](https://github.com/henslewm/universal-ai-project-template/issues/8) and [PR #22](https://github.com/henslewm/universal-ai-project-template/pull/22). Issues #2 through #7 are closed through merged PRs #15 to #20; #8 was closed through PR #21 and reopened the same evening because Codex's review of the merged head landed after the closure. Read each child's completion comment for the limitations it carried forward rather than assuming a closed issue left nothing behind.

## Where PR #22 stands

Every Codex finding on the PR has a reply on GitHub (read them with `gh api`, never from email). The loop that produced 26 findings in 15 reviews was stopped for diagnosis: rounds 1–14 patched each lifetime or trust defect where it was noticed, and ADR-024 turned both into invariants — `ProcessTree.run` owns a check from launch to confirmed-stopped and ends the tree on every exit, `trusted_workspace`/`check_cwd` establish filesystem trust before any command and inspect every path component before resolution — with one regression per invariant. ADR-025 lets the GitHub ledger extend and publish a feedback ledger at `ACCEPTED`, the status `sync-feedback` leaves, so accepted work can complete publication end to end (regression in `test_full_acceptance_closes_the_feedback_task`). The standing rule: if a Codex round returns findings in the lifetime or trust class again, stop and report — the diagnosis would be wrong.

To finish: confirm a Codex review exists whose `commit_id` equals the current head with no unanswered finding and CI green; check whether Codex is already reviewing before posting `@codex review`; then wait for the maintainer's explicit merge approval. After the merge, re-close #8 with a completion comment, record the limitations below, and only then begin #9 in a fresh session.

## What #8 left you

`ACCEPTANCE_PROTOCOL.md` is the acceptance contract; `scripts/acceptance.py` keeps one hash-chained ledger per reviewed task, independently re-executes the contract's declared validation commands (ADR-014 — the single deliberate exception to the metadata-only pattern), renders minimal review packets from ledger records only, and grants acceptance only when every gate the risk floor requires has a current-submission passing record. Decisions ADR-014 through ADR-017. `docs/ISSUE_8_VALIDATION.md` is the full record; the 11-event dogfood ledger is preserved at `_acceptance-demo` beside the repository.

Three things there matter beyond #8 specifically.

First, the dogfood demonstrated the machinery on its own diff: the deterministic gate contradicted the implementer's clean-run claim with an observed drift failure, a fresh minimal-context same-family subagent then found a real gate-bypass defect (a pre-resubmission gate approval satisfying the gate for a never-reviewed resubmission — ADR-017), and acceptance was granted only after the regression-tested correction and a fresh approval. Minimal context is not a handicap: 13–15 KB packets carried everything two reviewers needed.

Second, cross-family review in practice remains unexercised for the template's own children (#7 and #8 both same-family, stated at both closures). What changed is that the lapse can no longer be silent: on high- and critical-risk packets, acceptance refuses same-family review without an explicitly recorded waiver. When a cross-family strong model is reachable in a future child's session, use it.

Third, for #9: the machine-runnable-versus-attested validation split is exactly the hardware distinction #9 must encode — a simulated check is a `command`, hardware-in-loop verification is an operator attestation, and the acceptance controller already refuses to blur them.

## Verified state

306 tests pass on Windows; the acceptance suite (66 tests, 3 Windows-only skips) and the GitHub ledger suite (59) pass under WSL Linux. Repository validation passes 67 required paths and `scripts/sync_skills.py --check` reports 0 differing files. Every push to PR #22 has had CI `validate` green.

## Exact next action

Finish PR #22 under the review protocol above. Do not merge, comment on, or close #8 without the maintainer's explicit approval, and do not start #9 while #8 has an unanswered finding.

## Limitations carried forward (outside #8; maintainer chose a note, not an issue)

Codex's repository review reproduced three template-packaging defects that predate PR #22 and are not #8's subject: a project generated from the template inherits `.github/workflows/validate-project.yml`, which runs `scripts/sync_skills.py --check` against a tree that is no longer the template (203 differing files for a new-directory project, 12 in place); `sync_skills.py` is source-driven and never detects a payload file whose source was deleted, so `--check` reports zero drift while an obsolete copy ships; and the bootstrap carries this repository's development decision history into fresh projects. Where a fix belongs is the maintainer's call under master #14.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; the working interpreter with `jsonschema==4.26.0` is at `%TEMP%\uaipt-venv\Scripts\python.exe`. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

A concurrent Claude session dropped three files into the working tree during #8. `prompts/PROVISION_LOCAL_MODEL.md` was committed at `0c8fc8c` on Winston's instruction as maintainer-supplied #12 input. `Claude outputs/` is gitignored and payload-excluded because the desktop app will recreate it; one earlier file from it is preserved at `_claude-outputs-preserved` beside the repository. Use explicit path adds, not `git add -A`, in case that session drops more files.

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them: a descendant that leaves the session with `setsid()` and a link created, read and removed inside one command are beyond ADR-024's invariants, and a project that must withstand an adversarial declared command runs the gate inside an isolation primitive of its own. Whether the declared commands genuinely exercise the criteria is an architect-quality question. Acceptance justifies but does not perform merge, publication, or closure. No credential belongs in configuration, packets, reports, ledgers or logs. Model-performance calibration remains #12, now carrying both #7's run-4 profile and #8's review-economics observations (two ~110K-token subagent reviews from 13–15 KB packets). Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
