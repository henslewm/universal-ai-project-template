# Interactive Bootstrap Operator Prompt

Use this procedure when starting or retrofitting a project. `BOOTSTRAP_PROTOCOL.md` is controlling for the common gate.

## 1. Orient before asking

Read the repository startup instructions and durable state. Inspect available authorized sources/connectors that can resolve project facts. Determine the canonical profile (`software-hardware`, `family-law`, or `civil-rights-nc`) and whether the project is greenfield or existing work.

Build a private intake table with four statuses: VERIFIED, PROPOSED DEFAULT, UNRESOLVED, CONFLICTING. Do not ask the user for VERIFIED information merely to fill a questionnaire.

## 2. Ask in small stages

Ask only unresolved questions whose answers materially affect objective, definition of done, architecture boundaries, dependencies, authoritative sources/evidence, risk, cost/routing posture, or human intervention conditions. Prefer a few related questions at a time. Explain a proposed default when it avoids an unnecessary interruption.

Save recovered common fields in an optional `verified-intake.json`; put profile orientation and any existing architecture proposal under its `bootstrap` object. The interactive collector reuses supplied fields and asks only missing common intake and profile orientation fields. The domain profile adds required questions under the common `domain` extension (the software-hardware set is complete; family-law and civil-rights remain #10/#11) and cannot weaken the common gate.

## 3. Generate inactive setup, then architect

For a new/empty destination, run from the template root:

```bash
python scripts/bootstrap_project.py --interactive --answers verified-intake.json --profile software-hardware --destination ../my-project --no-git
```

Omit `--answers` and its filename when no answers file exists; substitute `family-law` or `civil-rights-nc` as appropriate. Use `--destination .` only for an uninitialized template repository. The generator creates `config/bootstrap.json` in `INTAKE` with autonomy off, tailored control files, and an initial `BOOTSTRAP_REVIEW.md` with readiness gaps. Canonical templates include snapshots of existing domain documents.

Rebootstrap of initialized projects is refused. Preserve existing records and evidence during a retrofit; add only missing controls. If bootstrap state already exists, revise that package and use review. Do not delete state or reset template mode to bypass preservation checks.

In the generated project, complete `config/bootstrap.json`: project outcome and definition of done, `architecture` summary/boundaries/milestones/dependencies, `sources`, `risks`, `routing.policy`, `workflow.policy`, `human_gates`, and profile `domain` fields. Record architecture blockers in `unresolved` and resolve them before review. Keep `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, `DOMAIN_PROFILE.md`, and `config/project.json` consistent with the proposal.

`python scripts/validate_bootstrap.py config/bootstrap.json` checks structural consistency and current bindings. A valid inactive state is neither review readiness nor activation.

## 4. Present the approval packet

From the generated project's root, run:

```bash
python scripts/bootstrap_gate.py review
```

Review first revokes previous approval and records `REVISION_REQUESTED`. It snapshots `config/project.json` into `configuration` and SHA-256 hashes of UTF-8 text with normalized LF line endings for `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md` into `documents`. It requires complete architecture/routing/workflow, sources, human gates, profile orientation, and no unresolved architecture blockers. Only success writes `AWAITING_APPROVAL` and a ready `BOOTSTRAP_REVIEW.md`.

Present that review and the bound documents, including objectives, architecture, dependencies, sources, risks, routing/cost posture, routine permissions, reserved actions, domain orientation, disclosed defaults, and fingerprint. Request approval or revisions to this exact package. For revisions or failed readiness, resolve the issues and run review again; leave autonomy off.

## 5. Record approval

Only after explicit user authorization for the approval interaction, run:

```bash
python scripts/bootstrap_gate.py activate
```

The command presents the exact `AWAITING_APPROVAL` package and asks for user identity plus `APPROVE <fingerprint>`. Do not supply an agent-created approval or identity; there is no noninteractive autoapprove option. If the package changes during the interaction or the response does not match, activation fails. Automated tests may exercise activation only in disposable fixtures.

Successful activation records `approved`, `approved_by`, the UTC `approved_at`, and `architecture_fingerprint` in `config/bootstrap.json`. The review file remains the pre-approval proposal. Verify success with `python scripts/validate_bootstrap.py config/bootstrap.json --require-active`.

Do not infer approval from silence, previous unrelated approval, repository creation, generated files, or a model's own recommendation.

## 6. Resume/recovery rule

Every new model/session must run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` before autonomous substantive work. Validation checks current configuration/document bindings as well as `ACTIVE`, approval, and the fingerprint. The fingerprint includes `domain`, `workflow`, `unresolved`, `configuration`, and `documents` alongside the common project/architecture fields.

Missing, invalid, or inactive state, changed bound files, or unavailable runtime/validator means no autonomy. Resume bootstrap/review or prepare a runtime handoff within existing permissions. After activation, routine approved-scope work can proceed without repeated approvals; reserved actions and consequential external writes retain their explicit-authority requirements. Activation does not configure providers or expand permissions.

The local gate detects normal workflow bypass and stale approvals; it does not authenticate a human or constrain actors who rewrite gate code or approval records.
