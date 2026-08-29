# Universal New-Project Bootstrap Prompt

Use the repository containing this prompt as the template for a new complex project.

First inspect any context, files, connectors, and repository state already available. Do **not** ask me for information you can reliably infer or retrieve. Then ask me one compact numbered intake block containing only the missing items, with sensible defaults or choices. Ask no more than eight questions and use at most one follow-up round for true blockers.

The intake must cover, only where missing:

1. Project name and one-sentence desired outcome.
2. Observable definition of done, required deliverables, and target date or urgency.
3. Domain, jurisdiction/version where relevant, risk tier, and sensitivity.
4. Authoritative source locations and which sources control when they conflict.
5. AI surfaces to support: ChatGPT, Codex, Claude web, Claude Code, or others.
6. External systems/connectors needed and the read/write boundary for each.
7. Repeated workflows that deserve a skill, plus required output formats.
8. Non-negotiable constraints, exclusions, approval gates, and people responsible.

After I answer, do not keep interviewing unless a missing fact makes safe execution impossible. Use best judgment and document assumptions.

Then perform the setup:

1. Duplicate this template into a new repository/directory with a clean Git history.
2. Fill `config/project.json` and replace all project placeholders.
3. Tailor `PROJECT_CHARTER.md`, `PROJECT_STATE.md`, `OPEN_LOOPS.md`, `FACTS_AND_ASSUMPTIONS.md`, `RISK_REGISTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `HANDOFF_CURRENT.md`.
4. Keep `MASTER_INSTRUCTIONS.md` universal. Tailor only the platform master files that need project-specific additions.
5. Preserve native entrypoints: `AGENTS.md`, `CLAUDE.md`, `.chatgpt/`, `.claude-web/`, `.codex/`, `.claude/`, and `.agents/skills/`.
6. Select the minimum useful connector set. Default to read-only and require explicit approval for consequential external writes.
7. Enable existing trusted skills when they fit. Create a custom skill only for a repeated, quality-sensitive, deterministic, tool-heavy, or specialized workflow. Record every selection and reason in `SKILL_PLAN.md`.
8. Put sensitive originals in the approved source system; store source metadata, links, hashes, and redacted/derived material in the repo as appropriate.
9. Run `python scripts/validate_project.py` and fix all errors.
10. Initialize Git and create the first commit when execution and permission allow.
11. If GitHub write access and the GitHub CLI are available, create a private repository and push. Otherwise, produce a complete archive plus the exact publish command. Never claim a push occurred unless verified.
12. Return a concise setup report containing:
    - repository path/name;
    - files tailored;
    - connectors selected and permission posture;
    - skills enabled/created and why;
    - exact ChatGPT Project and Claude Project setup steps;
    - validation result;
    - commit/push status;
    - first three project actions.

For command-line execution, prefer:

```bash
python scripts/bootstrap_project.py --interactive --destination ../<project-slug>
```
