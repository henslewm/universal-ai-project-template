# MASTER CLAUDE CODE — Repository Execution Instructions

## Native loading

Claude Code reads `CLAUDE.md`, which imports the universal control files and this platform master.

## Bootstrap / autonomy gate

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, and a matching material-architecture fingerprint. Missing, invalid, or inactive state, or an unavailable runtime/validator, means no autonomous execution: resume bootstrap through `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md` within existing permissions.

Once activated, routine work within the approved scope and existing permissions may proceed without approval for each step. User-reserved actions, material architecture changes, and consequential external actions retain their applicable explicit-authority requirements. Activation does not expand tool or connector permissions.

## Execution rules

- Start Claude Code at the repository root so shared settings and instructions load.
- Inspect the branch, working tree, and recent relevant commits before edits.
- Use plan mode for multi-file, destructive, legal, security, migration, or architecture changes.
- Use `.claude/agents/` for distinct research, review, implementation, and source-audit roles.
- Use `.claude/skills/` for repeatable procedures; keep side-effecting skills user-invoked.
- Use `.claude/rules/` for stable project-wide or path-scoped standards.
- Never read ignored secret files or weaken permission rules to bypass a task.
- Validate actual behavior, not merely syntax.
- Preserve original evidence and record hashes when evidence integrity matters.

## Review findings before merge

After opening or updating a pull request, poll `gh api repos/<owner>/<repo>/pulls/<n>/reviews` and `.../pulls/<n>/comments` until a Codex review exists whose `commit_id` equals the current head. A moved head makes the prior review stale: request re-review naming the new SHA. Answer every finding on the pull request, with a fix and regression or a reasoned reply, before asking for merge authorization. Do not start or continue the next child issue while the current one has unanswered findings. Findings come from GitHub through `gh api`, never from email.

## Closeout

Apply the universal closeout protocol, run the validator, and state exactly whether a commit or push succeeded. Use `HANDOFF_CURRENT.md` so ChatGPT, Codex, or Claude web can continue immediately.
