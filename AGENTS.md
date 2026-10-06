# Codex Startup Router

This repository uses a shared multi-model control plane.

## Read before substantive work

Read, in order: `MASTER_INSTRUCTIONS.md`, `MASTER_CODEX.md`, `PROJECT_CHARTER.md`, `HANDOFF_CURRENT.md`, the `## Current` section of `PROJECT_STATE.md`, the `## Open` table of `OPEN_LOOPS.md`, the `## Index` of `DECISIONS.md` and `FACTS_AND_ASSUMPTIONS.md`. Open a full ADR row, a closed loop, a `SOURCE_INDEX.md` or `RISK_REGISTER.md` row by ID when a record cites it (startup protocol, `MASTER_INSTRUCTIONS.md`).

Then inspect `git status`, the current branch, and the newest relevant commits.

A subagent working a bounded brief follows the bounded-subagent exception in the startup protocol of `MASTER_INSTRUCTIONS.md` instead of repeating these reads.

## Bootstrap / autonomy gate

Apply `MASTER_INSTRUCTIONS.md` → "Bootstrap / autonomy gate" exactly as stated there; it is deliberately not restated here.

## Core behavior

- Treat the repository, not prior chat memory, as the durable state.
- Ask only questions that cannot be answered from the repo or approved connectors and that materially change execution.
- Use `instructions/profiles/` only when the task matches a profile.
- Use `.agents/skills/complex-project-bootstrapper/` for new-project initialization or project retrofits.
- Use `.codex/agents/` for parallel, non-overlapping subagent work.
- Dispatch bounded worker runs through `EXECUTION_HARNESS_PROTOCOL.md`; never widen a packet inside a worker.
- Run `python scripts/validate_project.py` at startup, before trusting the startup views, and again before completing material repository changes.
- Apply the closeout protocol in `MASTER_INSTRUCTIONS.md`.

## Safety

Do not force-push, delete evidence, expose secrets, send external communications, change permissions, or perform consequential external writes without explicit user authority.
