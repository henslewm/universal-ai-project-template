# Project Charter

## Project

- **Name:** Universal AI Project Template
- **Slug:** universal-ai-project-template
- **Domain:** (inferred) Multi-model AI project control plane, as a reusable template. Served tracks: software development and serial hardware / hardware-software interfaces. Legal work was archived under `archive/legal/` (owner decision).
- **Risk tier:** Not set
- **Sensitivity:** Not set. The repository is public.
- **Owner:** henslewm
- **Target date:** Not set

## Problem statement

All AI models hallucinate, drift and deviate from requests, goals, requirements and specs, so the controls must prevent that (endorsed "1000%"). (inferred) Having the strongest model do all the work costs too much, and one chat's memory does not carry across models or sessions.

## Desired outcome

A reusable, repo-backed control plane that makes complex, high-stakes AI-assisted work efficient: the owner is "spending money now to save money later." An architect model (Fable, Opus 5.5/6) must delegate intelligently to cheaper or local models under an explicit contract and monitor them effectively.

## Definition of done (inferred)

- Cheaper cloud or local models execute architect-written packets within the per-packet limits, monitored through the acceptance and feedback ledgers.
- The software and hardware tracks bootstrap, plan, execute and verify end to end. The ADR-089 freeze was lifted on 2026-10-06 (ADR-093) for two objectives: less drift and token cost at session start, and delegation by default.

## Required deliverables

- **Continuity:** GitHub as durable memory for ChatGPT, Codex, Claude, Claude Code and Mistral.
- **Packets:** the strong model writes bounded, machine-checkable packets; cheaper cloud or local models execute them.
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
- **F. Delegation:** superseded in part by ADR-093: a Claude Code session delegates bounded work to the `.claude/agents/` subagents by default. A human still runs any external harness worker (ADR-083 removed the launcher) until OL-036 is decided.
- **G. Savings telemetry and dry runs (#12, #13):** deferred.
- Filing and sending require explicit owner approval (unchanged).
- Simulations or guesses are never acceptable as verification (unchanged).

## Decisions (2026-10-06, ADR-093)

Stated by the owner: the template is unfrozen to reduce drift and to auto-delegate tasks.

- Startup reads are validator-checked views (`PROJECT_STATE.md` current section, `OPEN_LOOPS.md` open table, `DECISIONS.md` index), and duplicated rules are pointers to `MASTER_INSTRUCTIONS.md`.
- Claude Code sessions delegate bounded work to the project subagents by default, with model tiers and bounded-outcome reports (`MASTER_CLAUDE_CODE.md` → Delegation).
- Open: whether the architect may also launch external harness workers automatically (OL-036). Until decided, ADR-083 stands.
