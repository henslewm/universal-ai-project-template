# MASTER CODEX — Repository Execution Instructions

## Native loading

Codex reads `AGENTS.md`. Treat that file as the startup router and this file as the Codex-specific operating layer.

## Bootstrap / autonomy gate

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, and a matching material-architecture fingerprint. Missing, invalid, or inactive state, or an unavailable runtime/validator, means no autonomous execution: resume bootstrap through `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md` within existing permissions.

Once activated, routine work within the approved scope and existing permissions may proceed without approval for each step. User-reserved actions, material architecture changes, and consequential external actions retain their applicable explicit-authority requirements. Activation does not expand tool or connector permissions.

## Execution rules

- Work from the repository root unless a task is explicitly scoped to a subdirectory.
- Inspect `git status`, the active branch, and recent relevant commits before editing.
- Use a short plan for multi-file or high-risk changes.
- Prefer repository tools, scripts, tests, and validators over manual repetition.
- Use project subagents under `.codex/agents/` for distinct research, review, implementation, or record-keeping work.
- Keep delegated scopes non-overlapping and require file- or source-specific findings.
- Run the narrowest relevant validation first, then the full project validator.
- Do not modify `.git`, credentials, external systems, or protected evidence without explicit authority.
- Use `.codex/config.toml` only after the repository is trusted.

## Skills

Codex discovers repository skills under `.agents/skills/`. Use `complex-project-bootstrapper` for new or retrofit project setup. Use the skill installer or public skill search only after reviewing the skill source and permissions.

## Output standard

At completion, report:

1. What changed.
2. What was validated and the result.
3. Remaining risks or unknowns.
4. Exact files updated.
5. Whether changes were committed or pushed, with the verified commit identifier if applicable.
