# Software + hardware example: the synthetic sensor bridge

A fictional device, decomposed the way the `software-hardware` profile requires, so that every
component is verified independently and the gap between simulated success and hardware
verification is visible in the records rather than in anyone's memory. Everything here is
invented. No frame, timing, device response or evidence record describes real hardware.

## SYNTH-FRAME-1 fixture specification (SRC-SYNTH-SPEC)

- Frame: `TAG(0xA1) LEN PAYLOAD[LEN] CHECKSUM`, where `LEN <= 16` and `CHECKSUM` is the XOR of
  every byte from `TAG` through the last payload byte.
- Read request: payload `0x01`, so the frame is `A1 01 01 A1`.
- Reply: a two-byte big-endian reading, so `A1 02 HH LL CK`.
- Any other tag, length or checksum is invalid and is named by its cause: `SHORT`, `BAD_TAG`,
  `BAD_LENGTH`, `BAD_CHECKSUM`; a reply whose payload is not two bytes is `BAD_PAYLOAD`.
- A device answers a read request with exactly one reply frame or stays silent.

## Decomposition

`sample/` holds the reference implementation and its 28 `unittest` checks. `packets/` holds one
contract per component; each packet's `context_scope` names only its own files and the
interfaces it consumes, so no worker needs the whole repository.

| Packet | Component | Rungs | Hardware status declared |
|---|---|---|---|
| `SHB-01-codec` | protocol_codec | unit, contract | UNVERIFIED_ON_HARDWARE |
| `SHB-02-transport` | transport | simulation | UNVERIFIED_ON_HARDWARE |
| `SHB-03-device` | device_abstraction (fake sensor as its test double) | simulation | UNVERIFIED_ON_HARDWARE |
| `SHB-04-adapter` | hardware_adapter | unit, **hardware_in_loop** | UNVERIFIED_ON_HARDWARE |
| `SHB-05-telemetry` | telemetry_logging | unit | NOT_HARDWARE_FACING |
| `SHB-06-workflow` | business_logic | integration, **field** | UNVERIFIED_ON_HARDWARE |

Dependency order: codec, transport and telemetry first; device after codec and transport; adapter
after transport; the workflow last, after codec, device, adapter and telemetry. A packet's
declared scope is checked against what its files actually import: `tests/test_software_hardware.py`
parses every module and test the `context_scope` names and refuses an import of a `synth_bridge`
module the packet neither owns nor lists as a consumed interface, and refuses a consumed interface
whose owning packet is not a declared dependency. The adapter's checks therefore speak raw
transport bytes; the device-through-adapter crossing lives in the workflow packet. The fake sensor lives in the device packet because it exists
only to test that boundary; a project with a richer simulator gives it its own `simulator_fake`
packet.

## What the split enforces

Every rung from `static` through `integration` declares a `command`, so the acceptance
controller's deterministic gate re-executes it in the reviewed workspace and records what it
observed. `hardware_in_loop` and `field` never declare one: they fail closed to an attestation by
a non-implementer operator, and that attestation must bind a hardware evidence record by digest.
The contract can declare only `UNVERIFIED_ON_HARDWARE` or `NOT_HARDWARE_FACING`;
`VERIFIED_ON_HARDWARE` is derived from the ledger and can be earned only by an accepted task whose
hardware rungs were all attested. Passing every fake-port test in `SHB-04-adapter` leaves it
`UNVERIFIED_ON_HARDWARE`; that is the point.

## Walkthrough

Run from the repository root with the interpreter that has `jsonschema` installed.

```text
python scripts/software_hardware.py validate-contract examples/software-hardware/packets/SHB-04-adapter.contract.json
python scripts/work_packet.py create examples/software-hardware/packets/SHB-01-codec.contract.json --task-id SHB-01-codec --profile software-hardware --actor "Architect" --reason "Synthetic decomposition" --output work/SHB-01-codec.json
python scripts/work_packet.py graph work/SHB-*.json
python scripts/acceptance.py --config config/acceptance.example.json run-checks LEDGER --workspace examples/software-hardware
python scripts/software_hardware.py hardware-evidence RECORD.json --validation-id VAL-HIL
python scripts/acceptance.py --config config/acceptance.example.json attest LEDGER --validation-id VAL-HIL --operator "<operator>" --evidence "<each line printed above>"
python scripts/software_hardware.py status LEDGER --evidence-dir RECORDS
```

The packets declare `python` as the interpreter and `sample` as the working directory; the
`tests/test_software_hardware.py` suite runs the same commands through the deterministic gate
with the test interpreter substituted. `hardware-evidence.example.json` shows the record shape for
`SHB-04-adapter`'s `VAL-HIL`; it is explicitly fictional.

## Operator procedure for hardware-rung attestation (SRC-HIL-PROCEDURE)

1. Confirm the deterministic gate has already run and every machine rung `PASSED`; a hardware
   run is never the first check.
2. Connect the physical unit as the packet's `test_setup` will describe. Record the exact device
   identity and firmware version from the unit itself, not from a manual.
3. Run the workflow the validation describes. Write down expected and observed behavior in enough
   detail that a later reader could contradict it, and keep captures or logs as artifacts.
4. Fill a hardware evidence record (`config/domains/software-hardware.schema.json`,
   `$defs/hardware_evidence`) with `outcome` `pass` or `fail`. A failed observation goes back to
   the worker as a failure; it is never attested.
5. Run `software_hardware.py hardware-evidence` on the record and pass every printed line to
   `acceptance.py attest`. The attesting operator must be the record's operator and must not be an
   implementation actor.
6. Keep the record file where `status --evidence-dir` can find it; the attestation's digest line
   is what binds it. Without `--evidence-dir`, `status` reports the attested digests as attested,
   not record-verified, and says so in `evidence_basis` and `reason`; with it, a record recorded by
   an operator other than the attesting one does not verify, even when the digest matches.

## Boundaries

The controller cannot authenticate the operator or inspect the bench. What it enforces is that a
hardware claim has a structural place, a named non-implementer, a bound record and a digest, so a
claim that was never observed cannot be recorded as if it had been. Whether the record is truthful
is the operator's accountability, and the record makes that auditable rather than invisible.
