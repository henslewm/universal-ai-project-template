# Bootstrap Foundation Review

State: AWAITING_APPROVAL — autonomy is OFF until explicit activation.
Profile: software-hardware
Architecture fingerprint: `a14797640d639ac831fbd112312a1f3f94eccc6b8e3eda0a4e9e63ba20c399d3`

## Charter

```json
{
  "name": "Universal AI Project Template",
  "objective": "A reusable, repo-backed control plane in which an architect model delegates bounded, machine-checkable work packets to cheaper cloud models and monitors them, so complex AI-assisted work costs less without drift (PROJECT_CHARTER.md, Desired outcome).",
  "definition_of_done": [
    "Cheaper cloud models execute architect-written packets within the per-packet limits, monitored through the acceptance and feedback ledgers (charter).",
    "The software and hardware tracks bootstrap, plan, execute and verify end to end (charter).",
    "Every milestone below is merged with validate_project.py and the unit suite green and an automated review on the exact head (ADR-074)."
  ],
  "non_goals": [
    "Any feature outside the owner's stated requirements and the milestones below (owner, 2026-10-07)",
    "Legal work; it stays archived under archive/legal/",
    "A combined ledger (ADR-089 D)",
    "Savings telemetry and dry runs, issues #12 and #13 (deferred, ADR-089 G and ADR-096)"
  ],
  "constraints": [
    "Preserve authoritative source material and provenance; keep secrets and restricted material out of Git",
    "Simulations or guesses are never acceptable as verification",
    "template_mode stays true and every existing record is preserved",
    "Review cap of 4 automated rounds per pull request (ADR-089 A); worker-attempt default 2 (ADR-089 B)"
  ]
}
```

## Architecture and milestone dependency graph

```json
{
  "summary": "Unchanged template architecture: Markdown control files and validator-checked startup views; Python CLIs for bootstrap and gate, work packets, acceptance, feedback, model routing and the execution harness; the software-hardware profile with hardware and web-ui tracks; the complex-project-bootstrapper skill payload synchronized by sync_skills.py. Approved work is four milestones that complete owner requirements already stated; none adds a new capability beyond them.",
  "boundaries": [
    "Bootstrap and approval gate semantics (bootstrap_gate.py, validate_bootstrap.py) change only with renewed owner approval",
    "Acceptance-controller evidence binding and the work-packet schema change only with owner approval",
    "Merge and review discipline (ADR-074, ADR-063, ADR-089 A) changes only as ADR-094 states it",
    "Permission rules in .claude/settings.json change only as ADR-094 states it",
    "The launcher dispatches only within EXECUTION_HARNESS_PROTOCOL.md and the per-packet budget and attempt limits",
    "Generated-project payload shape and the template_mode contract stay compatible with bootstrap_project.py"
  ],
  "milestones": [
    "Records current",
    "Unknown-cost state",
    "Auto-closeout ADR-094",
    "External worker launcher OL-036"
  ],
  "dependencies": [
    "Records current -> Unknown-cost state",
    "Records current -> Auto-closeout ADR-094",
    "Unknown-cost state -> External worker launcher OL-036"
  ]
}
```

## Sources and evidence map

```json
[
  "Repository control files on main at ff5f5a4: PROJECT_CHARTER.md, DECISIONS.md, OPEN_LOOPS.md, PROJECT_STATE.md, the protocol files",
  "GitHub issues and pull requests of henslewm/universal-ai-project-template, read with gh api",
  "docs/AUDIT_2026-10-03.md section 2 (cost-as-zero defect)",
  "Branch claude/auto-closeout commit 7cca94e (owner direction for ADR-094)",
  "Owner decisions in the session of 2026-10-07 (ADR-096)"
]
```

## Risks

```json
[
  "Auto-merge removes the human merge check; a defective change merges if the automated review misses it (mitigated by ADR-074 exact-head review, green validator and tests, resolved threads, cap of 4)",
  "An automatic launcher spends money on external models; undercounted cost lets budget caps pass (mitigated by landing the unknown-cost state first)",
  "Removing the ADR-091 ask rules removes prompts for issue writes, deletions and gh api writes",
  "The local gate does not authenticate a human or constrain an actor who rewrites gate code (R-004)",
  "A fresh clone fails sync_skills --check and two tests until sync_skills.py builds the gitignored payload"
]
```

## Routing and cost policy

