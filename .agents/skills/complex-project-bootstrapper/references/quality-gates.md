# Quality Gates

Before completion verify:

- Required control files and native entrypoints exist.
- Generated projects have no unresolved `{{PLACEHOLDER}}` tokens.
- JSON and TOML configuration parses.
- `CLAUDE.md` imports resolve.
- Canonical skill and native copies match.
- Connector scopes and write boundaries are explicit.
- Skill selections have a reason and status.
- Source index and handoff exist.
- Sensitive files and secrets are not tracked.
- Repository validator passes.
- Commit and push claims are verified with actual identifiers/status.

For bootstrap preparation and review verify:

- Verified common intake and profile orientation are reused; only missing material fields are asked. Defaults are disclosed.
- New setup targets a new/empty directory or uninitialized template repository. Initialized project records, evidence, and approval state are preserved through retrofit/review; rebootstrap refusal is not bypassed.
- Generated `config/bootstrap.json` is `INTAKE` with false/null approval metadata and autonomy off. `BOOTSTRAP_REVIEW.md` identifies readiness gaps. Passing repository or inactive-state validation is not activation.
- The architect completes project objective/definition of done, architecture summary/boundaries/milestones/dependencies, sources, assessed risks, routing/workflow policies, human gates, and the selected profile's orientation. Architecture blockers are resolved before review; `unresolved` is empty.
- `python scripts/bootstrap_gate.py review` revokes prior approval before checking readiness. It snapshots current `config/project.json` and SHA-256 hashes of `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md`. Only readiness success writes `AWAITING_APPROVAL` and a ready review.
- The review and bound documents disclose scope, milestones/dependencies, sources, risks, routing/cost policy, routine permissions, reserved actions, domain orientation, defaults, and the exact fingerprint. Detailed domain work remains assigned to #9/#10/#11; existing domain-document snapshots are not evidence of its completion.

For activation and continuation verify:

- `python scripts/bootstrap_gate.py activate` is used only after explicit user authorization for the approval interaction. It presents the exact package and asks for approving identity plus `APPROVE <fingerprint>`. There is no noninteractive autoapprove option; the agent does not invent approval. Automated activation tests operate only on disposable fixtures.
- A successful activation has an approval receipt in `config/bootstrap.json` with approving identity, UTC timestamp, and the matching architecture fingerprint. The review file remains the pre-approval proposal.
- `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` passes against current repository files before autonomous substantive work in each session. Fingerprinted fields include `domain`, `workflow`, `unresolved`, `configuration`, and `documents`; configuration and document changes invalidate stale bindings.
- Missing, invalid, or inactive state, changed bindings, or unavailable runtime means no autonomous execution. Resume bootstrap/review or provide a runtime handoff within existing permissions. Report inactive readiness honestly rather than claiming activation.
- Routine approved-scope work after activation proceeds within existing permissions; reserved actions and consequential external writes retain explicit-authority requirements. Setup/activation does not configure providers or grant access.

The local gate prevents normal workflow bypass and detects stale approvals. It does not authenticate humans, create a tamper-proof audit trail, or constrain actors who rewrite gate code or approval records. Validate and describe that boundary accurately.
