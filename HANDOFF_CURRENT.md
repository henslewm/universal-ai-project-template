# Current Handoff

- **Prepared:** 2026-10-03
- **Repository:** `henslewm/universal-ai-project-template`
- **Scope:** the template is frozen at the software and hardware tracks (ADR-089). Next work only on a new owner request.

## What was decided

- Review cap of 4 automated-review rounds per PR (rule in `MASTER_INSTRUCTIONS.md`); worker-attempt default 2 recorded only; approvals unchanged; no combined ledger; no automatic delegation; savings telemetry (#12, #13) deferred. ADR-084 to ADR-088 are withdrawn.
- Legal work is archived in `archive/legal/` and not served. `worker_launcher` and `github_ledger` are removed (ADR-083). The generated-project charter wording is fixed (OL-031).

## Verified state

- `python scripts/validate_project.py` passes (81 required paths); `python scripts/sync_skills.py --check` clean.
- No project is activated from this template, so no re-approval is pending.

## Next action

None queued. Ask the owner before starting anything new. The skill payload is built by `scripts/sync_skills.py` and is not tracked, so distribute the skill as a release zip.

## Notes

- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
- `software_hardware.py` lazily imports `acceptance`, so the hardware track depends on acceptance, feedback, the router and the harness (OL-034).
