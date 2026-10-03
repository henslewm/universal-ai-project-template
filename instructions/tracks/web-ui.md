# Track: web-ui (web-frontend software, no hardware)

Software whose only interface is a web UI. There is no hardware, so none of the hardware rungs of the verification ladder apply. It is selected at bootstrap with `bootstrap_project.py --no-hardware` (or answering no to "Does the project involve hardware?"). The project still uses the `software-hardware` profile; the hardware-only intake fields (`hardware_identity`, `physical_access`) are filled with a fixed "no hardware" statement and this track is imported instead of `hardware`.

## Provisional verification

The owner has not defined this track's verification ladder. Until then use only the machine-runnable rungs of `DOMAIN_PROFILE.md`'s ladder (static, unit, contract, integration), each with a declared command the acceptance controller re-runs. Claim nothing about real browsers, devices or users that no command observed.

## Read

- `MASTER_INSTRUCTIONS.md` work standard and `WORK_PACKET_PROTOCOL.md`.
- `docs/WEBUI_SETUP.md` is about working through a chat web UI, not about this track.
