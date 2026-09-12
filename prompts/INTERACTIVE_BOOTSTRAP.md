# Interactive Bootstrap Operator Prompt

Use this procedure when starting or retrofitting a project. `BOOTSTRAP_PROTOCOL.md` is controlling for the common gate.

## 1. Orient before asking

Read the repository startup instructions and durable state. Inspect available authorized sources/connectors that can resolve project facts. Determine the canonical profile (`software-hardware`, `family-law`, or `civil-rights-nc`) and whether the project is greenfield or existing work.

Build a private intake table with four statuses: VERIFIED, PROPOSED DEFAULT, UNRESOLVED, CONFLICTING. Do not ask the user for VERIFIED information merely to fill a questionnaire.

## 2. Ask in small stages

Ask only unresolved questions whose answers materially affect objective, definition of done, architecture boundaries, dependencies, authoritative sources/evidence, risk, cost/routing posture, or human intervention conditions. Prefer a few related questions at a time. Explain a proposed default when it avoids an unnecessary interruption.

The domain profile may add questions under the common `domain` extension. It may not weaken the common approval gate.

## 3. Construct the architecture package

Populate `config/bootstrap.json` progressively. During intake/setup its state is not `ACTIVE`. Before approval, the package must contain the project objective/definition of done/non-goals/constraints, architecture summary/boundaries/milestones/dependencies, authoritative source locations, risks, routing policy, human gates, and applicable domain extension data.

Run:

`python scripts/validate_bootstrap.py config/bootstrap.json`

A valid setup state means the file is structurally coherent. It does **not** mean the project is active.

## 4. Present the approval packet

Set state to `AWAITING_APPROVAL`, leave approval false/null, and present the user a concise review containing the objective, architecture, milestones/dependencies, sources/evidence assumptions, risks, routing/cost posture, autonomous permissions, reserved actions, unresolved assumptions, and the fingerprint printed by:

`python scripts/validate_bootstrap.py config/bootstrap.json --fingerprint`

Ask the user to approve or revise that exact architecture package.

## 5. Record approval

Only after an explicit affirmative decision about the presented package may the approval record be populated and state changed to `ACTIVE`. Record approving identity, timestamp, and the fingerprint of the material architecture. Then run:

`python scripts/validate_bootstrap.py config/bootstrap.json --require-active`

Do not infer approval from silence, previous unrelated approval, repository creation, generated files, or a model's own recommendation.

## 6. Resume/recovery rule

Every new model/session checks `config/bootstrap.json` before autonomous substantive work. Continue autonomously only if the validator confirms `ACTIVE` and the stored fingerprint still matches. If material architecture has changed, the fingerprint mismatch is a stop condition requiring resolution under the architecture-change policy.