```json
{
  "policy": "The architect session decomposes and integrates; bounded research, edits and records go to the .claude/agents subagents on sonnet; independent review stays at the architect tier (ADR-093). Once the launcher lands, packets may go to the cheapest external or local tier expected to pass acceptance, within per-packet budget and attempt limits (MODEL_ROUTING.md). Automated PR review by Codex or CodeRabbit."
}
```

## GitHub workflow and routine permissions

```json
{
  "policy": "One branch and pull request per milestone. Before merge: validate_project.py and the unit suite green, sync_skills.py --check clean, an automated review on the exact head (ADR-074), every actionable finding answered (ADR-063), at most 4 rounds (ADR-089). The owner merges until ADR-094 lands; after that, auto-merge applies only under its stated conditions. Closeout records per MASTER_INSTRUCTIONS.md."
}
```

## Reserved human actions

```json
[
  "Running bootstrap_gate.py activate (owner only)",
  "Any material architecture change outside the approved milestones",
  "Merging a pull request, until ADR-094 auto-merge lands; afterwards only merges that fail its conditions",
  "Sending, filing or publishing outside this repository, and purchases",
  "Permission changes other than the ADR-094 removal of the ADR-091 ask rules",
  "Deleting or overwriting original evidence, sources or history; force pushes",
  "Raising a launcher budget or attempt limit above the per-packet contract"
]
```

## Domain orientation

```json
{
  "baseline": "main at ff5f5a4 (merge of PR #117, 2026-10-07): validate_project.py passes with 85 required paths; 462 unit tests pass (3 skipped) after sync_skills.py builds the payload. Source: this session's runs on Linux, Python 3.13.",
  "hardware_identity": "None: software-only project; no hardware is in scope",
  "interfaces": "Python CLIs in scripts/ (bootstrap_project, bootstrap_gate, validate_bootstrap, validate_project, work_packet, acceptance, feedback, model_router, execution_harness, sync_skills); JSON schemas config/*.schema.json at schema_version 1.0; Markdown control files; GitHub REST via gh api.",
  "specifications": "BOOTSTRAP_PROTOCOL.md, WORK_PACKET_PROTOCOL.md, ACCEPTANCE_PROTOCOL.md, FEEDBACK_PROTOCOL.md, MODEL_ROUTING.md, EXECUTION_HARNESS_PROTOCOL.md, MASTER_INSTRUCTIONS.md and config/*.schema.json, held in this repository.",
  "environment": "Python 3.11 or newer, Git and the gh CLI on Windows (owner) and Linux (cloud sessions); GitHub Actions workflow validate-project.yml; no deployment target.",
  "known_paths": "Known-good: validate_project.py, the unit suite and sync_skills.py --check after the payload is built (observed 2026-10-07). Known-failing: a fresh clone fails sync_skills.py --check and two tests until sync_skills.py runs (observed 2026-10-07). Unverified: the ADR-091 ask rules live; any real cheaper-model run (only synthetic harness runs exist).",
  "validation_resources": "tests/ unit suite, validate_project.py, validate_bootstrap.py, sync_skills.py --check, the CI workflow, the synthetic harness and fake device examples, and Codex or CodeRabbit review on GitHub.",
  "physical_access": "None: software-only project; no hardware is in scope",
  "architecture_boundaries": "The gate, acceptance binding, work-packet schema, merge and review rules, permission rules and the template payload contract; changes outside the approved milestones need owner approval."
}
```

## Unresolved blockers

```json
[]
```

## Project configuration and disclosed defaults

