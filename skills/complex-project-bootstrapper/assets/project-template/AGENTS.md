# Codex Startup Router

This repository uses a shared multi-model control plane.

## Read before substantive work

Read these files in order:

1. `MASTER_INSTRUCTIONS.md`
2. `MASTER_CODEX.md`
3. `PROJECT_CHARTER.md`
4. `PROJECT_STATE.md`
5. `OPEN_LOOPS.md`
6. `DECISIONS.md`
7. `FACTS_AND_ASSUMPTIONS.md`
8. `SOURCE_INDEX.md`
9. `RISK_REGISTER.md`
10. `HANDOFF_CURRENT.md`

Then inspect `git status`, the current branch, and the newest relevant commits.

## Bootstrap / autonomy gate

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, and a matching material-architecture fingerprint. A missing, invalid, or inactive bootstrap file, or an unavailable runtime/validator, means autonomy is not authorized. Resume bootstrap through `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md`; orientation, intake, and preparation of the approval package may continue within existing permissions. Generated files, completed intake, or assumed approval do not satisfy the gate.

After activation, routine work within the approved scope and existing permissions may proceed without renewed approval for each step. User-reserved actions, material architecture changes, and consequential external actions still require their applicable explicit authority; activation does not expand tool or connector permissions.

## Core behavior

- Treat the repository, not prior chat memory, as the durable state.
- Ask only questions that cannot be answered from the repo or approved connectors and that materially change execution.
- Use `instructions/profiles/` only when the task matches a profile.
- Use `.agents/skills/complex-project-bootstrapper/` for new-project initialization or project retrofits.
- Use `.codex/agents/` for parallel, non-overlapping subagent work.
- Dispatch bounded worker runs through `EXECUTION_HARNESS_PROTOCOL.md`; never widen a packet inside a worker.
- Run `python scripts/validate_project.py` before completing material repository changes.
- Apply the closeout protocol in `MASTER_INSTRUCTIONS.md`.

## Safety

Do not force-push, delete evidence, expose secrets, send external communications, change permissions, or perform consequential external writes without explicit user authority.
