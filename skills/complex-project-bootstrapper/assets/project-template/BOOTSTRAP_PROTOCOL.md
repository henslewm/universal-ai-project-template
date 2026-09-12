# Interactive Bootstrap and Autonomy Activation Protocol

Issue: #2

## Purpose

A new project must not enter autonomous execution merely because files were generated. Bootstrap recovers known facts, asks only material unresolved questions, produces a reviewable architecture package, and requires explicit user approval of that exact package before autonomous work can begin. Setup, review, and activation are separate operations.

## Canonical states

`NEW -> ORIENTING -> INTAKE -> ARCHITECTING -> AWAITING_APPROVAL -> ACTIVE`

Alternate states: `NEEDS_INPUT`, `BLOCKED`, `REVISION_REQUESTED`, `ARCHIVED`.

The generator records `INTAKE` with autonomy off. Only `scripts/bootstrap_gate.py activate` may transition a ready `AWAITING_APPROVAL` package to `ACTIVE` through the explicit approval interaction below.

## Stage 1 — ORIENT

Before questioning the user:

- identify the selected canonical profile: `software-hardware`, `family-law`, or `civil-rights-nc`;
- inspect repository instructions, project state, decisions, open loops, sources, risks, branch and recent relevant history;
- inspect authorized connectors/sources when they can answer an intake question without user repetition;
- classify recovered information as verified, proposed/defaulted, unresolved, or conflicting;
- determine greenfield versus existing-project mode.

Never treat prior chat as the sole durable source for a material architecture fact.

For an initialized project, preserve its records, evidence, configuration, and approval history. The generator refuses a destination with `config/bootstrap.json` or an initialized `config/project.json`; do not delete those files or reset template mode to bypass the refusal. Recover missing control files through a preservation-oriented retrofit. For a project already using this gate, revise its existing package and use the review operation below instead of generating over it.

## Stage 2 — OBJECTIVE / INTAKE

Resolve the minimum information required to architect the project:

- project identity and desired outcome;
- observable definition of done;
- explicit non-goals;
- priorities, deadlines and constraints that materially affect architecture;
- authoritative source/evidence locations;
- privacy/security/evidence restrictions;
- available execution resources and external dependencies;
- user-reserved consequential actions.

Questions are conditional. If a value is already verified in durable state, do not ask it again. If a default cannot materially change architecture, scope or risk, use the default and disclose it in the approval packet.

Save recovered intake in an optional JSON answers file. Select one canonical profile and generate into a new/empty directory, or tailor an uninitialized template repository in place:

```bash
python scripts/bootstrap_project.py --interactive --answers verified-intake.json --profile software-hardware --destination ../my-project --no-git
```

Omit `--answers verified-intake.json` when no answers file exists. Substitute `family-law` or `civil-rights-nc` for the profile as appropriate. Use `--destination .` only for an uninitialized template repository. The interactive collector reuses supplied fields and asks only missing common intake and profile orientation fields; it does not invent the architecture. Optional proposal data belongs under the answers file's `bootstrap` object.

The generator writes tailored project files, `config/project.json`, `config/bootstrap.json` in `INTAKE` with false/null approval metadata, and an initial `BOOTSTRAP_REVIEW.md` listing readiness gaps. `--no-git` keeps this preparation separate from Git initialization. Approval records and old review packets are excluded from template copies, including unsuccessful generation from an already-approved source. Neither generated files, a passing repository validator, nor a commit or push activates the project.

Domain-specific intake is supplied through the `domain` extension. This common protocol requires the extension point but does not preempt the detailed domain work assigned to #9, #10 and #11.

## Stage 3 — ARCHITECT

The strongest appropriate architect completes `config/bootstrap.json` and keeps the project documents consistent with it. The package contains:

- project charter;
- architecture/case/claim/component boundaries;
- milestone and dependency graph;
- source/evidence model;
- initial risk register;
- capability-tier/model-routing policy;
- GitHub execution policy;
- explicit human-intervention conditions;
- assumptions and unresolved matters.

Use `architecture` for the summary, boundaries, milestones and dependencies; `routing.policy` for model/cost policy; `workflow.policy` for GitHub execution and routine permissions; `human_gates` for reserved actions; `risks` for the assessed risks; and `unresolved` for architecture blockers. Preserve the project, sources, and applicable `domain` orientation data recovered during intake. Dependencies use exact milestone names as `prerequisite -> dependent`; the validator rejects unknown nodes and cycles. Resolve blockers before review; `unresolved` must then be an empty list. Document any nonblocking assumptions in the package.

The architect may propose defaults but may not approve its own architecture on the user's behalf. `python scripts/validate_bootstrap.py config/bootstrap.json` checks structural consistency and current file bindings during setup; success alone does not mean the package is ready or active. The review operation refreshes those bindings and enforces readiness.

## Stage 4 — REVIEW

From the generated project's root, run:

```bash
python scripts/bootstrap_gate.py review
```