```json
{
  "template_mode": true,
  "template_version": "1.0.0",
  "created": "2026-08-29",
  "project_name": "Universal AI Project Template",
  "project_slug": "universal-ai-project-template",
  "objective": "A reusable, repo-backed control plane in which an architect model delegates bounded, machine-checkable work packets to cheaper cloud models and monitors them, so complex AI-assisted work costs less without drift (PROJECT_CHARTER.md, Desired outcome).",
  "problem_statement": "All AI models hallucinate, drift and deviate from requests, goals, requirements and specs, so the controls must prevent that; having the strongest model do all the work costs too much, and one chat's memory does not carry across models or sessions (PROJECT_CHARTER.md).",
  "success_criteria": [
    "Cheaper cloud models execute architect-written packets within the per-packet limits, monitored through the acceptance and feedback ledgers (charter).",
    "The software and hardware tracks bootstrap, plan, execute and verify end to end (charter).",
    "Every milestone below is merged with validate_project.py and the unit suite green and an automated review on the exact head (ADR-074)."
  ],
  "deliverables": [],
  "target_date": "",
  "domain": "software-hardware",
  "jurisdiction_or_version": "",
  "risk_tier": "low",
  "sensitivity": "public",
  "owner": "henslewm",
  "ai_clients": [
    "chatgpt",
    "codex",
    "claude",
    "claude-code"
  ],
  "connectors": [
    "github",
    "web"
  ],
  "connector_permissions": {
    "github": "read-and-project-write",
    "web": "read"
  },
  "source_locations": [
    "Repository control files on main at ff5f5a4: PROJECT_CHARTER.md, DECISIONS.md, OPEN_LOOPS.md, PROJECT_STATE.md, the protocol files",
    "GitHub issues and pull requests of henslewm/universal-ai-project-template, read with gh api",
    "docs/AUDIT_2026-10-03.md section 2 (cost-as-zero defect)",
    "Branch claude/auto-closeout commit 7cca94e (owner direction for ADR-094)",
    "Owner decisions in the session of 2026-10-07 (ADR-096)"
  ],
  "repeatable_workflows": [],
  "output_formats": [
    "markdown"
  ],
  "constraints": [
    "Preserve authoritative source material and provenance; keep secrets and restricted material out of Git",
    "Simulations or guesses are never acceptable as verification",
    "template_mode stays true and every existing record is preserved",
    "Review cap of 4 automated rounds per pull request (ADR-089 A); worker-attempt default 2 (ADR-089 B)"
  ],
  "out_of_scope": [
    "Any feature outside the owner's stated requirements and the milestones below (owner, 2026-10-07)",
    "Legal work; it stays archived under archive/legal/",
    "A combined ledger (ADR-089 D)",
    "Savings telemetry and dry runs, issues #12 and #13 (deferred, ADR-089 G and ADR-096)"
  ],
  "domain_profile": "software-hardware"
}
```

## Bound document hashes

```json
{
  "PROJECT_CHARTER.md": "4a116815d04e04393df0f091cf02db253976ecdb8a43bb017e0c4195b3c1f60d",
  "CONNECTOR_PLAN.md": "f1871dc620ceeaa8bda289e04723a96c0ffbb53b2b9434403c4bc289c94167d4",
  "SKILL_PLAN.md": "6d1b8c44b088d462ae588ae81d191bc523878ee66e08eb5c38802df851585e1d",
  "DOMAIN_PROFILE.md": "91d42727ef1a1b26894f5c3e9f6938c01ac8e372544079da97b7140665875e65"
}
```

## Readiness

- Ready for an explicit user decision.

## Bound document: PROJECT_CHARTER.md

# Project Charter

## Project

- **Name:** Universal AI Project Template
- **Slug:** universal-ai-project-template
- **Domain:** (inferred) Multi-model AI project control plane, as a reusable template. Served tracks: software development and serial hardware / hardware-software interfaces. Legal work was archived under `archive/legal/` (owner decision).
- **Risk tier:** Low (owner, 2026-10-07, ADR-096)
- **Sensitivity:** Public (owner, 2026-10-07, ADR-096). The repository is public.
- **Owner:** henslewm
- **Target date:** Not set

## Problem statement

All AI models hallucinate, drift and deviate from requests, goals, requirements and specs, so the controls must prevent that (endorsed "1000%"). (inferred) Having the strongest model do all the work costs too much, and one chat's memory does not carry across models or sessions.

## Desired outcome

A reusable, repo-backed control plane that makes complex, high-stakes AI-assisted work efficient: the owner is "spending money now to save money later." An architect model (Fable, Opus 5.5/6) must delegate intelligently to cheaper cloud models under an explicit contract and monitor them effectively.

## Definition of done (inferred)

- Cheaper cloud models execute architect-written packets within the per-packet limits, monitored through the acceptance and feedback ledgers.
- The software and hardware tracks bootstrap, plan, execute and verify end to end. The ADR-089 freeze was lifted on 2026-10-06 (ADR-093) for two objectives: less drift and token cost at session start, and delegation by default.

## Required deliverables

