# Autonomous Project Control Plane

## Objective

Run complex projects with the lowest practical total cost per accepted result while preserving correctness, traceability, evidence integrity, and the ability for a stronger model or the user to intervene when the architecture itself must change.

The repository is the durable control plane. Chat history is not authoritative project state.

## Operating phases

### Phase 0 — Interactive setup

Autonomy is **off** until the initial project setup is complete. The setup agent conducts a concise interactive intake, resolves material ambiguities, identifies authoritative sources, proposes the architecture and work decomposition, and presents a project charter for approval.

Required outputs before activation:

1. Approved `PROJECT_CHARTER.md`.
2. Approved system/case architecture and boundaries.
3. Initial milestones and dependency graph.
4. Initial risk register.
5. Model-routing and cost policy.
6. Source/evidence locations and provenance rules.
7. Human-intervention triggers.
8. GitHub workflow and branch/PR policy.

Approval of this foundation is the **Autonomy Activation Gate**.

### Phase 1+ — Autonomous execution

After activation, routine execution proceeds without asking for permission at each step. Within the approved architecture, agents may autonomously:

- decompose approved milestones into bounded work packets;
- create/update GitHub issues and comments;
- assign dependency relationships and execution order;
- create working branches;
- implement or draft within an approved task contract;
- run local tests, validators, linters, builds, simulations, or evidence checks;
- iterate within the bounded retry policy;
- route or escalate work between model tiers;
- open and update pull requests;
- perform independent model review;
- post test/review evidence to the issue and PR;
- merge when all required gates pass and repository policy permits it;
- update project state, decisions, risks, and open loops;
- move to the next unblocked task.

## Human-intervention gate

The system stops and requests approval when the architect determines that an **architecture change** is required.

An architecture change includes a material change to any approved system boundary, claim/case theory framework, public interface, evidence schema, security model, dependency topology, persistence model, deployment topology, controlling legal theory, jurisdictional posture, or project scope that would invalidate existing task contracts or materially alter downstream work.

An implementation detail, ordinary bug fix, bounded refactor, test change, task reprioritization, model escalation, or clarification that remains inside an approved contract is **not** an architecture change.

The system must also stop when an action is outside repository autonomy and is independently consequential, such as filing a court document, sending an external communication, deleting or altering original evidence, exposing a secret, making a purchase, changing access permissions, or taking another irreversible external action. Drafting and preparation remain autonomous; execution of the external act requires explicit authority.

## Architect role

The architect is the most capable available reasoning tier. Its principal job is not routine production. It:

- converts goals into architecture and milestones;
- breaks milestones into independently testable work packets;
- defines interfaces, inputs, outputs, dependencies, non-goals, acceptance criteria, and evidence requirements;
- assigns minimum and maximum model tiers and reasoning effort;
- assigns retry budgets and escalation paths;
- determines whether a failed task is an implementation failure, contract failure, or architecture failure;
- reviews milestone integration and systemic risk;
- invokes the human-intervention gate only when the approved architecture must materially change.

The architect should not repeatedly re-enter ordinary worker loops.

## Worker rule

Canonical work packets now use `config/work-packet.schema.json` and the local tooling in `WORK_PACKET_PROTOCOL.md`. The schema applies to all three profiles; the latest versioned contract snapshot generates the human-readable issue view. Complete-graph validation checks dependencies before a task is recorded ready. These local records do not independently verify external evidence or authorize execution; the bootstrap gate and subsequent executor/review controls remain necessary.

A worker may solve only the work packet it was given. It may not silently expand scope or redesign the project.

A worker may return only a bounded outcome:

- `PASS` — acceptance criteria satisfied with evidence;
- `FAIL` — current attempt failed, but another bounded attempt is allowed;
- `BLOCKED` — an external dependency or missing fact prevents work;
- `NEEDS_ESCALATION` — the task exceeds the worker's capability tier or retry budget;
- `ARCHITECTURE_CONFLICT` — the task cannot be completed without changing an approved boundary or contract.

New unrelated findings become new GitHub issues. No orphan work and no silent scope expansion.

## Cost objective

Optimize **total cost per accepted result**, not merely API price.

Track, where practical:

- model/provider and capability tier;
- task type and estimated complexity;
- attempts;
- wall-clock time;
- input/output tokens or provider cost when available;
- tests/validation passed;
- review outcome;
- whether escalation was required;
- defects discovered after merge.

Local inference has zero marginal API charge but not zero cost: repeated failure, human delay, context churn, and regression risk count against it.

## Default capability tiers

| Tier | Capability | Current mapping |
|---|---|---|
| T0 Utility | deterministic cleanup, indexing, formatting, narrow extraction | small LM Studio model |
| T1 Local Coder/Analyst | bounded implementation or analysis with objective tests | strongest suitable LM Studio model |
| T2 Economical Cloud | moderate reasoning where local models stall | Mistral API |
| T3 Strong Specialist | difficult implementation, legal analysis, debugging, adversarial review | Claude or Codex/OpenAI |
| T4 Architect | architecture, decomposition, integration diagnosis, high-impact review | strongest available Claude/OpenAI reasoning model |

The task contract specifies a **capability tier**, not a vendor name. Provider mappings may change without changing architecture.

`MODEL_ROUTING.md` implements offline selection through `scripts/model_router.py`: exact contract tiers/effort, risk/complexity floors, estimates of accepted-result cost, bounded escalation/fallback and saved decision replay. Its example resources are disabled and fictional. Actual execution still requires the active bootstrap and permission/dependency/review gates; a routing record grants no execution authority.

## Default bounded escalation

The architect may override this per task.

1. T0/T1: up to 2–3 objective attempts.
2. If failure persists, escalate to T2.
3. T2: up to 1–2 bounded attempts.
4. If failure persists, escalate to T3.
5. T3: diagnose and attempt within the task contract.
6. If T3 concludes the task contract is defective, return to T4.
7. If T4 can repair decomposition without changing architecture, it may do so autonomously.
8. If T4 determines the approved architecture must change, stop for user approval.

Do not blindly traverse every tier. High-risk or inherently complex work may start at T3 or T4.

`FEEDBACK_PROTOCOL.md` implements the local bounded controller: durable reservations, per-task/per-tier limits, repeated-failure fingerprints, focused escalation context and finite architect repair/recovery. It preserves budgets across revisions and blocks worker dispatch on architecture conflict; confirmed architecture changes enter a human-decision state. Model execution, live evidence and GitHub publication remain separate integrations.

## Review economy

Reviewers should receive the smallest sufficient context:

1. work packet contract;
2. relevant diff/draft/result;
3. test or evidence output;
4. relevant interface or controlling-source excerpts;
5. identified risks.

Do not make a premium reviewer reread the entire repository unless system-level context is genuinely required.

High-risk work should use an independent reviewer model when practical. The implementer and reviewer should not be the same strong model by default when a second strong model is available.

## GitHub state machine

Every material work item should move through a visible state:

`PROPOSED -> ARCHITECTED -> READY -> IN_PROGRESS -> VALIDATING -> REVIEW -> MERGED/ACCEPTED -> VERIFIED`

Alternate states: `BLOCKED`, `ESCALATED`, `NEEDS_DECISION`, `SUPERSEDED`, `FAILED`.

The issue thread is the execution ledger. The PR is the change/review ledger. Project-level documents hold only durable state and decisions that should survive individual task closure.

## Completion rule

A task is not complete merely because an agent says it is complete. Completion requires the objective evidence specified by its contract and all required review gates.
