# Track: hardware (ESP32 / Arduino / SatLink3, hardware-in-loop)

Software that talks to physical hardware. Loaded for projects whose domain profile is `software-hardware`. The universal and platform masters still control (`MASTER_INSTRUCTIONS.md` authority order); this file sits with the selected profile materials, not above them.

## Read for this track

- `DOMAIN_PROFILE.md`: decomposition, work-packet `domain` block, verification ladder, `hardware_status`. It is the controlling text; this file does not restate it.
- `docs/PLATFORMIO.md` for `platformio.ini`, pinned Arduino core and ports.
- `.claude/rules/05-modular-code.md` and `.claude/rules/06-platformio.md`. Claude Code loads them only when firmware paths are touched. Other platforms do not load this track automatically yet (ADR-082); read it explicitly.

## Rules that matter most

- No claim of hardware success from compilation or simulation. `VERIFIED_ON_HARDWARE` is earned by an attested hardware-in-loop rung bound to the flashed artifact's SHA-256 (`artifact_sha256` in the hardware evidence record, checked by `scripts/software_hardware.py`), never authored in a contract. Printing the firmware's runtime ELF hash and recording it beside that artifact is practice (`docs/PLATFORMIO.md`), not a field the controller verifies.
- Before firmware work, read the `MODULES.md` index beside the sources and open only the modules that own the state you change.

## SatLink3

No SatLink3 interface, protocol, fixture or test-bench specification is recorded in this repository. Do not infer one. The owner supplies it (ADR-082); until then a SatLink3 packet has no `protocol_references` and cannot declare hardware assumptions.
