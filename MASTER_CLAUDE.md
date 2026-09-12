# MASTER CLAUDE — Claude Web Project Instructions

## Role

Use Claude web for synthesis, research, drafting, and long-context analysis. The GitHub repository is the durable project record.

## Project setup

- Add the repository through Claude's GitHub integration when available.
- Paste `.claude-web/PROJECT_INSTRUCTIONS.md` into the Project instructions field.
- Add active control files to project knowledge if the repository is not fully connected.
- Do not assume one chat's context is available in another unless the information is in project knowledge or the repository.

## Startup

Read `PROJECT_CHARTER.md`, `PROJECT_STATE.md`, `OPEN_LOOPS.md`, `DECISIONS.md`, `SOURCE_INDEX.md`, and `HANDOFF_CURRENT.md` before substantive work. Check the repository for newer versions than any uploaded copies.

## Bootstrap / autonomy gate

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` against the current repository from its root. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, and a matching material-architecture fingerprint. If the bootstrap state is missing, invalid, or inactive, or this surface has no runtime capable of running the validator, do not proceed autonomously. Resume bootstrap through `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md`, preparing the approval package or a runtime handoff within existing permissions. Uploaded state or a model's assertion cannot replace the validation gate.

Once activated, routine work within the approved scope and existing permissions may proceed without approval for each step. User-reserved actions, material architecture changes, and consequential external actions retain their applicable explicit-authority requirements. Activation does not expand tool or connector permissions.

## Work and closeout

Apply `MASTER_INSTRUCTIONS.md`. Preserve source distinctions and write durable outputs back to the repository when tools permit. If the integration is read-only, produce exact commit-ready files or patches and a concise handoff.
