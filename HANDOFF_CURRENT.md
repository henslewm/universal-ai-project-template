# Current Handoff

- **Prepared:** 2026-10-07
- **Repository:** `henslewm/universal-ai-project-template`
- **Scope:** the template is frozen at the software and hardware tracks (ADR-089). Next work only on a new owner request.

## What was done

- ADR-092: part 1 (PR #113) made the intake interactive by default, printed plain next steps and added `scripts/web_setup.py`. Part 2 (branch `claude/layperson-readme`) rewrote `README.md` and `START_HERE.md` for a layperson and moved the reference material to `docs/REFERENCE.md`.
- On the owner's request, `.claude/settings.json` gained `permissions.ask` rules (ADR-091) that prompt before merges, issue writes, deletions and `gh api` writes (Bash and PowerShell), plus PowerShell mirrors of the deny rules and broader force-push denies. The repository-scoped auto-mode rules went into the owner's `~/.claude/settings.json`, because the classifier ignores `autoMode` in project settings. Merged as PR #111 (`e76a20b`) after four Codex rounds. On the owner's explicit choice the final head `4158a3a` merged without a fifth review (recorded in ADR-091). Ask rules do not apply in `bypassPermissions` mode.
- Previous pass (2026-10-04): status section on master issue #14 (ADR-090).

## Verified state

- `python scripts/validate_project.py` passes and `python scripts/sync_skills.py --check` is clean after a sync (2026-10-07). The payload build is untracked and CI rebuilds it before tests (ADR-083).
- `claude auto-mode config` shows the user-scope rules in effect. The ask rules are not live-verified; they need a restart before a dry `gh pr merge` can confirm the prompt.
- No project is activated from this template, so no re-approval is pending. `config/bootstrap.json` is absent, as expected for the unactivated template.

## Next action

None queued. After a restart, the owner may confirm a dry `gh pr merge` prompts (cancel at the prompt). Ask the owner before starting anything new. The skill payload is built by `scripts/sync_skills.py` and is not tracked, so distribute the skill as a release zip.

## Notes

- Preserve ADR-062: confirm no other unattended agent is writing to the same tree before multi-file work.
- `software_hardware.py` lazily imports `acceptance`, so the hardware track depends on acceptance, feedback, the router and the harness (OL-034).
- The master's immutability rule still applies to its original text; future status changes stay comments.
