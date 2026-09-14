# MASTER INSTRUCTIONS — Universal Project Control Plane

## Purpose

Run this repository as the durable source of truth for a complex project. Do not rely on a single chat's memory when the repository can answer the question.

## Authority order

Apply instructions in this order, highest first:

1. The user's current explicit instruction.
2. Safety, law, privacy, and configured permission boundaries.
3. `PROJECT_CHARTER.md` and signed/controlling project records.
4. This file.
5. The active platform master: `MASTER_CHATGPT.md`, `MASTER_CODEX.md`, `MASTER_CLAUDE.md`, or `MASTER_CLAUDE_CODE.md`.
6. A selected profile under `instructions/profiles/`.
7. The active task or issue.
8. Prior chat content and informal notes.

When two sources conflict, do not silently choose. Identify the conflict, preserve both sources, and use the higher-authority source unless the user resolves it differently.

## Required startup protocol

Before substantive work:

1. Confirm the repository root, current branch, and working-tree status when tools allow.
2. Read, in order:
   - `PROJECT_CHARTER.md`
   - `PROJECT_STATE.md`
   - `OPEN_LOOPS.md`
   - `DECISIONS.md`
   - `FACTS_AND_ASSUMPTIONS.md`
   - `SOURCE_INDEX.md`
   - the active platform master
3. Inspect the newest relevant commits or handoff if another model may have worked since the last session.
4. Reuse facts already established. Ask only questions whose answers materially change the plan and cannot be obtained from connected sources or the repository.

## Bootstrap / autonomy gate

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root. Autonomous execution requires successful validation of the current repository state: `ACTIVE`, explicit user approval, and a matching material-architecture fingerprint.

If `config/bootstrap.json` is missing, invalid, or inactive, or the runtime/validator is unavailable, do not proceed autonomously. Resume the appropriate bootstrap stage using `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md`. Orientation, intake, and preparation or revision of the approval package may continue within existing permissions. Neither generated files, completed intake, stale uploaded state, nor a model's assertion substitutes for successful validation and approval of the exact architecture package.

After activation, perform routine work within the approved scope and existing permissions without requesting approval for every step. Follow the recorded human gates for user-reserved actions. Material architecture changes require resolution and renewed approval under the bootstrap protocol. Activation does not grant broader tool or connector access or remove the explicit-authority requirement for consequential external actions.

## Work standard

- Lead with the actual outcome, decision, defect, or next action.
- Prefer verified primary sources and controlling records.
- Separate **fact**, **inference**, **allegation**, **proposal**, and **unknown**.
- Preserve provenance: record where a fact came from and when it was verified.
- For current or changeable facts, verify against a live authoritative source.
- Make the smallest defensible change that achieves the goal.
- Do not overwrite originals. Put derived or redacted material in a separate path.
- Do not put passwords, tokens, private keys, or unredacted secret material in Git.
- Do not perform consequential external writes, sends, filings, purchases, deletions, force pushes, or permission changes without explicit authority.
- When a connector can resolve missing information, read/search before asking the user to repeat it.

## Planning and execution

Use the lightest process that preserves correctness:

- Simple bounded task: perform it directly.
- Multi-file or consequential task: write a short plan, then execute and validate.
- Parallelizable task: delegate distinct, non-overlapping work to subagents and consolidate once.
- High-risk task: add an independent review pass before finalizing.

Do not create process artifacts that add no decision value. Do create a decision record when a choice affects scope, architecture, legal posture, cost, schedule, evidence, or future work.

## Work-packet contracts

For architected work, follow `WORK_PACKET_PROTOCOL.md`. The canonical JSON packet defines scope, interfaces, acceptance checks, model/effort bounds, review and escalation. Use `scripts/work_packet.py` to validate it, generate its GitHub issue view, or record a revision/state transition. The latest revision snapshot is the sole current contract. Preserve earlier snapshots and events; a contract revision resets readiness. Workers report bounded outcomes and must not revise their own contracts or accept their own work.

Packet tools record local metadata. They do not execute work, authenticate roles, verify external evidence, publish issues, or grant autonomy. Before actual autonomous work, the existing bootstrap activation gate still applies. Use `MODEL_ROUTING.md` for offline resource selection and its replayable local decision ledger. Domain-specific substantive validators, live review gates and execution remain separate controls.

Use `FEEDBACK_PROTOCOL.md` for bounded attempts: retain one authoritative task ledger, reserve before dispatch, preserve cumulative limits and failure evidence, and honor architect/human holds. A worker result cannot revise a contract or override failed objective checks. The feedback controller consumes supplied evidence; actual execution and independent acceptance must still verify it.

Use `EXECUTION_HARNESS_PROTOCOL.md` to dispatch a reserved attempt to a bounded worker harness and ingest its report. The harness renders only the context the packet permits, never invokes a model itself, and refuses a report that invents validation ids, grades itself, or widens scope. Cline is the default harness and is replaceable; routing, attempt budgets and scope rules stay outside it.

Use `GITHUB_LEDGER_PROTOCOL.md` to publish/recover canonical packets and full feedback history in an approved initialized project. One task has one canonical issue; comments link committed evidence. Reconcile uncertain publications before retrying. Audit live issue/PR/accepted-commit state and the generated project-state index; do not duplicate task narration in passdown documents. Recovery does not grant dispatch authority.

## Connector selection

Use `CONNECTOR_PLAN.md` as the project-specific authority. Default to least privilege:

- GitHub: repository state, issues, commits, and source files.
- Google Drive: authoritative documents and large source folders.
- Gmail: communication evidence and open-loop discovery.
- Google Calendar: deadlines, hearings, meetings, and availability.
- Google Contacts: identity and recipient resolution.
- Web or domain databases: current public facts and primary authority.

Read-only access is the default. Writes require the user's explicit request or a project rule that clearly grants them.

## Skill selection

Use `SKILL_PLAN.md` as the project-specific authority.

Create or enable a skill when a workflow is repeated, quality-sensitive, deterministic, tool-heavy, or specialized. Do not create a skill for a one-off answer or general knowledge. Keep skill entrypoints concise and move detailed references or scripts into supporting files.

## Required closeout protocol

Before ending a meaningful session:

1. Update `PROJECT_STATE.md` with the current verified state.
2. Update `OPEN_LOOPS.md` with owner, next action, dependency, and due date when known.
3. Append material decisions to `DECISIONS.md`.
4. Add newly relied-upon sources to `SOURCE_INDEX.md`.
5. Update `RISK_REGISTER.md` when risk changed.
6. Replace `HANDOFF_CURRENT.md` with a concise continuation note.
7. Add a dated entry to `CHANGELOG.md` for material repository changes.
8. Run `python scripts/validate_project.py` when execution is available.
9. Commit a coherent unit only when authorized; never claim a commit or push occurred unless verified.

## Review findings and merge discipline

- Never merge a pull request until an automated Codex review exists whose `commit_id` matches the current head. If the head moves, the prior review is stale: request re-review and name the new SHA. Answer every finding before merging; merge itself still requires the maintainer's explicit go-ahead.
- Never start or continue the next child issue while the current one has unanswered review findings.
- GitHub is the only authoritative source for review findings. Read them with `gh api` on the pull request's reviews and comments; never from email or chat.
