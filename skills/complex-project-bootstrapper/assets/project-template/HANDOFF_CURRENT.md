# Current Handoff

- **Prepared:** 2026-09-13 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** main
- **Latest accepted merge:** `226353c6279fc36f11d4aa3b36801c82ea88f9ac` (PR #21, closed #8). Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** none active. #9 is next and has not been started.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #9](https://github.com/henslewm/universal-ai-project-template/issues/9) — complete software + hardware domain template. Issues #2 through #8 are closed through merged PRs #15 to #21. Read each child's completion comment for the limitations it carried forward rather than assuming a closed issue left nothing behind.

## What #8 left you

`ACCEPTANCE_PROTOCOL.md` is the acceptance contract; `scripts/acceptance.py` keeps one hash-chained ledger per reviewed task, independently re-executes the contract's declared validation commands (ADR-014 — the single deliberate exception to the metadata-only pattern), renders minimal review packets from ledger records only, and grants acceptance only when every gate the risk floor requires has a current-submission passing record. Decisions ADR-014 through ADR-017. `docs/ISSUE_8_VALIDATION.md` is the full record; the 11-event dogfood ledger is preserved at `_acceptance-demo` beside the repository.

Three things there matter beyond #8 specifically.

First, the dogfood demonstrated the machinery on its own diff: the deterministic gate contradicted the implementer's clean-run claim with an observed drift failure, a fresh minimal-context same-family subagent then found a real gate-bypass defect (a pre-resubmission gate approval satisfying the gate for a never-reviewed resubmission — ADR-017), and acceptance was granted only after the regression-tested correction and a fresh approval. Minimal context is not a handicap: 13–15 KB packets carried everything two reviewers needed.

Second, cross-family review in practice remains unexercised for the template's own children (#7 and #8 both same-family, stated at both closures). What changed is that the lapse can no longer be silent: on high- and critical-risk packets, acceptance refuses same-family review without an explicitly recorded waiver. When a cross-family strong model is reachable in a future child's session, use it.

Third, for #9: the machine-runnable-versus-attested validation split is exactly the hardware distinction #9 must encode — a simulated check is a `command`, hardware-in-loop verification is an operator attestation, and the acceptance controller already refuses to blur them.

## Verified state

284 tests pass on Windows and in CI on Linux. Repository validation passes 67 required paths (harness and acceptance files now registered) and `scripts/sync_skills.py --check` reports 0 differing files. CI `validate` was green on PR #21 before merge; the maintainer explicitly authorized the merge after the session surfaced that the only reviews were agent-run.

## Exact next action

Begin #9 in a fresh session, orienting from master #14 and #9 only plus these durable documents. Do not start it in the same session that merged #8 — master #14 requires rereading it before selecting the next child, and a fresh read after a merge is the point of that rule. Nothing is in flight, no branch is pending, no reservation and no acceptance ledger is open.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; the working interpreter with `jsonschema==4.26.0` is at `%TEMP%\uaipt-venv\Scripts\python.exe`. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

A concurrent Claude session dropped three files into the working tree during #8. `prompts/PROVISION_LOCAL_MODEL.md` sits untracked in root and payload awaiting Winston's deliberate commit (it reads as #12 input — local model provisioning). `Claude outputs/` is now gitignored and payload-excluded because the desktop app will recreate it; one earlier file from it is preserved at `_claude-outputs-preserved` beside the repository. Use explicit path adds, not `git add -A`, while those files remain untracked.

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands; whether those commands genuinely exercise the criteria is an architect-quality question. Acceptance justifies but does not perform merge, publication, or closure. No credential belongs in configuration, packets, reports, ledgers or logs. Model-performance calibration remains #12, now carrying both #7's run-4 profile and #8's review-economics observations (two ~110K-token subagent reviews from 13–15 KB packets). Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
