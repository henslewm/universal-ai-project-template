# Current Handoff

- **Prepared:** 2026-09-16 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `issue-10-family-law-domain` (off `main` at `d2350ec25474816545b4418a4c8c5cd97516e2c6`, PR #35 / Issue #9 follow-up, ADR-058). Confirm the current head with `git log --oneline -1` rather than trusting a figure here.
- **Scope:** Issue #10 (complete high-conflict NC family-law template), session 1: design approved and posted to the issue, core mechanism delivered. Not yet closed — the repeat-dogfood acceptance run, PR, and Codex review loop remain.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10) — read its design comment before continuing. Issues #2 through #9 are closed through merged PRs #15 to #34; #9's post-merge follow-up is merged through PR #35. Read each closed child's completion comment for the limitations it carried forward.

## What this session (#10, session 1) delivered

Following the interactive-bootstrap-then-decompose pattern #9 used: a design was proposed, approved by Winston, then implemented and posted as [a comment on Issue #10](https://github.com/henslewm/universal-ai-project-template/issues/10). The mechanism reuses #9's acceptance-controller split (machine-runnable command vs. non-implementer attestation bound to a digest-referenced evidence record) rather than inventing a parallel one:

- `config/domains/family-law.schema.json` and `scripts/family_law.py`, registered in `work_packet.DOMAIN_MODULES`, add `workstream` (the charter's eleven linked-workstream categories), `fact_assertions` (each declared `ALLEGATION`/`DISPUTED_FACT`/`INFERENCE`/`LEGAL_PROPOSITION`/`UNKNOWN` and citing a contract source), `source_references`, `adverse_authority` (required non-empty for any `LEGAL_PROPOSITION` assertion — new, no software-hardware precedent), a three-rung ladder (`structural`, `citation_linked` machine-runnable; `primary_source_verified` attested), and `fact_basis` declarable only as `UNVERIFIED_FACT` or `NOT_FACT_ASSERTING` — `VERIFIED_FACT` is earned in the ledger, never authored.
- One deliberate addition beyond the hardware mirror: unlike a hardware pass/fail, a primary source can legitimately contradict the claim it was consulted to check. `status` reports a third earned outcome, `CONTRADICTED_BY_SOURCE`, surfaced ahead of every other reason so a genuine adverse finding is never read as merely unverified; an inconclusive review is reported unverified with that reason stated. Neither ever earns `VERIFIED_FACT`.
- `DOMAIN_FIELDS["family-law"]` expanded from 3 thin orientation fields to the 10 the charter actually requires (`case_identity`, `controlling_orders`, `objectives_and_deadlines`, `discovery`, `evidence`, `financial_support`, `parenting_custody`, `adverse_facts`, `appellate_preservation`, `reserved_actions`), kept synchronized from the start across `scripts/validate_bootstrap.py`, `config/bootstrap.schema.json`, and the bootstrapper's intake reference — applying #9's ADR-040 lesson proactively instead of discovering the drift later.
- A small fictional four-packet worked decomposition under `examples/family-law/` (docket/deadline tracking; a support-calculation packet with a checked income inference; a custody allegation checked against a fictional transcript that turns out to contradict it, deliberately exercising `CONTRADICTED_BY_SOURCE`; a legal-proposition packet with cited adverse authority), plus a bound `source-record.example.json`.
- `tests/test_family_law.py` (33 tests) exercising the domain schema, the attestation-binding rules, the `CONTRADICTED_BY_SOURCE`/inconclusive derivations, the CLI, and the bootstrap intake fields.
- `templates/family-law/PROFILE.md` rewritten to describe the now-structural mechanism, following #9's `PROFILE.md` shape.
- Three pre-existing generic fixtures/tests had to be adjusted because `family-law` is now a *registered* domain profile rather than the stock example of an unregistered one: `tests/test_work_packet.py`'s and `tests/test_software_hardware.py`'s "domain rules apply only to the registered profile" demonstrations now use `civil-rights-nc` instead; two `tests/test_github_ledger.py` profile-mismatch fixtures do the same; `examples/work-packets/family-law.contract.json`'s `domain` block was brought into the new closed schema.

See ADR-059 for the full design rationale and alternatives considered.

## What #9 and PR #35 left you (background, unchanged this session)

`docs/ISSUE_9_VALIDATION.md` is the full record of #9's own acceptance and 23-round Codex review (ADR-041–ADR-055). Its two generic-controller lessons — evidence-binding is several checks, not one (revision, contract hash, dispatch/artifact identity, an observation-time bound), and a stored shortfall-marked record must replay for history but never justify a *new* acceptance (ADR-053) — were applied to family-law's mechanism from the start rather than rediscovered, though #10's own review will likely still find edges specific to this domain (R-012: stop for diagnosis when a review class recurs, and #9's own submission-binding class took five separate review rounds to close completely — expect this pattern to recur here too, and look for the actual invariant rather than patching the first reproduction a reviewer hands you). PR #35 (ADR-056–058) fixed a hardware-evidence `validation_id` binding gap and completed the sample adapter's zero-timeout `receive()` fix; unrelated to #10.

## Verified state

394 tests pass on Windows (`unittest discover -s tests -p "test_*.py"` from the repo root — plain `discover` finds nothing; 361 before this session plus 33 new in `tests/test_family_law.py`). `python scripts/validate_project.py` passes 81 required paths. `python scripts/sync_skills.py --check` reports 0 differing files after running `sync_skills.py` (without `--check`) to propagate the canonical `scripts/`, `config/`, `templates/`, and `skills/complex-project-bootstrapper/` changes into the `.agents/skills`, `.claude/skills`, and payload mirrors. Nothing has been pushed, and no PR exists yet for this branch.

## Exact next action

Continue Issue #10 on `issue-10-family-law-domain`: run the repeat-dogfood acceptance exercise (a fresh ledger, same-family then cross-family review, no waiver unless Winston authorizes one — the same shape as `_acceptance-demo-9b`), then open the PR and run the Codex review loop to a clean result before asking for merge authorization. The construction branch `issue-9-software-hardware-domain` remains until the later authorized cleanup; do not delete it outside that cleanup.

## Limitations carried forward (outside #9/#10; maintainer's call under master #14)

OL-016 (template-packaging defects: generated projects inherit a payload-drift CI check they cannot pass; `sync_skills.py` never detects an obsolete payload file; development decision history ships into fresh projects) remains open from #8's closure, unaddressed by #9 or #10.

## Environment and tooling notes

The template is deliberately unactivated: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`. Everything proceeds as the maintainer's explicitly authorized template maintenance.

This checkout has no repository virtualenv and must not gain one; the working interpreter with `jsonschema==4.26.0` is at `%TEMP%\uaipt-venv\Scripts\python.exe`. Run the Windows suite with `unittest discover -s tests -p "test_*.py"` from the repository root — plain `discover` finds nothing. Under WSL, discover each suite individually (`discover -s tests -p test_acceptance.py`, etc.); importing by dotted module name fails because `tests/` is not a package. `scripts/sync_skills.py` (without `--check`) mirrors the tree into the distribution payload; `--check` is what CI enforces.

## Boundaries

The acceptance controller enforces independence against recorded declarations it cannot authenticate; a misdeclared reviewer family defeats the cross-family gate, and the record makes that auditable rather than invisible (R-010). The deterministic gate executes only architect-committed contract commands and does not sandbox them. A source verification record is an operator's declaration the controller cannot authenticate; the digest makes it auditable, not true. Acceptance justifies but does not perform merge, publication, or closure. No credential, restricted case fact, or real party/case identity belongs in this repository's examples, fixtures, configuration, packets, reports, ledgers or logs — every family-law example in this template is deliberately fictional and declares `domain.synthetic: true`. Model-performance calibration remains #12. Do not edit the locked master, and do not delete construction branches outside the later authorized cleanup.
