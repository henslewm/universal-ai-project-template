# Universal New-Project Bootstrap Prompt

Use the repository containing this prompt as the template for a new complex project.

Follow `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md`. First inspect available context, files, authorized connectors, and repository state. Recover verified facts before asking questions; distinguish facts, proposed defaults, unresolved matters, and conflicts. Ask only missing, decision-relevant questions in small related stages. Do not infer approval from this request to set up the project.

The intake must cover, only where missing:

1. Project name and one-sentence desired outcome.
2. Observable definition of done, required deliverables, and target date or urgency.
3. Canonical profile (`software-hardware`, `family-law`, or `civil-rights-nc`), jurisdiction/version where relevant, risk tier, and sensitivity.
4. Authoritative source locations and which sources control when they conflict.
5. AI surfaces to support: ChatGPT, Codex, Claude web, Claude Code, or others.
6. External systems/connectors needed and the read/write boundary for each.
7. Repeated workflows that deserve a skill, plus required output formats.
8. Non-negotiable constraints, exclusions, approval gates, and people responsible.

Reuse my supplied answers and verified repository/source facts. Ask only missing common intake and profile orientation fields. Propose nonmaterial defaults transparently; do not invent architecture, source access, or permission grants to fill gaps. Detailed domain design remains assigned to #9/#10/#11; the canonical templates carry snapshots of existing domain documents.

Then perform the setup:

1. Choose a new/empty destination, or tailor an uninitialized repository created with GitHub **Use this template** in place. Preserve the base template when creating a separate project. Rebootstrap of initialized projects is refused: preserve their records and evidence, add only missing controls through a retrofit, and revise/review any existing bootstrap package instead of overwriting it.
2. Save recovered common intake in an optional `verified-intake.json`, with profile orientation and any existing proposal under `bootstrap`. Run the generator using the appropriate command below. It writes tailored project files, `config/project.json`, `config/bootstrap.json` in `INTAKE` with autonomy off, and an initial `BOOTSTRAP_REVIEW.md` identifying readiness gaps.
3. Have the architect complete the bootstrap JSON's project, architecture summary/boundaries/milestones/dependencies, sources, risks, `routing.policy`, `workflow.policy`, `human_gates`, and profile `domain` data. Record blockers in `unresolved` and resolve them before review. Keep the charter, connector plan, skill plan, domain profile, and project configuration consistent with the proposal.
4. Preserve universal instructions and native entrypoints. Select the minimum useful connectors and trusted skills, document their reasons and permission boundaries, and preserve sensitive originals in the approved source system. Proposing routing or connectors does not configure providers or grant access.
5. Run `python scripts/validate_project.py` and correct errors. An inactive but structurally valid setup remains inactive.
6. From the generated project's root, run `python scripts/bootstrap_gate.py review`. This first revokes any previous approval, snapshots `config/project.json` and SHA-256 hashes of the four bound documents, and checks readiness. Only success writes `AWAITING_APPROVAL` and a ready `BOOTSTRAP_REVIEW.md`.
7. Present the review and bound `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md`. Include objectives, boundaries, dependencies, sources, risks, routing/cost posture, routine permissions, reserved actions, domain orientation, defaults, and the exact fingerprint. Resolve requested revisions and rerun review before asking for approval.
8. Only after I explicitly authorize the approval interaction, run `python scripts/bootstrap_gate.py activate`. It presents the exact package and asks for my identity plus `APPROVE <fingerprint>`. Do not invent approval or use an automatic affirmative response. There is no noninteractive autoapprove option. The approval receipt is recorded in `config/bootstrap.json`; the review file stays the pre-approval proposal.
9. Verify with `python scripts/validate_bootstrap.py config/bootstrap.json --require-active`. Run that check again before autonomous substantive work in each session; it checks current configuration/document bindings too. Missing, invalid, or inactive state, changed bound files, or no runtime means no autonomy. Resume bootstrap/review or prepare a runtime handoff.
10. After activation, routine work within the approved scope and existing permissions may proceed without approval for every step. Reserved actions, material architecture changes, and consequential external writes retain their explicit-authority requirements. Initialize Git, commit, or publish only within actual authorization; never claim a commit or push without verification.
11. Return the repository path, bootstrap state and autonomy status, review path, files tailored, connectors/skills and their permission posture, web Project setup steps, validation results, verified commit/push status, and next actions. Do not label inactive setup as an active project.

For command-line execution, use the matching mode:

```bash
# New/empty directory; reuse verified intake if available
python scripts/bootstrap_project.py --interactive --answers verified-intake.json --profile software-hardware --destination ../my-project --no-git

# Uninitialized GitHub "Use this template" repository: tailor in place
python scripts/bootstrap_project.py --interactive --profile software-hardware --destination . --no-git
```

Omit `--answers` and its filename if no answers file exists. Replace the example profile with `family-law` or `civil-rights-nc` as appropriate.

The local gate prevents normal workflow bypass and detects stale approvals. It does not authenticate the approving human or constrain actors who rewrite gate code or approval records. Automated activation tests must use disposable fixtures, never a real project.
