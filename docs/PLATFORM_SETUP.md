# Platform Setup

## Universal design

The shared files are vendor-neutral. Native entrypoints make each client actually load them:

- Codex automatically discovers `AGENTS.md` and project `.codex/config.toml` in trusted repositories.
- Claude Code automatically reads `CLAUDE.md`; it can import shared files with `@path` and loads project skills and agents from `.claude/`.
- ChatGPT Projects use Project instructions, uploaded/source files, memory, and connected apps.
- Claude Projects use project instructions, project knowledge, and integrations such as GitHub.

## ChatGPT web

1. Create a new Project.
2. Paste `.chatgpt/PROJECT_INSTRUCTIONS.md` into Project settings.
3. Add the compact files in `.chatgpt/PROJECT_FILES.md`.
4. Connect GitHub and only the additional apps listed in `CONNECTOR_PLAN.md`.
5. Install `skill.zip` through the Skills interface when you want the bootstrap workflow available across chats.
6. Start with `prompts/START_SESSION.md` or the bootstrap prompt.

## Codex

1. Clone the repository and open Codex at the repo root.
2. Trust the project only after reviewing `.codex/config.toml`, hooks, rules, and skills.
3. Codex reads `AGENTS.md`; do not rename it to a custom master filename.
4. Repository skills live under `.agents/skills/`.
5. Project subagents live under `.codex/agents/`.
6. Run the validator before handing work to another client.

## Claude web

1. Create a Project and paste `.claude-web/PROJECT_INSTRUCTIONS.md`.
2. Add the repository through the GitHub integration.
3. If the full repo cannot be added, add the compact knowledge set listed in `.claude-web/PROJECT_KNOWLEDGE.md`.
4. Treat project knowledge, not prior chat history, as the cross-chat source.

## Claude Code

1. Start at the repo root.
2. Review `.claude/settings.json` before trusting the project.
3. Claude Code reads `CLAUDE.md`, which imports shared masters and state.
4. Skills live under `.claude/skills/`; subagents under `.claude/agents/`; stable rules under `.claude/rules/`.
5. Run `/context` or the relevant diagnostics to confirm loaded instructions when behavior is uncertain.
