# Universal AI Project Template

A repo-first operating system for complex, ongoing, high-stakes, or multi-session work across **ChatGPT, Codex, Claude, Claude Code, Mistral Vibe, and GitHub**.

The repository is the durable source of truth. Each AI surface gets a small native entry file that loads the same project charter, state, decisions, sources, and handoff record. The result is continuity without depending on a single chat thread or a single vendor's memory.

## What this template solves

- Starts a complicated project with one reusable intake prompt.
- Reuses verified intake and asks only missing, decision-relevant questions in stages.
- Produces a tailored project charter, state file, source ledger, risk register, connector plan, and skill plan.
- Gives Codex and Claude Code native instruction files they automatically discover.
- Gives ChatGPT, Claude web, and Mistral Vibe exact Project instructions and a minimal file/source list.
- Creates portable `SKILL.md` workflows for Codex, ChatGPT, and Claude Code.
- Preserves session handoffs so another model can continue from the same branch and state.
- Validates the repository before work is committed or handed off.
- Keeps generated projects inactive until the architecture package is ready and the user explicitly approves its fingerprint.

## Fastest start

### From the base template repository

Use the `software-hardware` profile (add `--no-hardware` for a software-only project, which loads the `web-ui` track instead of `hardware`). Create a separate project in a new/empty directory:

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

Open [`prompts/BOOTSTRAP_NEW_PROJECT.md`](prompts/BOOTSTRAP_NEW_PROJECT.md), paste it into ChatGPT, Codex, Claude, Claude Code, or Mistral Vibe, and answer only missing intake questions. A repository-capable client runs the setup/review flow; a web-only client without a validator runtime prepares files and a runtime handoff while autonomy remains off.

## Architected work packets

Use [`WORK_PACKET_PROTOCOL.md`](WORK_PACKET_PROTOCOL.md) to define bounded tasks with a shared JSON contract, dependency validation, versioned history and generated GitHub issue bodies. The example covers software/hardware. Install `requirements-work-packets.txt` before using the packet commands. These tools record local metadata; live execution and external acceptance verification remain separate workstreams.

[`MODEL_ROUTING.md`](MODEL_ROUTING.md) adds deterministic capability/effort routing with risk floors, cost-per-accepted-result estimates, bounded escalation and provider fallback. It saves replayable local decision records. The shipped provider resources are disabled synthetic examples; the router does not call models or activate autonomy.

[`FEEDBACK_PROTOCOL.md`](FEEDBACK_PROTOCOL.md) adds durable dispatch reservations, cumulative task/tier limits, repeated-failure escalation, focused evidence context and architect/human holds. Its local event ledger survives restarts and preserves budgets across contract repairs. Model execution and independent acceptance remain separate gates.

## Native entrypoints

| Surface | Native entrypoint | Shared files it loads or directs the model to read |
|---|---|---|
| Codex | `AGENTS.md` | `MASTER_INSTRUCTIONS.md`, `MASTER_CODEX.md`, project state files |
| Claude Code | `CLAUDE.md` | Imports the universal and Claude Code masters plus active state |
| ChatGPT web Project | `.chatgpt/PROJECT_INSTRUCTIONS.md` | Add the compact control files and use the GitHub connector |
| Claude web Project | `.claude-web/PROJECT_INSTRUCTIONS.md` | Add the GitHub repo/integration and active control files |
| Mistral Vibe Project | `.mistral/PROJECT_INSTRUCTIONS.md` | Connect the GitHub App connector and use the compact control files in `.mistral/PROJECT_KNOWLEDGE.md` |
| GitHub Copilot | `.github/copilot-instructions.md` | Universal rules and project state |

## Repository map

