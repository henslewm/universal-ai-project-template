---
name: complex-project-bootstrapper
description: Build or retrofit a focused, repo-backed workspace for complex, ongoing, high-stakes, source-heavy, or multi-session work. Use when the user asks to initialize a project, create a reusable GitHub project base, coordinate ChatGPT/Codex/Claude/Claude Code, design project instructions, select connectors or skills, preserve cross-model history, or turn a complicated chat into a durable project. Produces a concise intake, tailored repository files, native model entrypoints, connector and skill plans, validation, Git initialization, and a web-UI setup checklist. Do not use for a simple one-off chat answer.
---

# Complex Project Bootstrapper

Create a durable project workspace whose canonical state lives in a repository rather than in one chat.

## Inputs

Accept a problem statement, existing repository or template, desired deliverables, authoritative source locations, deadlines, risk/sensitivity, AI clients, connector boundaries, and repeated workflows. Inspect available context and connected sources before asking the user to repeat information.

## Outputs

Produce:

- a tailored project repository or retrofit;
- universal and platform-specific instructions;
- current charter, state, open loops, decisions, facts/assumptions, sources, risks, and handoff;
- ChatGPT and Claude web Project setup instructions;
- Codex and Claude Code native configuration;
- connector and skill selection plans;
- validation results and verified Git/GitHub status.

## Workflow

1. Determine mode:
   - **New project:** duplicate the bundled or current template.
   - **Retrofit:** preserve the existing repo and add only missing control files and native entrypoints.
   - **Audit:** inspect and propose the smallest repair set before editing.
2. Read `references/intake-schema.md` and inspect existing context.
3. Ask one compact intake block containing only missing, decision-relevant information. Ask no more than eight questions and use at most one follow-up round for true blockers.
4. Normalize answers into `config/project.json`.
5. Create or tailor the repository using `scripts/bootstrap_project.py` when execution is available.
6. Apply `references/platform-map.md` so each client uses its native discovery mechanism.
7. Apply `references/capability-selection.md` to choose the minimum connectors and skills. Default connectors to read-only. Do not treat tool availability as authority for consequential writes.
8. Preserve sensitive originals in the approved source system. Put links, metadata, hashes, redacted copies, and derived work in the repository as appropriate.
9. Run the repository validator and fix every error.
10. Initialize Git and commit when permitted. Create/push a GitHub repository only when a write-capable tool or authenticated GitHub CLI is available and the user authorized it.
11. If repository creation is unavailable, return a complete archive and the exact publish command. Never imply a commit or push occurred unless verified.
12. Return a concise setup report using `references/output-format.md`.

## Intake behavior

- Infer or retrieve what is already known.
- Prefer defaults and choices over open-ended interrogation.
- Ask only questions whose answers change files, permissions, sources, scope, or success criteria.
- When the user says to proceed without more questions, use reasonable defaults, record assumptions, and continue unless safety makes execution impossible.

## Connector rules

Use GitHub for the durable repository. Add Drive, Gmail, Calendar, Contacts, web, specialist databases, or task systems only when a deliverable depends on them. Search/read first; external writes require explicit current authority.

## Skill rules

Enable a trusted existing skill when it covers the workflow. Create a custom skill only when inputs, outputs, connector needs, and a repeatable process are concrete. Keep `SKILL.md` concise; place detailed references, scripts, and assets in supporting folders.

## Validation gates

Read `references/quality-gates.md`. Do not finish while required files are absent, generated projects contain unresolved placeholders, native skill copies diverge, config files do not parse, source/permission boundaries are missing, or the claimed Git/GitHub state is unverified.
