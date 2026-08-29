# MASTER CODEX — Repository Execution Instructions

## Native loading

Codex reads `AGENTS.md`. Treat that file as the startup router and this file as the Codex-specific operating layer.

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