- **Continuity:** GitHub as durable memory for ChatGPT, Codex, Claude, Claude Code and Mistral.
- **Packets:** the strong model writes bounded, machine-checkable packets; cheaper cloud models execute them.
- **Ledgers:** the existing acceptance and feedback ledgers and the Markdown control files. A combined ledger is not pursued (ADR-089).
- **Domain templates:** the `software-hardware` profile with a `hardware` or `web-ui` track (`instructions/tracks/`). ESP32/PlatformIO is only one example of serial hardware and hardware/software human interfaces.

## Scope

### In scope

- (inferred) The template: control files, scripts, schemas, ledger designs, fictional examples and model entrypoints.

### Out of scope

- Legal work: archived under `archive/legal/` and not served by this template (owner decision).

## Constraints

- Preserve authoritative source material and provenance. Keep secrets and restricted material out of Git.
- Sending requires explicit owner approval. Until a superseding ADR on C is recorded with owner sign-off, the current rules' other explicit-authority gates, including those for deletions and consequential external writes, also apply.
- Simulations or guesses are never acceptable as verification (owner, stated with the domain-template requirement).

## Decision rights

- The owner (henslewm) owns goals, scope, business choices, and consequential external actions.
- AI tools may research, analyze, draft, organize, validate, and make reversible repository changes within granted permissions.
- Each conflict between an owner requirement and a current rule needs an ADR in `DECISIONS.md` and owner sign-off; until then the current rule applies.
- Unresolved conflicts, material adverse facts, and high-impact assumptions must be surfaced rather than hidden.

## Decisions (resolved 2026-10-03, ADR-089)

Stated by the owner. Each item below was decided; ADR-089 records them and withdraws the draft ADR-084 to ADR-088.

