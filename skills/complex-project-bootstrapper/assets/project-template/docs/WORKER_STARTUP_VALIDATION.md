# Lean automatic worker startup: validation

Date: 2026-09-27. Branch: `worker-startup-lean`, from `main` at `bd446ea`. Decision: ADR-070.
Authority: the maintainer's explicit instruction to re-land worker startup with a lean design,
replacing draft PR #55 (`d1daa59`).

## Why PR #55 was not merged

PR #55 embedded the complete text of `MASTER_INSTRUCTIONS.md`, `AUTONOMY_CONTROL_PLANE.md`,
`PROJECT_CHARTER.md`, `WORK_PACKET_PROTOCOL.md`, `EXECUTION_HARNESS_PROTOCOL.md`, `AGENTS.md` and
the worker rules in every brief. Rendered as the indented brief a worker receives, that was about
71k characters, about 20k tokens at the configured 3.5 characters per token. Add Cline's declared
7000-token overhead and the 4000-token growth reserve, and a worker needed about 34k tokens before
its contract. The harness's own capacity check would therefore refuse every example local binding
(8192 and 16384) and every cloud tier with a window up to 32k. Most of that text is for the architect
or integrator, and the brief then told the worker to ignore it. PR #55's tests used an unlimited
window, so none of them caught this.

## What a brief carries now

- `startup.rules`: the full text of `templates/harness/BOUNDED_WORKER_RULES.md` (3,715 characters), with its SHA-256.
- `startup.documents`: the full text of only the files the contract's optional `worker_instructions` names, in order, with digests.
- `startup.governance`: the path and SHA-256 of each of the five governing documents. Their text is never sent to a worker.
- `limits.startup_max_chars` (default 12000) caps rules plus documents.

As rendered in a brief with no `worker_instructions`, the startup block is 5,756 characters.

## Measured capacity (example Cline harness, real rules, real governing documents)

For the example software-hardware contract with 1,000 reserved output tokens:

| Served window | Result | Brief | Overhead | Growth reserve | Required | Headroom |
|---|---|---|---|---|---|---|
| 16,384 | PREPARED | 3,867 | 7,000 | 4,000 | 15,867 | 517 |
| 8,192 | refused | | | | 15,866 | |

The brief figure includes the rules. They are counted once, because the example argv now passes only
`{brief}`. The 8,192-token binding was already infeasible on `main`: 7,000 + 4,000 exceeds it before any brief.
That binding is unchanged here. The 517-token margin shows the capacity is tight. Keep the rules and
any `worker_instructions` short. The margin assumes 1,000 reserved output tokens. On a 16k window,
Cline's overhead plus the growth reserve leaves about 5,400 tokens for the brief and the output
together, even with no startup block. A packet that reserves 4,000 output tokens therefore needs
a larger served window whatever this change does.

## Checks

- A missing, empty, non-UTF-8, credential-like, linked or oversized source, or a missing governing document, refuses the dispatch before `feedback.reserve` is called. No attempt is spent and no run directory is left.
- Unsafe paths are refused: absolute paths, traversal, drive letters, Win32 device names and trailing dots. A `worker_instructions` entry is refused if it names a governing document (compared case-insensitively) or if its bytes match one, which catches a hard link or a copy. Governing text travels only as a digest.
- `verify-report` checks startup integrity: digests, no text in governance entries, and documents exactly matching the contract's `worker_instructions`. It still accepts an exact legacy `1.0` brief.
- A regression dispatches with the real rules and governing documents against the example 16384-token binding, and requires positive headroom.

## Results (Windows, system Python 3.12.8, `jsonschema` 4.26.0)

- `python -m unittest discover -s tests -p "test_*.py"`: 419 tests passed, 407 on `main` plus 12 new.
- `python scripts/validate_project.py`: 81 required paths passed, exit code 0.
- `python scripts/sync_skills.py`, then `--check`: in this Git worktree, `--check` reports drift on exactly one path, `skills/complex-project-bootstrapper/assets/project-template/.git`. That is the worktree's `.git` pointer file, which `sync_skills.py` copies into the payload. It is not ignored, so it was deleted and never committed. Every tracked payload file matches. In a normal clone, as CI uses, `.git` is a directory, is excluded, and the check passes. This is a pre-existing packaging limitation (#49), not part of this change.
- The template is intentionally unactivated. Bootstrap validation reports a missing `config/bootstrap.json`, and this work proceeds as authorized template maintenance.

These are synthetic local runs. No provider was called, and the digests prove delivery, not comprehension.
