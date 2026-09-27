# MASTER MISTRAL — Vibe (Le Chat) Project Instructions

## Role

Use Mistral Vibe (formerly Le Chat) for synthesis, research, drafting, and connector-aware work. The GitHub repository is the durable project record.

## Project setup

- In Vibe's **Work** mode, create a dedicated Project for this repository. A chat belongs to exactly one Project, so keep this repository's work inside it.
- Paste `.mistral/PROJECT_INSTRUCTIONS.md` into the Project's custom instructions.
- Connect the **GitHub App** connector so chats can read the repository directly.
- If the repository cannot be connected, add the compact control files listed in `.mistral/PROJECT_KNOWLEDGE.md` to the Project or an attached Library.
- Keep durable rules in this repository: account-wide custom instructions apply only to new tasks and are overridden by active Skills.

## Startup

Read `PROJECT_CHARTER.md`, `PROJECT_STATE.md`, `OPEN_LOOPS.md`, `DECISIONS.md`, `SOURCE_INDEX.md`, and `HANDOFF_CURRENT.md` before substantive work — through the GitHub connector when available. Prefer the newest repository versions over files uploaded to the Project or a Library.

## Work and closeout

Apply `MASTER_INSTRUCTIONS.md`. Separate facts, inferences, allegations, proposals, and unknowns, and preserve provenance. Default connectors to read-only; the GitHub connector can manage issues and pull requests, but use write actions only on the user's explicit current instruction. At the end of meaningful work, produce commit-ready updates to the project state, open loops, decisions, source index, risks, changelog, and handoff. Never imply a commit or push occurred unless it was verified.

## Notes

- Memories (legacy Chat mode) are convenience context only; the repository, not Memories, is the cross-session source of truth.
- MCP connectors are added by a workspace admin; on personal plans the account owner is the admin by default. Record any additions in `CONNECTOR_PLAN.md`.
