# Interactive Bootstrap and Autonomy Activation Protocol

Issue: #2

## Purpose

A new project must not enter autonomous execution merely because files were generated. Bootstrap is a staged architecture negotiation. The repository first recovers what is already known, asks only material unresolved questions, produces a reviewable architecture package, and requires explicit user approval before autonomous work can begin.

## Canonical states

`NEW -> ORIENTING -> INTAKE -> ARCHITECTING -> AWAITING_APPROVAL -> ACTIVE`

Alternate states: `NEEDS_INPUT`, `BLOCKED`, `REVISION_REQUESTED`, `ARCHIVED`.

Only the activation operation may transition `AWAITING_APPROVAL` to `ACTIVE`.

## Stage 1 — ORIENT

Before questioning the user:

- identify the selected canonical profile: `software-hardware`, `family-law`, or `civil-rights-nc`;
- inspect repository instructions, project state, decisions, open loops, sources, risks, branch and recent relevant history;
- inspect authorized connectors/sources when they can answer an intake question without user repetition;
- classify recovered information as verified, proposed/defaulted, unresolved, or conflicting;
- determine greenfield versus existing-project mode.

Never treat prior chat as the sole durable source for a material architecture fact.

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

Domain-specific intake is supplied through the `domain` extension. This common protocol requires the extension point but does not preempt the detailed domain work assigned to #9, #10 and #11.

## Stage 3 — ARCHITECT

The strongest appropriate architect produces:

- project charter;
- architecture/case/claim/component boundaries;
- milestone and dependency graph;
- source/evidence model;
- initial risk register;
- capability-tier/model-routing policy;
- GitHub execution policy;
- explicit human-intervention conditions;
- assumptions and unresolved matters.

The architect may propose defaults but may not approve its own architecture on the user's behalf.

## Stage 4 — REVIEW

Set state to `AWAITING_APPROVAL` and present a compact approval packet containing:

1. objective and definition of done;
2. architecture summary and boundaries;
3. milestones/dependencies;
4. sources/evidence assumptions;
5. major risks;
6. routing/cost policy;
7. actions autonomy may take without interruption;
8. actions reserved to the user;
9. unresolved assumptions or conflicts;
10. the architecture fingerprint to be approved.

If the user requests a material revision, transition to `REVISION_REQUESTED`, revise the architecture package, compute a new fingerprint, and return to `AWAITING_APPROVAL`.

## Stage 5 — ACTIVATE

Activation requires an explicit affirmative user decision about the presented architecture. Record:

- `approval.approved = true`;
- approving identity;
- UTC timestamp;
- fingerprint of the exact architecture package approved.

Then run the bootstrap validator. Transition to `ACTIVE` only when validation succeeds.

A generic repository creation, script completion, generated charter, previous approval of another architecture version, model assertion, or absence of objections is not approval.

## Architecture fingerprint

The fingerprint binds approval to the material architecture. Compute SHA-256 over a canonical JSON representation of the fields that materially define autonomy: domain profile, project objective/definition of done/non-goals/constraints, architecture, sources, risks, routing policy and human gates. Exclude approval metadata itself.

If one of those fields changes after approval, the stored fingerprint no longer matches and autonomous execution must be considered inactive until the change is resolved under the applicable architecture-change policy.

## Domain extension contract

Every canonical branch may add structured fields under `domain`, but may not weaken the common gate. Domain extensions may add required questions, evidence rules, validators and human gates. They may not create an alternate path to `ACTIVE`.

Minimum domain orientation targets:

- `software-hardware`: hardware/firmware identity, protocols/interfaces, authoritative specifications, software/deployment baseline, simulator/HIL resources, known-good/failing paths and physical-access constraints.
- `family-law`: court/case/procedural posture, controlling orders, pending matters/deadlines, evidence/discovery sources, ranked objectives, disputed issues and preservation constraints.
- `civil-rights-nc`: forum/jurisdiction posture, potential defendants/roles/capacities, alleged rights/theories, procedural history, evidence sources, limitations/accrual posture and requested remedies.

Detailed domain schemas remain owned by #9/#10/#11.

## Autonomy after activation

Once `ACTIVE`, agents may execute the approved architecture according to `AUTONOMY_CONTROL_PLANE.md`: decompose work, create/update GitHub work records, execute bounded tasks, validate, review, escalate, accept/merge when authorized, update durable state and continue to the next unblocked task.

A true architecture change invalidates the activation fingerprint and requires a new user decision. Independently consequential external actions remain reserved as defined by the control plane.

## Recovery

After interruption or a new model/session:

1. read `config/bootstrap.json` if present;
2. validate it;
3. recompute the architecture fingerprint;
4. continue autonomously only when state is `ACTIVE`, approval is explicit, and fingerprint matches;
5. otherwise resume the appropriate bootstrap/review state rather than guessing approval from chat history.