- **A. Review cap:** at most 4 automated-review rounds per pull request, then answer the findings already received and ask the maintainer. ADR-063 and ADR-074 unchanged.
- **B. Worker attempts:** preferred default 2, recorded only; the per-packet `retry_budget.max_attempts` stays the enforcement point.
- **C. Approvals:** current rules stay (`MASTER_INSTRUCTIONS.md`, `.claude/rules/02` and `04`, `AGENTS.md`). Not changed.
- **D. Single ledger:** not pursued. Question 2 is closed as no combined ledger.
- **F. Delegation:** superseded in part by ADR-093: a Claude Code session delegates bounded work to the `.claude/agents/` subagents by default. A human still runs any external harness worker (ADR-083 removed the launcher) until the launcher approved by ADR-096 (OL-036, decided 2026-10-07) lands.
- **G. Savings telemetry and dry runs (#12, #13):** deferred.
- Filing and sending require explicit owner approval (unchanged).
- Simulations or guesses are never acceptable as verification (unchanged).

## Decisions (2026-10-06, ADR-093)

Stated by the owner: the template is unfrozen to reduce drift and to auto-delegate tasks.

- Startup reads are validator-checked views (`PROJECT_STATE.md` current section, `OPEN_LOOPS.md` open table, `DECISIONS.md` index), and duplicated rules are pointers to `MASTER_INSTRUCTIONS.md`.
- Claude Code sessions delegate bounded work to the project subagents by default, with model tiers and bounded-outcome reports (`MASTER_CLAUDE_CODE.md` → Delegation).
- Open: whether the architect may also launch external harness workers automatically (OL-036). Until decided, ADR-083 stands.

## Decisions (2026-10-07, ADR-096)

Stated by the owner in the session of 2026-10-07.

- **Bootstrap retrofit:** the template runs under its own bootstrap gate (`config/bootstrap.json`), with `template_mode` kept and every record preserved. Autonomy starts only after the owner runs `python scripts/bootstrap_gate.py activate`.
- **Scope rule:** autonomous work is limited to the owner's stated requirements; no new features beyond the approved milestones.
- **Risk and sensitivity:** low and public.
- **OL-036:** yes. The architect may launch external harness workers automatically once a launcher is scoped and built under `EXECUTION_HARNESS_PROTOCOL.md`, starting from the ADR-077 limits. This supersedes the ADR-083 and ADR-089 refusals for that launcher only.
- **ADR-094 (branch `claude/auto-closeout`):** finish as directed: push on closeout, auto-merge once machine-checked ready (validator and tests green, an automated review on the exact head per ADR-074, every thread resolved, within the cap of 4), remove the ADR-091 ask rules, and mirror open loops as GitHub issues.
- **Savings:** fix the cost-as-zero defect (abandoned and failed attempts recorded as $0, `docs/AUDIT_2026-10-03.md` section 2); #12 and #13 stay deferred (decision G).

## Decisions (2026-10-09, ADR-100)

Stated by the owner after the first real launch on Windows timed out with no report on a local model.

- **Local models dropped:** local models (LM Studio, Ollama, llama.cpp and the like) are removed from the template's goals and instructions. Workers are cheaper cloud models only.
- The launcher milestone (OL-036) now completes on a first real launch against a metered cloud binding, within the per-packet budget and attempt limits (ADR-099).


## Bound document: CONNECTOR_PLAN.md

# Connector Plan

> Template defaults. Bootstrap replaces this file with a project-specific plan.

| Connector / source | Default | Use when | Access boundary | Write policy |
|---|---|---|---|---|
| GitHub | Required | Reading and maintaining project state | This repository and explicitly named related repos | Project-file writes only when requested; no force push |
| Web search | Conditional | Current public facts, official documentation, law, prices, schedules | Public sources; prefer primary authority | None |
| Google Drive | Conditional | Authoritative documents or large source folders live in Drive | Explicit files/folders or search scope | Read by default |
| Gmail | Conditional | Email is evidence, instruction, or an open-loop source | Relevant senders, recipients, dates, and terms | Search/read by default; no send without explicit request |
| Google Calendar | Conditional | Deadlines, hearings, meetings, availability | Relevant calendars and date windows | Read/free-busy by default |
| Google Contacts | Conditional | Identity or recipient resolution is needed | Named people or organizations | Read only |
| Specialist database | Conditional | Controlling scientific, technical, or financial authority is needed | Named database and task scope | Read only |

## Rules

- Do not connect a system merely because it is available.
- Use the narrowest useful scope.
- Record material sources in `SOURCE_INDEX.md`.
- Treat connector output as source material, not automatically as controlling truth.
- Consequential writes require explicit authority and verification.


## Bound document: SKILL_PLAN.md

# Skill Plan

> Template defaults. Bootstrap replaces this file with a project-specific plan.

## Always available or recommended

- `complex-project-bootstrapper`: initialize or retrofit a complex repo-backed project.
- Skill creator: create or update a repeatable workflow only after concrete inputs, outputs, and connector needs are known.
- Planning / execution-plan skill: use for long-horizon, multi-stage implementation.
- Skill installer or public skill search: discover reviewed skills rather than copying unknown instructions blindly.

## Enable only when the deliverable requires it

- PDF processing
- DOCX creation or redlining
- Spreadsheet analysis or modeling
- Presentation creation
- Image generation or editing
- Official documentation lookup
- CI troubleshooting

## Custom-skill threshold

Create a custom skill when at least one is true:

1. The workflow will recur at least twice.
2. The same multi-step instructions would otherwise be pasted repeatedly.
3. Deterministic scripts or validation materially improve reliability.
4. The workflow depends on project-specific conventions, schemas, connectors, or source boundaries.
5. Quality or safety requires a fixed checklist.

Do not create a skill for a single ordinary answer, general subject knowledge, or a process too unstable to standardize.


## Bound document: DOMAIN_PROFILE.md

# Domain Profile — Software + Hardware Interfaces

This is the default `main` specialization of the universal autonomous project template: software
that interacts with physical hardware, built so that most bounded work can go to cheap or local
models while no claim of hardware success is ever made on the strength of compilation or
simulation. `AUTONOMY_CONTROL_PLANE.md` is the controlling workflow policy; the controllers named
below are the mechanism.

## Startup gate

Autonomy is OFF until interactive intake is complete and the user approves the exact package.
`scripts/validate_bootstrap.py` requires, for this profile, a meaningful answer to every domain
orientation field before review or activation: existing baseline; exact hardware identity and
firmware; interfaces and protocols; authoritative specifications; host and deployment
environment; known-good and known-failing paths; fixtures, simulators, loopback and
hardware-in-loop resources; physical-access constraints; and the architecture boundaries whose
change requires approval. The architect then presents the component boundaries, dependency graph,
hardware abstraction boundary, verification ladder per component, routing policy, first milestone
and stop conditions. A placeholder answer is refused, not deferred.

## Decomposition

Prefer components that can be validated without physical hardware. Every packet names exactly one
component from the profile's separation list: protocol codec, transport, device abstraction,
hardware adapter, configuration, persistence, business logic, UI/API, simulator/fake,
telemetry/logging, deployment/operations. A packet that spans several is not independently
testable and is decomposed further. Hardware-facing components expose contracts that a fake or
loopback can satisfy, so their host-side rules are machine-runnable even when the device is not
on the bench. `examples/software-hardware/` is a complete worked decomposition.

## Work packet

The common contract is unchanged. For this profile the `domain` block is structural, validated by
`config/domains/software-hardware.schema.json` and `scripts/software_hardware.py` wherever a
contract is validated:

- `component`: the one separation category.
- `hardware_assumptions`: every physical behavior the packet relies on, each citing a contract
  source. Empty means the packet is `NOT_HARDWARE_FACING`.
- `protocol_references`: the specification sources implemented against; required when any
  hardware assumption exists.
- `validation_levels`: every validation id mapped to exactly one rung of the ladder.
- `hardware_status`: `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING`. A contract cannot declare
  `VERIFIED_ON_HARDWARE`; it is earned, never authored. The block is closed — no undeclared key
  and no free text can carry that literal anywhere in it — and `validate_contract` takes the
  profile as a required argument, so no caller skips these rules by omitting it.

## Verification ladder

static → unit → contract → simulation/loopback → integration → hardware-in-loop → representative
field workflow where required.

The first five rungs are machine-runnable: each such validation must declare a `command`, and the
acceptance controller's deterministic gate re-executes it in the reviewed workspace and records
what it observed (ADR-014). The two hardware rungs must not declare a command: they fail closed to
an attestation by a non-implementer operator, and that attestation must bind a structured hardware
evidence record by digest. A hardware rung with a command is refused as a simulator masquerading
as hardware; a machine rung without one is refused as attestation substituting for a runnable
check. `software_hardware.py status` derives the earned status from the ledger:
`VERIFIED_ON_HARDWARE` only for an accepted task whose hardware rungs were all attested and whose
contract does not declare `domain.synthetic: true` — a synthetic contract's inputs are fictional
by that declaration, so its hardware rungs can be attested and their bound records re-verified,
but the derived status stays `UNVERIFIED_ON_HARDWARE` regardless; every worked example in this
template declares it. A compile or simulation pass never upgrades it. The output names its
`evidence_basis`: without
`--evidence-dir` the status rests on the ledger's attestations and their declared digests, and
says it is attested, not record-verified; with `--evidence-dir` every bound record is found by
digest, validated as a hardware evidence record, and re-verified for task, validation, rung, a
`pass` outcome, the attesting operator and every line the attestation carried, compared exactly
except for the operator — a digest proves which bytes were bound, not that they are a record or
that they say what was attested. A ledger stored before these rules existed replays marked with
its shortfall for audit and acceptance status; only new events are refused, and the hardware
status is the one derivation that refuses (ADR-032).

## Code structure

Keep firmware in single-responsibility modules indexed by a `MODULES.md` beside the sources
(template: `templates/software-hardware/MODULES.md`). The rules are in
`.claude/rules/05-modular-code.md`.

## Build configuration (Arduino / ESP32)

Every Arduino or ESP32 firmware project keeps a root `platformio.ini` generated under
`docs/PLATFORMIO.md`. BLE/NimBLE and Windows-pairing lessons: `docs/BLE_NOTES.md`.

## Cost posture

Pure functions, codecs, parsers, fixtures, fakes, tests, log analysis and repetitive adapters route
to the local tiers first; objective failures and risk, never preference, drive escalation. The
hardware adapter and the integration/field packets carry `high` risk so the acceptance floor adds
independent model review and the cross-family gate. Hardware runs are operator actions and are
never dispatched to a worker.

## GitHub ledger

One tracking issue per milestone with its dependency-ordered wave plan; one issue per packet;
new findings become separate issues; PRs link the packet and carry validation evidence. Hardware
observations are recorded as bound evidence records and their attestations, not as prose in a
comment.

## Human-intervention gate

Routine implementation, testing, issue/PR updates, model escalation and bounded refactoring
proceed autonomously inside the approved architecture. Stop for user approval before materially
changing protocol assumptions, hardware support scope, public interfaces, persistence
architecture, the security/authentication model, deployment topology, core framework/language, or
the hardware abstraction boundary. Any action on physical hardware that can damage it, or any
claim of hardware verification, is an operator action recorded as evidence, never an autonomous
step.

