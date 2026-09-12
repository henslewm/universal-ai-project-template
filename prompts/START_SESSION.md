# Start Session Prompt

Read the native instruction entrypoint and current project control files. Check the branch, working tree, latest relevant commits, and `HANDOFF_CURRENT.md`.

Before autonomous substantive work in every session, run `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` from the repository root. Continue autonomously only after successful validation confirms `ACTIVE`, explicit approval, and a matching material-architecture fingerprint. Missing, invalid, or inactive bootstrap state, or an unavailable runtime/validator, means no autonomous execution: resume bootstrap through `BOOTSTRAP_PROTOCOL.md` and `prompts/INTERACTIVE_BOOTSTRAP.md` within existing permissions.

State the active objective, validation result, and next best action in no more than five lines. If the gate passes, execute routine work within the approved scope and existing permissions without approval for each step. Otherwise, continue only the applicable bootstrap preparation or runtime handoff. User-reserved actions, material architecture changes, and consequential external actions retain their applicable explicit-authority requirements; activation does not expand tool or connector permissions. Ask one concise question only when a true blocker requires it.
