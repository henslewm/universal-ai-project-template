# Domain Profile — Software + Hardware Interfaces

This is the default `main` specialization of the universal autonomous project template: software
that interacts with physical hardware, built so that most bounded work can go to cheap or local
models while no claim of hardware success is ever made on the strength of compilation or
simulation. `AUTONOMY_CONTROL_PLANE.md` is the controlling workflow policy; the controllers named
below are the mechanism.

## Startup gate

Autonomy is OFF until interactive intake is complete and the user approves the exact package.
`scripts/validate_bootstrap.py` requires, for this profile, a meaningful answer to every domain
orientation field before review or activation: existing baseline; exact hardware identity and
firmware; interfaces and protocols; authoritative specifications; host and deployment
environment; known-good and known-failing paths; fixtures, simulators, loopback and
hardware-in-loop resources; physical-access constraints; and the architecture boundaries whose
change requires approval. The architect then presents the component boundaries, dependency graph,
hardware abstraction boundary, verification ladder per component, routing policy, first milestone
and stop conditions. A placeholder answer is refused, not deferred.

## Decomposition

Prefer components that can be validated without physical hardware. Every packet names exactly one
component from the profile's separation list: protocol codec, transport, device abstraction,
hardware adapter, configuration, persistence, business logic, UI/API, simulator/fake,
telemetry/logging, deployment/operations. A packet that spans several is not independently
testable and is decomposed further. Hardware-facing components expose contracts that a fake or
loopback can satisfy, so their host-side rules are machine-runnable even when the device is not
on the bench. `examples/software-hardware/` is a complete worked decomposition.

## Work packet

The common contract is unchanged. For this profile the `domain` block is structural, validated by
`config/domains/software-hardware.schema.json` and `scripts/software_hardware.py` wherever a
contract is validated:

- `component`: the one separation category.
- `hardware_assumptions`: every physical behavior the packet relies on, each citing a contract
  source. Empty means the packet is `NOT_HARDWARE_FACING`.
- `protocol_references`: the specification sources implemented against; required when any
  hardware assumption exists.
- `validation_levels`: every validation id mapped to exactly one rung of the ladder.
- `hardware_status`: `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING`. A contract cannot declare
  `VERIFIED_ON_HARDWARE`; it is earned, never authored. The block is closed — no undeclared key
  and no free text can carry that literal anywhere in it — and `validate_contract` takes the
  profile as a required argument, so no caller skips these rules by omitting it.

## Verification ladder

static → unit → contract → simulation/loopback → integration → hardware-in-loop → representative
field workflow where required.

The first five rungs are machine-runnable: each such validation must declare a `command`, and the
acceptance controller's deterministic gate re-executes it in the reviewed workspace and records
what it observed (ADR-014). The two hardware rungs must not declare a command: they fail closed to
an attestation by a non-implementer operator, and that attestation must bind a structured hardware
evidence record by digest. A hardware rung with a command is refused as a simulator masquerading
as hardware; a machine rung without one is refused as attestation substituting for a runnable
check. `software_hardware.py status` derives the earned status from the ledger:
`VERIFIED_ON_HARDWARE` only for an accepted task whose hardware rungs were all attested and whose
contract does not declare `domain.synthetic: true` — a synthetic contract's inputs are fictional
by that declaration, so its hardware rungs can be attested and their bound records re-verified,
but the derived status stays `UNVERIFIED_ON_HARDWARE` regardless; every worked example in this
template declares it. A compile or simulation pass never upgrades it. The output names its
`evidence_basis`: without
`--evidence-dir` the status rests on the ledger's attestations and their declared digests, and
says it is attested, not record-verified; with `--evidence-dir` every bound record is found by
digest, validated as a hardware evidence record, and re-verified for task, validation, rung, a
`pass` outcome, the attesting operator and every line the attestation carried, compared exactly
except for the operator — a digest proves which bytes were bound, not that they are a record or
that they say what was attested. A ledger stored before these rules existed replays marked with
its shortfall for audit and acceptance status; only new events are refused, and the hardware
status is the one derivation that refuses (ADR-032).

## Code structure

Keep code modular so a model can change one part without re-reading the whole codebase. Firmware
lives in single-responsibility modules listed in a `MODULES.md` index beside the sources: one row
per module naming what it owns, its public API and what it depends on. Each module's header is its
contract. An Arduino `.ino` holds only `setup()`/`loop()`. Shared state is written only by its
owning module. New behavior goes in its owning module or a new one, never back into a monolithic
file, and the index changes in the same commit. Scripts follow the same rule: one focused module
or helper per concern. Splitting an existing monolith is a mechanical move with an equivalence
check (for example, comparing the built binaries), never a rewrite. See `.claude/rules/05-modular-code.md`.

## Build configuration (Arduino / ESP32)

Every Arduino or ESP32 firmware project keeps a root `platformio.ini`, generated under
`docs/PLATFORMIO.md` from observed hardware (`esptool flash-id`: chip, flash size, embedded PSRAM)
and the project's pinned core. Stock `espressif32@6.x` ships Arduino-ESP32 2.0.x. Core 3.x needs a
pinned pioarduino release URL, never a floating version. Ports are selected by USB VID:PID, not
COM number. The default environment's log level respects the project's boot and log rules. The
equivalent arduino-cli FQBN is recorded, and evidence names the toolchain, build identifier and ELF
hash of every flashed artifact.

Hardware-facing lessons from a composite BLE HID project (template issue #51):

- A pinned-core defect can look like a descriptor or host problem. Print the actual GATT handles,
  and log raw stack events (including ones the framework wrapper ignores), before editing report
  maps or blaming the host. Add observation-only diagnostics before any fix.
- Arduino-ESP32 3.3.12 with NimBLE silently drops a second characteristic with the same UUID, for
  example a second HID input report (0x2A4D). Its handle stays 0xFFFF.
- A Windows desktop process pairs a BLE peripheral through exact-address
  `BluetoothLEDevice.FromBluetoothAddressAsync` and custom `ConfirmOnly` pairing. Association
  endpoint enumeration and plain `PairAsync()` are unreliable without pairing UI.
- Leaving a peripheral mode must end the host link, not only advertising.
## Cost posture

Pure functions, codecs, parsers, fixtures, fakes, tests, log analysis and repetitive adapters route
to the local tiers first; objective failures and risk, never preference, drive escalation. The
hardware adapter and the integration/field packets carry `high` risk so the acceptance floor adds
independent model review and the cross-family gate. Hardware runs are operator actions and are
never dispatched to a worker.

## GitHub ledger

One tracking issue per milestone with its dependency-ordered wave plan; one issue per packet;
new findings become separate issues; PRs link the packet and carry validation evidence. Hardware
observations are recorded as bound evidence records and their attestations, not as prose in a
comment.

## Human-intervention gate

Routine implementation, testing, issue/PR updates, model escalation and bounded refactoring
proceed autonomously inside the approved architecture. Stop for user approval before materially
changing protocol assumptions, hardware support scope, public interfaces, persistence
architecture, the security/authentication model, deployment topology, core framework/language, or
the hardware abstraction boundary. Any action on physical hardware that can damage it, or any
claim of hardware verification, is an operator action recorded as evidence, never an autonomous
step.
