# Current Handoff

- **Prepared:** 2026-10-06
- **Repository:** `henslewm/universal-ai-project-template`
- **Scope:** the template is frozen at the software and hardware tracks (ADR-089). Next work only on a new owner request.

## What was done

- On the owner's request, `.claude/settings.json` gained an `autoMode` block (ADR-091) mirroring the merge, sending, deletion, secrets and stay-in-repo gates. Branch `claude/auto-mode-rules`; PR open, merge awaits the owner's go-ahead after a head-matching Codex review.
- Previous pass (2026-10-04): status section on master issue #14 (ADR-090).

## Verified state

- `python scripts/validate_project.py` passes; `python scripts/sync_skills.py --check` clean (see the changelog entry for this pass).
- No project is activated from this template, so no re-approval is pending. `config/bootstrap.json` is absent, as expected for the unactivated template.

## Next action

Answer review findings on the auto-mode PR; do not merge without the owner. Otherwise none queued. Ask the owner before starting anything new. The skill payload is built by `scripts/sync_skills.py` and is not tracked, so distribute the skill as a release zip.

## Notes

- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
- `software_hardware.py` lazily imports `acceptance`, so the hardware track depends on acceptance, feedback, the router and the harness (OL-034).
- The master's immutability rule still applies to its original text; future status changes stay comments.
