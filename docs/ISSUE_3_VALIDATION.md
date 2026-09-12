# Issue #3 validation and scope

Verified locally on 2026-09-12 UTC using Python 3.12.8 on Windows and an isolated environment with `requirements-work-packets.txt` installed. No paid provider, API credits, permission changes, or real-project activation were needed.

## Acceptance mapping

| Issue #3 criterion | Delivered evidence |
|---|---|
| One machine-readable schema works across all three domains | `config/work-packet.schema.json`, including all required common contract fields and an additive `domain` extension; complete synthetic examples for the three profiles. |
| GitHub representation generated from the same contract | `work_packet.py render` produces the entire current contract and revision/event provenance. Key order does not change output; embedded markup is escaped. No GitHub publication occurs. |
| Required fields validated automatically | The runtime consumes the schema directly and enforces tier ordering, criterion coverage/references, hashes, chronology, lifecycle roles and complete dependency graphs. |
| Contract changes versioned and traceable | Full consecutive snapshots bind task/profile/version/contract; supported revision commands retain prior records and reset to PROPOSED. Events are replayed against their original revision. |
| A bounded worker packet states exactly what completes the task | Every packet carries scope/prohibitions, named inputs/outputs/interface, acceptance/validation/evidence requirements, context, tier/effort, retry/review/escalation and architecture boundaries. The rendered view excludes old contract bodies. |

## Executed checks

```text
python -m unittest discover -s tests -p "test_*.py"
Ran 70 tests in 46.922s
OK

python scripts/validate_project.py
VALIDATION PASSED
Required paths checked: 38

python scripts/sync_skills.py --check
Bootstrap payloads verified; 0 files differed.

git diff --check
Passed
```

That initial complete run contained 38 packet tests plus the 32 existing bootstrap/repository tests. After GitHub review identified lossy scalar/list rendering in arbitrary domain extensions, the renderer was corrected to use fenced JSON and a round-trip type/key/nesting regression was added. The final local packet suite passed **39 tests in 7.124s**; repository validation, sync and diff checks passed again. Current full-suite remote results are recorded in PR #16 / Issue #3.

Packet checks cover all required fields; malformed values; domain extensions; reference coverage; tier bounds; invalid historical snapshots and events; state/role failures; implementation-actor self-acceptance; retained revision history; missing, duplicate, cyclic or stale dependency records; deterministic rendering; malformed JSON; and exclusive-output file preservation.

Existing bootstrap integration tests were extended to create, validate and render packets from generated projects using all three profiles through root, native-skill and standalone-skill entrypoints. This checks actual packaged delivery of the new tool/schema/examples while retaining the bootstrap approval tests.

## Independent review

An independent reviewer inspected contract/history/state/graph behavior and the documentation. Findings fixed and regression-tested:

- Integral-valued JSON numbers such as event revision `1.0` are valid schema integers and must not crash history indexing.
- Timestamp validation must run even without jsonschema's optional RFC3339 dependency; malformed calendar/time/offset values fail, while lowercase RFC3339 `t`/`z` is supported.
- Malformed graph members must fail through normal validation before target-record lookup.
- Identifiers must reject trailing newlines/control characters rather than relying only on the regex `$` anchor.
- Arbitrary domain-extension keys, JSON scalar types and nested arrays must survive the generated issue view; fenced JSON now preserves them, including embedded backtick sequences.

## Boundaries

This is a local contract and recorded-state foundation. It does not run workers, enforce actual retry execution, configure models, publish GitHub issues, authenticate actors, inspect referenced evidence, or prove real tests/review/merge. Actual execution still requires the bootstrap gate and the subsequent executor/review controls. Recorded VERIFIED prerequisites do not mechanically prove compatibility of changed dependency interfaces. Full domain-specific substantive validation remains #9/#10/#11.

Supported commands preserve snapshots/events and reject accidental inconsistent edits. They are not a tamper-resistant log against an actor who can rewrite and rehash all records. Scope strings are contracts, not filesystem access controls. A claimed different reviewer identity is not authentication.

The tool validates architect-supplied packet graphs; it does not infer the initial decomposition from free-text intake. The full automatic intake-to-first-task-graph-to-worker path remains the integrated demonstration for #13. Broader issue forms/GitHub automation remain #6. Detailed canonical legal-branch rollout remains the later domain workstreams, as with the common bootstrap foundation.

The live Issue #3 and linked PR carry the accepted commit, remote check/review results, merge and closure evidence. This local report is not itself a remote acceptance record.
