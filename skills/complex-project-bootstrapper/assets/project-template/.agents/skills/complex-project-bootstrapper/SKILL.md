---
name: complex-project-bootstrapper
description: Build or retrofit a focused, repo-backed workspace for complex, ongoing, high-stakes, source-heavy, or multi-session work. Use when the user asks to initialize a project, create a reusable GitHub project base, coordinate ChatGPT/Codex/Claude/Claude Code, design project instructions, select connectors or skills, preserve cross-model history, or turn a complicated chat into a durable project. Produces reused or missing-only intake, inactive tailored files, an architecture review package, explicit approval activation, native model entrypoints, connector and skill plans, validation, and a web-UI setup checklist. Do not use for a simple one-off chat answer.
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
- `config/bootstrap.json` and `BOOTSTRAP_REVIEW.md`, with setup, readiness, and activation status kept distinct;
- validation results and verified Git/GitHub status.

## Workflow

1. Determine mode:
   - **New project:** duplicate the bundled or current template into a new/empty directory, or tailor an uninitialized template repository in place.
   - **Retrofit:** preserve the existing repo and add only missing control files and native entrypoints.
   - **Audit:** inspect and propose the smallest repair set before editing.
2. Read `references/intake-schema.md`, `BOOTSTRAP_PROTOCOL.md`, and `prompts/INTERACTIVE_BOOTSTRAP.md` in the current or bundled template. Inspect existing context and authorized sources before asking questions.
3. Recover verified intake into an optional answers JSON. Ask only missing, decision-relevant common and canonical profile orientation fields in small stages; preserve source distinctions and disclose proposed defaults.
4. For new setup, run `python scripts/bootstrap_project.py --interactive --answers verified-intake.json --profile software-hardware --destination ../my-project --no-git`, substituting `family-law` or `civil-rights-nc` as appropriate. Omit `--answers` and its filename when unavailable; use `--destination .` only for an uninitialized template repository. The generator produces `INTAKE` with autonomy off, `config/bootstrap.json`, and an initial review with readiness gaps.
5. Rebootstrap of initialized projects is refused. Preserve existing records, evidence, and approval history; add only missing controls during retrofit. Revise and review an existing bootstrap package instead of deleting state or resetting template mode to overwrite it.
6. Apply `references/platform-map.md` so each client uses its native discovery mechanism.
7. Apply `references/capability-selection.md` to choose the minimum connectors and skills. Default connectors to read-only. Do not treat tool availability as authority for consequential writes.
8. Preserve sensitive originals in the approved source system. Put links, metadata, hashes, redacted copies, and derived work in the repository as appropriate.
9. Have the architect complete project/architecture boundaries, milestones/dependencies, sources, risks, `routing.policy`, `workflow.policy`, `human_gates`, and profile `domain` in `config/bootstrap.json`; resolve the `unresolved` blockers. Align the charter, connector/skill plans, domain profile, and `config/project.json`. Run the repository validator and fix errors.
10. From the generated project's root, run `python scripts/bootstrap_gate.py review`. It revokes previous approval first, snapshots `config/project.json` and SHA-256 hashes of UTF-8 text with normalized LF line endings for the four bound documents, and requires readiness. Only success writes `AWAITING_APPROVAL` with a ready `BOOTSTRAP_REVIEW.md`; failure leaves autonomy off and reports readiness gaps. Present the review and bound documents to the user. Resolve revisions and rerun review before approval.
11. Only after explicit user authorization for the approval interaction, run `python scripts/bootstrap_gate.py activate`. It presents the exact package and asks for approving identity and `APPROVE <fingerprint>`; there is no noninteractive autoapprove option. Never invent approval. Success records the receipt in `config/bootstrap.json` and retains the pre-approval review. Automated activation tests use disposable fixtures only.
12. Run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` before autonomous substantive work in every session. Missing/invalid/inactive state, stale bindings, or unavailable runtime means no autonomy; resume bootstrap/review or prepare a runtime handoff. After activation, routine approved-scope work may proceed within existing permissions. Reserved actions and consequential external writes still require their applicable explicit authority.
13. Initialize Git, commit, or publish only when authorized; tool availability is not authority. If execution is unavailable, provide prepared files or an archive and a runtime handoff. Never imply a commit, push, or activation occurred unless verified.
14. Return a concise setup report using `references/output-format.md`, explicitly adding bootstrap state, autonomy status, review path, readiness gaps, and approval receipt status. Inactive setup is a valid handoff, not an active project.

## Intake behavior

- Infer or retrieve what is already known.
- Prefer defaults and choices over open-ended interrogation.
- Ask only questions whose answers change files, permissions, sources, scope, or success criteria.
- When the user says to proceed without more questions, use reasonable nonmaterial defaults and record assumptions during preparation. Do not invent material facts or treat that instruction as approval of the architecture package.

## Connector rules

Use GitHub for the durable repository. Add Drive, Gmail, Calendar, Contacts, web, specialist databases, or task systems only when a deliverable depends on them. Search/read first; external writes require explicit current authority.

## Skill rules

Enable a trusted existing skill when it covers the workflow. Create a custom skill only when inputs, outputs, connector needs, and a repeatable process are concrete. Keep `SKILL.md` concise; place detailed references, scripts, and assets in supporting folders.

## Validation gates

Read `references/quality-gates.md`. Do not finish while required files are absent, generated projects contain unresolved placeholders, native skill copies diverge, config files do not parse, source/permission boundaries are missing, or claimed Git/GitHub state is unverified. Report unresolved readiness or absent approval honestly; a valid inactive handoff does not authorize autonomy.

The fingerprint includes domain, workflow, unresolved blockers, configuration, and document bindings. Startup validation compares bound configuration and files with current repository content. This local gate detects normal bypass and stale approvals; it does not authenticate humans or constrain actors who rewrite code or approval records. It does not configure providers or expand permissions. Canonical templates carry snapshots of existing domain documents; detailed domain schemas/workflows remain owned by #9/#10/#11.
