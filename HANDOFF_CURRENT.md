# Current Handoff

- **Prepared:** 2026-09-28 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** `copilot/fix-evidence-gap-issue`
- **Scope:** Quick closure for [issue #87](https://github.com/henslewm/universal-ai-project-template/issues/87) via PR #88.

## Outcome on this branch

- Hardened `.github/ISSUE_TEMPLATE/evidence-gap.yml` so the form now:
  - tells a reporter to stop and open/update a blocker instead if they cannot identify the canonical task, master issue, packet binding, and exact blocked criterion;
  - explicitly rejects placeholder text such as `Blocker`, `unknown`, or “I am not sure what the problem is”;
  - provides concrete placeholders for task/master links, packet binding, missing-evidence statements, provenance/search logs, verification requirements, and ownership.
- Added a narrow regression in `tests/test_validate_project.py` that asserts the new anti-placeholder guidance and sample packet/task fields remain present.
- Ran `python scripts/sync_skills.py`, which updated the payload mirror copies automatically.

## Verified state

- `python -m unittest discover -s tests -p 'test_validate_project.py'` ✅
- `python scripts/sync_skills.py --check` ✅
- `python scripts/validate_project.py` ✅
- Bootstrap gate remains intentionally inactive here: `python scripts/validate_bootstrap.py config/bootstrap.json --require-active` reports `BOOTSTRAP INVALID: no such file`, consistent with template-maintenance mode.

## Exact next action

1. Review PR #88's diff for the four intended changed files only:
   - `.github/ISSUE_TEMPLATE/evidence-gap.yml`
   - `tests/test_validate_project.py`
   - `skills/complex-project-bootstrapper/assets/project-template/.github/ISSUE_TEMPLATE/evidence-gap.yml`
   - `skills/complex-project-bootstrapper/assets/project-template/tests/test_validate_project.py`
2. Run automated PR review per ADR-074 on the current head.
3. Merge PR #88 if the review is clean or all actionable findings are answered.
4. Return to the quick-closure queue and then child #11 under master #14.

## Notes

- This fix is intentionally template-only. GitHub issue forms can require a field but do not offer a good way to validate provenance-rich freeform text; stronger guidance/examples at the form itself are the smallest effective control.
- Preserve the standing warning from ADR-062: before substantive multi-file work in a shared checkout, confirm no other unattended agent is writing to the same tree.
