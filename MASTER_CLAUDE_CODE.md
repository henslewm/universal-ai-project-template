# MASTER CLAUDE CODE — Repository Execution Instructions

## Native loading

Claude Code reads `CLAUDE.md`, which imports the universal control files and this platform master.

## Bootstrap / autonomy gate

Apply `MASTER_INSTRUCTIONS.md` → "Bootstrap / autonomy gate" exactly as stated there; it is deliberately not restated here.

## Delegation (ADR-091)

The session that completed the startup protocol is the architect. It delegates by default and keeps only what a brief cannot bound:

| Agent (`.claude/agents/`) | Model | Delegate |
|---|---|---|
| `researcher` | sonnet | source sweeps, repository or web research, fact-finding before drafting |
| `operator` | sonnet | a bounded, already-understood change with stated acceptance checks and validation |
| `record-keeper` | sonnet | the closeout records after verified work |
| `reviewer` | inherit (architect tier) | independent review of a material draft, plan or change |

Rules: every brief states scope, acceptance checks, the facts and decisions it depends on, and the attempt limit (default 2). Run non-overlapping briefs in parallel and consolidate once. A report ends with one bounded outcome (PASS, FAIL, BLOCKED, NEEDS_ESCALATION, ARCHITECTURE_CONFLICT); the architect verifies it rather than trusting it, and on FAIL re-briefs at most once before escalating to itself. Agents inherit `CLAUDE.md` and its imports, so the brief carries only what those do not. The reviewer stays at the architect tier because review quality, not cost, is the control. User-reserved and consequential external actions are never delegated. Dispatch to an external harness (Cline, local models) stays operator-run until a separate decision (OL-036).

## Execution rules

- Start Claude Code at the repository root so shared settings and instructions load.
- Inspect the branch, working tree, and recent relevant commits before edits.
- Use plan mode for multi-file, destructive, security, migration, or architecture changes.
- Use `.claude/agents/` for distinct research, review, implementation, and source-audit roles.
- Use `.claude/skills/` for repeatable procedures; keep side-effecting skills user-invoked.
- Use `.claude/rules/` for stable project-wide or path-scoped standards.
- Never read ignored secret files or weaken permission rules to bypass a task.
- Validate actual behavior, not merely syntax.
- Preserve original evidence and record hashes when evidence integrity matters.

## Review findings before merge

Apply `MASTER_INSTRUCTIONS.md` → "Review findings and merge discipline" exactly as stated; it is the single definition and is not restated here. Read reviews and comments with `gh api` on the pull request (`.../pulls/<n>/reviews` and `.../pulls/<n>/comments`), never from email.

## Closeout

Apply the universal closeout protocol, run the validator, and state exactly whether a commit or push succeeded. Use `HANDOFF_CURRENT.md` so ChatGPT, Codex, or Claude web can continue immediately.
