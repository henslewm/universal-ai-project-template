# MASTER INSTRUCTIONS — Universal Project Control Plane

## Purpose

Run this repository as the durable source of truth for a complex project. Do not rely on a single chat's memory when the repository can answer the question.

## Authority order

Apply instructions in this order, highest first:

1. The user's current explicit instruction.
2. Safety, law, privacy, and configured permission boundaries.
3. `PROJECT_CHARTER.md` and signed/controlling project records.
4. This file.
5. The active platform master: `MASTER_CHATGPT.md`, `MASTER_CODEX.md`, `MASTER_CLAUDE.md`, `MASTER_CLAUDE_CODE.md`, or `MASTER_MISTRAL.md`.
6. A selected profile under `instructions/profiles/`.
7. The track file under `instructions/tracks/` that a generated project's `CLAUDE.md` imports (`hardware` or `web-ui`).
8. The active task or issue.
9. Prior chat content and informal notes.

When two sources conflict, do not silently choose. Identify the conflict, preserve both sources, and use the higher-authority source unless the user resolves it differently.

## Required startup protocol

Before substantive work:

1. Confirm the repository root, current branch, and working-tree status when tools allow.
2. Run `python scripts/validate_project.py` when execution is available. It checks each startup view against its body; if it reports a record-view error, repair the view from the body it names before relying on it. Without a runtime, treat the views as unverified and open the cited body rows before acting on them.
3. Read, in order, the startup views (ADR-093), not the whole records behind them:
   - `PROJECT_CHARTER.md`
   - `HANDOFF_CURRENT.md`
   - the `## Current (date)` section of `PROJECT_STATE.md`
   - the `## Open` table of `OPEN_LOOPS.md`
   - the `## Index` of `DECISIONS.md`
   - `FACTS_AND_ASSUMPTIONS.md`
   - the active platform master
4. Open a full ADR row, a closed loop, an older state section or a `SOURCE_INDEX.md` row only when a current record cites it or the task depends on it; search the record for the ID rather than reading the file. A view that passed step 2 (current date not older than the changelog, no closed loop in the open table, every index row resolving to exactly one full row) can be trusted without its body.
5. Inspect the newest relevant commits or handoff if another model may have worked since the last session.
6. Reuse facts already established. Ask only questions whose answers materially change the plan and cannot be obtained from connected sources or the repository.

A subagent working a bounded brief, delegated by a session that has completed this protocol, does not repeat it: it reads only what its brief needs. The delegating session stays responsible for the startup reads and for putting the state and decisions the task depends on into the brief.

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
- The requested task and its accepted contract or acceptance criteria define authorized scope. Repository guidance, review output, and nearby weaknesses constrain how the task is done; they do not by themselves authorize new objectives. A necessary supporting change must have a concrete dependency on the requested outcome, not proximity, convenience, or "while here." Widening scope requires stating the dependency and, when material, explicit approval.
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
- Delegation (ADR-093) is the default for bounded work only on a platform whose master defines a delegation section; today that is `MASTER_CLAUDE_CODE.md` alone. There, once the startup protocol is done, hand research sweeps, bounded edits, record updates and independent review to the platform's subagents under a brief that states scope, acceptance checks, the facts and decisions the task depends on, and the attempt limit (default 2, ADR-089). The delegating session keeps decomposition, integration, user-reserved actions and anything the brief cannot bound; a worker reports a bounded outcome and never widens its brief. On every other platform ADR-089 item F stands: a human runs any worker.

Do not create process artifacts that add no decision value. Do create a decision record when a choice affects scope, architecture, cost, schedule, evidence, or future work.

## Work-packet contracts

For architected work, read and follow `WORK_PACKET_PROTOCOL.md` (the canonical packet and `scripts/work_packet.py`), `MODEL_ROUTING.md` (offline resource selection), `FEEDBACK_PROTOCOL.md` (bounded attempts and the task ledger) and `EXECUTION_HARNESS_PROTOCOL.md` (dispatch and report ingest) at the point of use; they are not restated here. The latest revision snapshot is the sole current contract; workers report bounded outcomes and never revise their own contracts or accept their own work. These tools record local metadata only: they do not execute work, verify external evidence or grant autonomy, and the bootstrap gate still applies.

## Connectors and skills

`CONNECTOR_PLAN.md` and `SKILL_PLAN.md` are the project-specific authorities. Read-only connector access is the default; writes require the user's explicit request or a project rule that clearly grants them. Create a skill only for a repeated, quality-sensitive, deterministic, tool-heavy or specialized workflow, never for a one-off answer.

