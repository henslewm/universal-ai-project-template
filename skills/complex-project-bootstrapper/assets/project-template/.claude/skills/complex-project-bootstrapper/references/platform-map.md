# Platform Map

| Client | Native project mechanism | Required template adapter |
|---|---|---|
| Codex | `AGENTS.md`; trusted `.codex/config.toml`; `.agents/skills`; `.codex/agents` | Keep `AGENTS.md` as a concise router to shared masters and state |
| Claude Code | `CLAUDE.md` imports; `.claude/settings.json`; `.claude/rules`; `.claude/skills`; `.claude/agents` | Import shared masters/state from `CLAUDE.md` |
| ChatGPT web Project | Project instructions, Project files/sources, connected apps, skills | Paste `.chatgpt/PROJECT_INSTRUCTIONS.md`; add compact active files; connect GitHub |
| Claude web Project | Project instructions, project knowledge, GitHub/Drive integrations | Paste `.claude-web/PROJECT_INSTRUCTIONS.md`; add repo or compact knowledge set |
| GitHub Copilot | `.github/copilot-instructions.md` | Point to universal control files |

Custom master filenames are not sufficient by themselves. Preserve the native entrypoint each client actually discovers.