The operation first revokes any previous approval and records `REVISION_REQUESTED`. It snapshots the current `config/project.json` into `configuration`, computes SHA-256 hashes of UTF-8 text with normalized LF line endings for `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md` into `documents`, and checks readiness. Only a ready package is written as `AWAITING_APPROVAL`. Failure leaves autonomy off; resolve the reported problems and run review again.

The generated `BOOTSTRAP_REVIEW.md` presents:

1. objective and definition of done;
2. architecture summary and boundaries;
3. milestones/dependencies;
4. sources/evidence assumptions;
5. major risks;
6. routing/cost policy;
7. actions autonomy may take without interruption;
8. actions reserved to the user;
9. domain orientation and unresolved blockers;
10. the configuration snapshot, including disclosed defaults, and bound document hashes;
11. the architecture fingerprint to be approved.

Present the package and the bound documents to the user. If a revision is needed, revise the JSON and documents, then run review again. Do not manually preserve an old approval across a revision.

## Stage 5 — ACTIVATE

Only when the user has explicitly authorized the approval interaction, run:

```bash
python scripts/bootstrap_gate.py activate
```

The command requires a valid `AWAITING_APPROVAL` package, presents that exact package, and asks for the approving user's identity and the exact text `APPROVE <fingerprint>`. There is no noninteractive autoapprove option. An agent must not invent an identity, supply its own approval, or treat a general instruction to continue as approval of this package. Automated activation tests must use disposable fixtures, never a real project's state.

If the response is affirmative and the package and bound files have not changed during the interaction, activation writes the receipt in `config/bootstrap.json`:

- `approval.approved = true`;
- approving identity;
- UTC timestamp;
- fingerprint of the exact architecture package approved.

The command validates before saving `ACTIVE`. `BOOTSTRAP_REVIEW.md` remains the exact pre-approval proposal; the JSON approval record is the receipt. Then verify:

```bash
python scripts/validate_bootstrap.py config/bootstrap.json --require-active
```

A generic repository creation, script completion, generated charter, previous approval of another architecture version, model assertion, or absence of objections is not approval.

## Architecture fingerprint

The fingerprint is SHA-256 over canonical JSON for `schema_version`, `domain_profile`, `project`, `architecture`, `sources`, `risks`, `routing`, `workflow`, `human_gates`, `domain`, `unresolved`, `configuration`, and `documents`. State and approval metadata are excluded. Configuration and document bindings make edits outside the bootstrap JSON detectable too: startup validation compares the snapshot and hashes with the current repository files.

If one of those fields changes after approval, the stored fingerprint no longer matches and autonomous execution must be considered inactive until the change is resolved under the applicable architecture-change policy.

## Domain extension contract

Every canonical branch may add structured fields under `domain`, but may not weaken the common gate. Domain extensions may add required questions, evidence rules, validators and human gates. They may not create an alternate path to `ACTIVE`.

Minimum domain orientation targets:

- `software-hardware`: hardware/firmware identity, protocols/interfaces, authoritative specifications, software/deployment baseline, simulator/HIL resources, known-good/failing paths and physical-access constraints.
- `family-law`: court/case/procedural posture, controlling orders, pending matters/deadlines, evidence/discovery sources, ranked objectives, disputed issues and preservation constraints.
- `civil-rights-nc`: forum/jurisdiction posture, potential defendants/roles/capacities, alleged rights/theories, procedural history, evidence sources, limitations/accrual posture and requested remedies.

The common implementation requires only the initial profile orientation fields. Detailed domain schemas remain owned by #9/#10/#11. Canonical templates carry snapshots of the existing domain documents; these snapshots do not represent completion of those detailed domain workstreams.

## Autonomy after activation

Once `ACTIVE`, agents may execute the approved architecture according to `AUTONOMY_CONTROL_PLANE.md`: decompose work, create/update GitHub work records, execute bounded tasks, validate, review, escalate, accept/merge when authorized, update durable state and continue to the next unblocked task.

Routine work within the approved scope and existing permissions does not need renewed approval for each step. A material architecture change or changed bound configuration/document invalidates the current approval and requires review and a new user decision. Independently consequential external actions remain reserved as defined by the control plane. Activation neither configures providers nor expands tool, connector, or external-system permissions.

## Recovery

After interruption or a new model/session:

1. Read current repository instructions and durable state.
2. Before autonomous substantive work, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root.
3. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, a matching fingerprint, and current configuration/document bindings.
4. A missing, invalid, or inactive state, changed bound files, or unavailable runtime/validator means no autonomous execution. Resume the appropriate bootstrap/review stage with `prompts/INTERACTIVE_BOOTSTRAP.md`, or prepare a runtime handoff within existing permissions.

## Local gate limits

This local gate prevents normal workflow bypass and detects stale approvals against the files it binds. It does not authenticate the human entering an identity, provide a tamper-proof audit trail, or constrain actors who can rewrite the validator, gate code, or approval records. Existing access controls and explicit external-action permissions remain necessary.