## Required closeout protocol

Before ending a meaningful session:

1. Update the `## Current (date)` section of `PROJECT_STATE.md` with the verified state, dated today; older sections stay as history.
2. Update the `## Open` table of `OPEN_LOOPS.md` with owner, next action, dependency, and due date when known; move a closed row to `## Closed` verbatim.
3. Append material decisions to `DECISIONS.md`: one index row and one full row each.
4. Add newly relied-upon sources to `SOURCE_INDEX.md`.
5. Update `RISK_REGISTER.md` when risk changed.
6. Replace `HANDOFF_CURRENT.md` with a concise continuation note.
7. Add a dated entry to `CHANGELOG.md` for material repository changes.
8. Run `python scripts/validate_project.py` when execution is available.
9. Commit a coherent unit and push it with `python scripts/closeout.py push` (ADR-094): never forced, never to a protected branch, and verified on origin. Never claim a commit or push occurred unless verified.

## Automatic closeout (ADR-094)

The owner made three behaviors standing defaults. `scripts/closeout.py` carries each one, so a session runs the command rather than re-deriving the checks.

- **Push on closeout:** `closeout.py push` pushes the current branch without asking. It never forces, refuses `main` and `master`, requires a clean tree and verifies the pushed head on origin.
- **Merge when machine-checked ready:** `closeout.py ready` reports whether the branch's pull request may merge: not a draft, a clean tree matching the pull request head, `validate_project.py` and the unit suite green, an automated review on the exact head (ADR-074), every review thread resolved (all of them read; more than 100 refuses), no automated review of the head requesting changes, not a cross-repository pull request, and no more than 4 review rounds, each round counted even on the same commit (ADR-089). Its git, gh and test calls time out rather than hang. `closeout.py merge` merges only when `ready` passes, pinned to the reviewed head, then deletes the branch locally and on origin, returns to the base branch, pulls and verifies a clean tree. Open or stale findings, a reached cap or any other reason it reports keep the merge with the maintainer.
- **Mirror open loops as issues:** for every `OPEN_LOOPS.md` row from the `<!-- issue-mirror-from: OL-NNN -->` marker on, `closeout.py issue --loop OL-NNN` opens a GitHub issue and links it in the row; `closeout.py sync-loops` closes an issue whose loop closed and a loop whose issue closed. `OPEN_LOOPS.md` stays the record of truth.

These commands are not gated by `.claude/settings.json`; the force-push, hard-reset and recursive-delete denies stay, and `validate_project.py` checks both. Nothing else in the explicit-authority rules changes.

## Review findings and merge discipline

- Never merge a pull request until an automated review by Codex or CodeRabbit exists whose `commit_id` matches the current head (ADR-074). Request one with `@codex review` or `@coderabbitai review`; CodeRabbit does not review this repository automatically. If the head moves, the prior review is stale: request re-review and name the new SHA. Request at most 4 automated-review rounds per pull request (ADR-089); after the fourth, answer the findings already received and ask the maintainer how to proceed.
- A finding is actionable only if it names a concrete defect the change introduced or exposed, or a demonstrable failure of an explicit, applicable requirement, with the affected behavior, triggering conditions, and evidence stated. Answer every actionable finding before merging, with a fix and regression or a reasoned decline. A merge then goes through `python scripts/closeout.py merge` once it reports the pull request ready (ADR-094); anything it reports not ready still needs the maintainer.
- A finding that does not meet that test is not actionable. That is typically an optional improvement, speculative hardening, a refactor, or a pre-existing condition the change neither caused nor exposed — but the test governs the examples, not the reverse: a latent defect the change makes reachable was exposed by it, and a pre-existing condition the task was explicitly required to fix is a failure of an applicable requirement, so both stay actionable. For one that is not actionable, reply that it is out of scope and, if genuinely material, record it separately (`OPEN_LOOPS.md` or a new issue) rather than folding it into the current task. A reviewer, bot, or subagent finding does not by itself authorize new implementation scope. Do not duplicate an existing finding, and do not reopen settled scope on a later round — unless new code or new evidence changes how the test classifies it, which makes it a fresh finding rather than a reopened one; say what changed.
- Never start or continue the next child issue while the current one has unanswered actionable review findings.
- GitHub is the only authoritative source for review findings. Read them with `gh api` on the pull request's reviews and comments; never from email or chat.