```text
.
├── MASTER_INSTRUCTIONS.md
├── MASTER_CHATGPT.md
├── MASTER_CODEX.md
├── MASTER_CLAUDE.md
├── MASTER_CLAUDE_CODE.md
├── MASTER_MISTRAL.md
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
├── instructions/tracks/
├── archive/
├── .chatgpt/
├── .claude-web/
├── .mistral/
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

## CLI exit codes

Every `scripts/*.py` command follows one exit-code policy (ADR-072). Adopting it changed no command's existing code.

| Code | Meaning |
|---|---|
| 0 | Success, or an outcome the command reports in its output. A command can exit 0 on a hold, as the table below shows, so read its JSON `status`. |
| 1 | A handled refusal: invalid input found after argument parsing, a failed validation, or a refused operation. The reason is printed. A missing `jsonschema` also exits 1, with the install instruction. |
| 2 | A not-OK outcome from one of three sources. An argparse usage error prints usage on stderr and nothing on stdout. A domain stop or hold prints JSON with `status`, or with `valid: false`. `validate_bootstrap.py` exits 2 when it cannot read or parse its file. Tell them apart by stdout, never by the code alone. |
| 130 | Interrupted (Ctrl+C) at any point from the command's first statement, including while it loads its modules. No traceback is printed. Only the interpreter's own startup comes before that point. |

| Command | 0 | 1 | 2 (besides usage errors) |
|---|---|---|---|
| `acceptance.py` | JSON result with any other `status` | `Acceptance refused: …` | JSON `status` `ESCALATION_REQUIRED`, `ARCHITECTURE_CONFLICT` or `USER_REJECTED` |
| `bootstrap_gate.py` | `Bootstrap state: …` | `BOOTSTRAP BLOCKED: …` (stdout) | — |
| `bootstrap_project.py` | Project generated | `BOOTSTRAP BLOCKED: …`, or a stated reason such as an unrecognized template, a non-empty destination, invalid intake or a generated project that failed validation | Its `parser.error` refusals: no `--interactive` or `--answers`, existing bootstrap state, an initialized project, malformed answers, no canonical profile |
| `execution_harness.py` | JSON result. A hold other than `BLOCKED` (such as `NEEDS_DECISION`, `NEEDS_ARCHITECT` or `HARNESS_UNAVAILABLE`) also exits 0 | `Execution harness refused: …` | JSON `status` `BLOCKED` |
| `software_hardware.py` | JSON result | `Domain rule refused: …` | — |
| `feedback.py` | JSON result. `next` exits 0 only for `DISPATCH`; every other command exits 0 whatever state it records | `Feedback control refused: …` | `next` with any other `status`, a recorded hold such as `BLOCKED`, `NEEDS_ARCHITECT` or `NEEDS_DECISION` |
| `hash_file.py` | File metadata | — | `Not a file` (an argparse error) |
| `model_router.py` | `validate-config`, `verify`, and `route` when `ROUTED` | `Model routing failed: …` | `route` JSON `status` `STOP`; the record is still saved |
| `sync_skills.py` | Synchronized, or verified with `--check`; it also builds the untracked standalone-skill payload, so distribute the skill as a release zip built by running it (ADR-083) | `BOOTSTRAP PAYLOAD DRIFT` with `--check` | — |
| `validate_bootstrap.py` | `BOOTSTRAP VALID` | `BOOTSTRAP INVALID` with reasons, or `--require-active` on a path that is not a project's `config/bootstrap.json` | `BOOTSTRAP INVALID: <read error>`: the file is missing, unreadable or not JSON |
| `validate_project.py` | `VALIDATION PASSED` | `VALIDATION FAILED` | — (it takes no arguments) |
| `work_packet.py` | Valid, rendered or recorded | `WORK PACKET INVALID: …` | — |

An interrupt stops work without undoing it. Every command routes through `scripts/cli_exit.py`, which reports the interrupt and exits 130; it never writes, repairs or removes a ledger, report or evidence file. Records written before the interrupt stay, so check `status` before retrying. An event being appended to an acceptance or feedback ledger, and a new file being created by the packet, routing, acceptance or harness commands, is finished before the interrupt takes effect. The bootstrap commands give no such guarantee: an interrupted `bootstrap_project.py` can leave a partly generated destination, which holds no approval and must be removed before generating again, and an interrupted `bootstrap_gate.py review` can leave approval revoked until review is run again.

During `acceptance.py run-checks`, the check's owner ends its whole process tree before the interrupt is reported. No checks are recorded, unless the interrupt arrived while the finished results were being written. If the tree cannot be confirmed stopped, the run is refused (exit 1) instead of reported as cancelled. A further Ctrl+C during that teardown waits until the teardown finishes, which is bounded. On Windows, Ctrl+C also reaches a check that shares the console; the owner still ends whatever remains through the check's job object. Stopping a process never records an outcome: a dispatched attempt is still closed only with `execution_harness.py abandon` (ADR-011), and acceptance still needs its gates. An unexpected exception exits 1 with a traceback; that is a defect report, not a refusal.

## Operating rule

**GitHub holds durable state; chats perform work.** A chat is not the record unless its decisions, sources, and next actions are written back to the repository.

## Security default

Use a private repository for personal, regulated, proprietary, or identifying information. Keep secrets out of Git. Store sensitive originals in an appropriate controlled system and track them in `SOURCE_INDEX.md` by location, hash, authority, and access scope.

## Template status

This repository intentionally contains placeholders. Generated project repositories set `config/project.json -> template_mode` to `false`; repository validation then rejects unresolved placeholders. That setting is not activation: generated bootstrap state remains `INTAKE` until explicit approval. Canonical templates carry snapshots of existing domain documents; the `software-hardware` profile is the only canonical domain.

