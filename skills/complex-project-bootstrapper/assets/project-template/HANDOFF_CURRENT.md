# Current Handoff

- **Prepared:** 2026-09-15 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** main
- **Latest accepted merge:** `494587cfae01f9dde442a5d0e5fbe50cdfb6b257` (PR #22, closed #8 again; parents `0c8fc8c` and `3a4e92b`). Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** #9 in progress on `issue-9-software-hardware-domain`. Started 2026-09-13 with an approved design (issue #9, first comment); the branch was merged up to `main` on 2026-09-14 with a merge commit and its provisional dogfood is being repeated against the merged gate.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #9](https://github.com/henslewm/universal-ai-project-template/issues/9) — complete software + hardware domain template. Issues #2 through #8 are closed through merged PRs #15 to #22; #8 was closed through PR #21, reopened the same evening because Codex's review of the merged head landed after the closure, and closed again through PR #22. Read each child's completion comment for the limitations it carried forward rather than assuming a closed issue left nothing behind.

## What the reopening of #8 left you

Every Codex finding on PR #22 has a reply on GitHub (read them with `gh api`, never from email). The loop that produced 30 findings in 17 reviews was stopped for diagnosis: rounds 1–14 patched each lifetime or trust defect where it was noticed, and ADR-024 turned both into invariants — `ProcessTree.own` holds a check from launch to confirmed-stopped and ends the tree on every exit (an error in its own teardown refuses the run rather than becoming a check result), `trusted_workspace`/`check_cwd` establish filesystem trust before any command and inspect every path component before resolution — with one regression per invariant. ADR-025 lets the GitHub ledger extend and publish a feedback ledger at `ACCEPTED`, the status `sync-feedback` leaves, so accepted work can complete publication end to end (regression in `test_full_acceptance_closes_the_feedback_task`). After ADR-024 the only lifetime-class returns were two defects in the new code itself — the launch-error handler wrapping the owned block, and a uid-based membership inference that a setuid helper defeats — both closed fail-closed (membership now comes from the kernel's `getpgid`). The standing rule, R-012: if a review class recurs, stop for diagnosis and write the invariant before code. Read the last two Codex rounds on PR #22 before touching the `/proc` liveness code again; eight findings landed there, and a future change should replace the primitive rather than patch it.

A clean Codex result arrives as an issue comment ("Didn't find any major issues", with the reviewed commit), not as a PR review; poll `issues/22/comments` as well as `pulls/22/reviews` when waiting for one.

## What #8 left you

`ACCEPTANCE_PROTOCOL.md` is the acceptance contract; `scripts/acceptance.py` keeps one hash-chained ledger per reviewed task, independently re-executes the contract's declared validation commands (ADR-014 — the single deliberate exception to the metadata-only pattern), renders minimal review packets from ledger records only, and grants acceptance only when every gate the risk floor requires has a current-submission passing record. Decisions ADR-014 through ADR-017. `docs/ISSUE_8_VALIDATION.md` is the full record; the 11-event dogfood ledger is preserved at `_acceptance-demo` beside the repository.

Three things there matter beyond #8 specifically.

First, the dogfood demonstrated the machinery on its own diff: the deterministic gate contradicted the implementer's clean-run claim with an observed drift failure, a fresh minimal-context same-family subagent then found a real gate-bypass defect (a pre-resubmission gate approval satisfying the gate for a never-reviewed resubmission — ADR-017), and acceptance was granted only after the regression-tested correction and a fresh approval. Minimal context is not a handicap: 13–15 KB packets carried everything two reviewers needed.

Second, cross-family review in practice remains unexercised for the template's own children (#7 and #8 both same-family, stated at both closures). What changed is that the lapse can no longer be silent: on high- and critical-risk packets, acceptance refuses same-family review without an explicitly recorded waiver. When a cross-family strong model is reachable in a future child's session, use it.

Third, for #9: the machine-runnable-versus-attested validation split is exactly the hardware distinction #9 must encode — a simulated check is a `command`, hardware-in-loop verification is an operator attestation, and the acceptance controller already refuses to blur them.

## Verified state

307 tests pass on Windows; the acceptance suite (67 tests, 3 Windows-only skips) and the GitHub ledger suite (59) pass under WSL Linux. Repository validation passes 67 required paths and `scripts/sync_skills.py --check` reports 0 differing files. CI `validate` was green on every push to PR #22 and on the merged head.

## Exact next action

Continue #9 on `issue-9-software-hardware-domain`, orienting from master #14 and #9 only plus these durable documents; `docs/ISSUE_9_VALIDATION.md` records what has been corrected, what the repeat dogfood established and what remains. The construction branch `issue-8-codex-findings` remains until the later authorized cleanup.

## Limitations carried forward (outside #8; maintainer chose a note, not an issue)

Codex's repository review reproduced three template-packaging defects that predate PR #22 and are not #8's subject: a project generated from the template inherits `.github/workflows/validate-project.yml`, which runs `scripts/sync_skills.py --check` against a tree that is no longer the template (203 differing files for a new-directory project, 12 in place); `sync_skills.py` is source-driven and never detects a payload file whose source was deleted, so `--check` reports zero drift while an obsolete copy ships; and the bootstrap carries this repository's development decision history into fresh projects. Where a fix belongs is the maintainer's call under master #14.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; the working interpreter with `jsonschema==4.26.0` is at `%TEMP%\uaipt-venv\Scripts\python.exe`. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

A concurrent Claude session dropped three files into the working tree during #8. `prompts/PROVISION_LOCAL_MODEL.md` was committed at `0c8fc8c` on Winston's instruction as maintainer-supplied #12 input. `Claude outputs/` is gitignored and payload-excluded because the desktop app will recreate it; one earlier file from it is preserved at `_claude-outputs-preserved` beside the repository. Use explicit path adds, not `git add -A`, in case that session drops more files.

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them: a descendant that leaves the session with `setsid()` and a link created, read and removed inside one command are beyond ADR-024's invariants, and a project that must withstand an adversarial declared command runs the gate inside an isolation primitive of its own. Whether the declared commands genuinely exercise the criteria is an architect-quality question. Acceptance justifies but does not perform merge, publication, or closure. No credential belongs in configuration, packets, reports, ledgers or logs. Model-performance calibration remains #12, now carrying both #7's run-4 profile and #8's review-economics observations (two ~110K-token subagent reviews from 13–15 KB packets). Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
