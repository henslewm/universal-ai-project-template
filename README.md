# Universal AI Project Template

A repo-first operating system for complex, ongoing, high-stakes, or multi-session work across **ChatGPT, Codex, Claude, Claude Code, and GitHub**.

The repository is the durable source of truth. Each AI surface gets a small native entry file that loads the same project charter, state, decisions, sources, and handoff record. The result is continuity without depending on a single chat thread or a single vendor's memory.

## What this template solves

- Starts a complicated project with one reusable intake prompt.
- Asks only the missing, decision-relevant questions in one compact batch.
- Produces a tailored project charter, state file, source ledger, risk register, connector plan, and skill plan.
- Gives Codex and Claude Code native instruction files they automatically discover.
- Gives ChatGPT and Claude web exact Project instructions and a minimal file/source list.
- Creates portable `SKILL.md` workflows for Codex, ChatGPT, and Claude Code.
- Preserves session handoffs so another model can continue from the same branch and state.
- Validates the repository before work is committed or handed off.

## Fastest start

### From this repository

```bash
python scripts/bootstrap_project.py --interactive --destination ../my-project
```

Then publish the generated local repository:

```bash
gh auth login
gh repo create henslewm/my-project --private --source ../my-project --remote origin --push
```

### From an AI chat

Open [`prompts/BOOTSTRAP_NEW_PROJECT.md`](prompts/BOOTSTRAP_NEW_PROJECT.md), paste it into ChatGPT, Codex, Claude, or Claude Code, and answer the compact intake block. A repository-capable client should run the bootstrap script; a web-only client should produce the completed files or an archive plus the publish command.

## Native entrypoints

| Surface | Native entrypoint | Shared files it loads or directs the model to read |
|---|---|---|
| Codex | `AGENTS.md` | `MASTER_INSTRUCTIONS.md`, `MASTER_CODEX.md`, project state files |
| Claude Code | `CLAUDE.md` | Imports the universal and Claude Code masters plus active state |
| ChatGPT web Project | `.chatgpt/PROJECT_INSTRUCTIONS.md` | Add the compact control files and use the GitHub connector |
| Claude web Project | `.claude-web/PROJECT_INSTRUCTIONS.md` | Add the GitHub repo/integration and active control files |
| GitHub Copilot | `.github/copilot-instructions.md` | Universal rules and project state |

## Repository map

```text
.
├── MASTER_INSTRUCTIONS.md
├── MASTER_CHATGPT.md
├── MASTER_CODEX.md
├── MASTER_CLAUDE.md
├── MASTER_CLAUDE_CODE.md
├── AGENTS.md
├── CLAUDE.md
├── PROJECT_CHARTER.md
├── PROJECT_STATE.md
├── OPEN_LOOPS.md
├── DECISIONS.md
├── FACTS_AND_ASSUMPTIONS.md
├── SOURCE_INDEX.md
├── RISK_REGISTER.md
├── HANDOFF_CURRENT.md
├── CONNECTOR_PLAN.md
├── SKILL_PLAN.md
├── prompts/
├── instructions/profiles/
├── .chatgpt/
├── .claude-web/
├── .codex/
├── .claude/
├── .agents/skills/
├── skills/
├── context/
├── evidence/
├── research/
├── work/
├── outputs/
├── templates/
├── scripts/
└── tests/
```

## Operating rule

**GitHub holds durable state; chats perform work.** A chat is not the record unless its decisions, sources, and next actions are written back to the repository.

## Security default

Use a private repository for personal, legal, regulated, proprietary, or identifying information. Keep secrets out of Git. Store sensitive originals in an appropriate controlled system and track them in `SOURCE_INDEX.md` by location, hash, authority, and access scope.

## Template status

This repository intentionally contains placeholders. Generated project repositories set `config/project.json -> template_mode` to `false`; validation then rejects unresolved placeholders.
