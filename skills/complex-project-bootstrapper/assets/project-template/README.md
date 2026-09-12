# Universal AI Project Template

A repo-first operating system for complex, ongoing, high-stakes, or multi-session work across **ChatGPT, Codex, Claude, Claude Code, and GitHub**.

The repository is the durable source of truth. Each AI surface gets a small native entry file that loads the same project charter, state, decisions, sources, and handoff record. The result is continuity without depending on a single chat thread or a single vendor's memory.

## What this template solves

- Starts a complicated project with one reusable intake prompt.
- Reuses verified intake and asks only missing, decision-relevant questions in stages.
- Produces a tailored project charter, state file, source ledger, risk register, connector plan, and skill plan.
- Gives Codex and Claude Code native instruction files they automatically discover.
- Gives ChatGPT and Claude web exact Project instructions and a minimal file/source list.
- Creates portable `SKILL.md` workflows for Codex, ChatGPT, and Claude Code.
- Preserves session handoffs so another model can continue from the same branch and state.
- Validates the repository before work is committed or handed off.
- Keeps generated projects inactive until the architecture package is ready and the user explicitly approves its fingerprint.

## Fastest start

### From the base template repository

Choose a canonical profile: `software-hardware`, `family-law`, or `civil-rights-nc`. Create a separate project in a new/empty directory:

```bash
python scripts/bootstrap_project.py --interactive --profile software-hardware --destination ../my-project --no-git
```

After using GitHub **Use this template**, tailor the uninitialized repository in place:

```bash
python scripts/bootstrap_project.py --interactive --profile software-hardware --destination . --no-git
```

To reuse verified intake, add `--answers verified-intake.json`; interactive mode asks only missing common and profile orientation fields. The generator writes tailored files, `config/bootstrap.json` in `INTAKE` with autonomy off, and `BOOTSTRAP_REVIEW.md` with readiness gaps. `--no-git` keeps preparation separate from Git initialization or publishing. Rebootstrap of an initialized project is refused; preserve existing records through a retrofit or revise its existing bootstrap package.

### Review and activate the foundation

Use [`prompts/INTERACTIVE_BOOTSTRAP.md`](prompts/INTERACTIVE_BOOTSTRAP.md) to complete the architecture, sources, risks, routing, GitHub workflow, reserved actions, and domain orientation in `config/bootstrap.json`. Resolve the `unresolved` architecture blockers, then run from the generated project's root:

```bash
python scripts/bootstrap_gate.py review
```

Review revokes any previous approval first, snapshots `config/project.json`, hashes `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md`, and checks readiness. Success writes `AWAITING_APPROVAL` and the review package. Present `BOOTSTRAP_REVIEW.md` and those documents to the user.

Only after explicit user authorization for the approval interaction, run:

```bash
python scripts/bootstrap_gate.py activate
python scripts/validate_bootstrap.py config/bootstrap.json --require-active
```

Activation presents the exact package and asks for the user's identity and `APPROVE <fingerprint>`; there is no noninteractive autoapprove option. The receipt lives in `config/bootstrap.json`, while the review file remains the pre-approval proposal. The fingerprint binds project/architecture data, sources, risks, routing, human gates, `domain`, `workflow`, `unresolved`, configuration, and document hashes.

Every new session must pass `--require-active` against the current configuration and documents before autonomous substantive work. Missing, invalid, or inactive state, stale bindings, or no available runtime means no autonomy. Resume bootstrap/review or prepare a runtime handoff. After activation, routine approved-scope work can continue within existing permissions; reserved actions and consequential external writes retain their explicit-authority requirements. See [`BOOTSTRAP_PROTOCOL.md`](BOOTSTRAP_PROTOCOL.md) for the full state and recovery rules.

The local gate prevents normal workflow bypass and detects stale approvals. It does not authenticate humans or constrain actors who rewrite gate code or approval records. Activation does not configure providers, change permissions, initialize Git, or publish a repository. See [`docs/GITHUB_PUBLISH.md`](docs/GITHUB_PUBLISH.md) for publishing when authorized.

### From an AI chat

Open [`prompts/BOOTSTRAP_NEW_PROJECT.md`](prompts/BOOTSTRAP_NEW_PROJECT.md), paste it into ChatGPT, Codex, Claude, or Claude Code, and answer only missing intake questions. A repository-capable client runs the setup/review flow; a web-only client without a validator runtime prepares files and a runtime handoff while autonomy remains off.

## Architected work packets

Use [`WORK_PACKET_PROTOCOL.md`](WORK_PACKET_PROTOCOL.md) to define bounded tasks with a shared JSON contract, dependency validation, versioned history and generated GitHub issue bodies. Examples cover software/hardware, family law and civil rights. Install `requirements-work-packets.txt` before using the packet commands. These tools record local metadata; provider routing, live execution and external acceptance verification remain separate workstreams.

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

This repository intentionally contains placeholders. Generated project repositories set `config/project.json -> template_mode` to `false`; repository validation then rejects unresolved placeholders. That setting is not activation: generated bootstrap state remains `INTAKE` until explicit approval. Canonical templates carry snapshots of existing domain documents; detailed domain schemas and workflows remain assigned to #9/#10/#11.
