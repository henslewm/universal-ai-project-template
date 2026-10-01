# Track: web-ui (web-frontend software, no hardware)

Software whose only interface is a web UI. There is no hardware, so none of the hardware rungs of the verification ladder apply. This track has no bootstrap domain profile yet (ADR-082), so `bootstrap_project.py` does not select it.

## Provisional verification

The owner has not defined this track's verification ladder. Until then use only the machine-runnable rungs of `DOMAIN_PROFILE.md`'s ladder (static, unit, contract, integration), each with a declared command the acceptance controller re-runs. Claim nothing about real browsers, devices or users that no command observed.

## Read

- `MASTER_INSTRUCTIONS.md` work standard and `WORK_PACKET_PROTOCOL.md`.
- `docs/WEBUI_SETUP.md` is about working through a chat web UI, not about this track.
