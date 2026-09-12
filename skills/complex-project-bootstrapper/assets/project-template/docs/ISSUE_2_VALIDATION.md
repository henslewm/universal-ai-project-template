# Issue #2 validation evidence

Verified locally on 2026-09-12 UTC with Python 3.12.8 on Windows. The initial clean checkout at `3be71e6` passed 9 tests but did not integrate the activation gate into normal generation. The final acceptance commit and remote results are recorded in [Issue #2](https://github.com/henslewm/universal-ai-project-template/issues/2) and [PR #15](https://github.com/henslewm/universal-ai-project-template/pull/15).

## Results

- `python -m unittest discover -s tests -v`: **32 tests passed** (24.572 seconds in the final local run).
- `python scripts/validate_project.py`: **passed**, 31 required paths.
- `python scripts/sync_skills.py --check`: **passed**, zero payload drift.
- `git diff --check`: **passed**.
- Independent read-only review identified a Windows Git line-ending portability defect and malformed intake coercion. Both were fixed and independently reproduced as passing regressions. No remaining findings in that final delta review. A subsequent failed-copy approval inheritance edge was reproduced, fixed by excluding approval files from template copies, and covered by a command-path regression. GitHub review then identified placeholder-prefixed values and an empty risk list; both readiness gaps were repaired with schema/runtime and CLI regressions.

## Acceptance coverage

| Requirement | Executed evidence |
|---|---|
| Three profile paths | Fresh interactive software/hardware, family-law and civil-rights intake, synthetic architect completion, review and activation; profile recovery from the existing canonical domain-document snapshots |
| Every supported distribution | Root script, repository-native skill and an isolated installed standalone skill, each across all three profiles |
| Generation cannot approve | Generated state remains INTAKE/inactive even if an answers file supplies ACTIVE/approved values; startup requires an explicit valid receipt; failed generation from an approved source cannot inherit its receipt |
| Explicit decision required | Activation rejected during intake, without input, with generic yes, and with a wrong fingerprint; matching synthetic identity/decision accepted |
| Readiness is mechanical | Blank/placeholder-prefixed/wrong-type fields, an empty risk assessment, missing orientation, unresolved blockers, unknown dependency nodes and cycles rejected |
| Approved foundation stays bound | Every fingerprint section, changed connector permissions and every bound governing document invalidate activation; an explicit review revokes previous approval |
| Existing work preserved | In-place rebootstrap of an active project fails without altering its records; uninitialized template in-place generation remains supported |
| Durable restart | Valid approval survives local Git commit and fresh clone, including forced CRLF-to-LF document normalization |
| Malformed inputs | Direct validator and actual CLI inputs fail without tracebacks; malformed answers are rejected before destination creation |

## Canonical files changed

Execution: `scripts/bootstrap_project.py`, `scripts/bootstrap_gate.py`, `scripts/validate_bootstrap.py`, `scripts/validate_project.py`, `scripts/sync_skills.py`.

Contract and examples: `config/bootstrap.schema.json`, `config/bootstrap.example.json`, `tests/fixtures/bootstrap-*.json`, `tests/fixtures/legal-project.json`, `templates/family-law/PROFILE.md`, `templates/civil-rights-nc/PROFILE.md` (snapshots of existing branch documents).

Tests/CI: `tests/test_bootstrap_gate.py`, `tests/test_bootstrap_integration.py`, `.github/workflows/validate-project.yml`.

Startup and operating documentation: `AGENTS.md`, `CLAUDE.md`, all five `MASTER_*.md` files, `.chatgpt/PROJECT_INSTRUCTIONS.md`, `.claude-web/PROJECT_INSTRUCTIONS.md`, `.github/copilot-instructions.md`, `prompts/START_SESSION.md`, both bootstrap prompts, `BOOTSTRAP_PROTOCOL.md`, `README.md`, `START_HERE.md`, canonical bootstrap skill and its intake/quality-gate references.

Durable records: `PROJECT_STATE.md`, `OPEN_LOOPS.md`, `DECISIONS.md`, `SOURCE_INDEX.md`, `RISK_REGISTER.md`, `HANDOFF_CURRENT.md`, `CHANGELOG.md`, and this report. Native skills and the standalone bundled template mirror the canonical files; the PR contains those synchronized copies too.

## Limitations and scope

The local gate enforces normal workflow and configuration integrity, not human authentication or a hostile-writer security boundary. Actors who can rewrite code or approval records remain outside that guarantee. Without a validator runtime, autonomous work remains blocked.

Tests activate only disposable synthetic projects. They do not configure paid providers, call paid model APIs, alter external permissions, activate a real project, verify physical hardware, or analyze a live legal matter. Domain fixtures establish the common extension contract; detailed domain questionnaires/schemas and rollout to the existing legal branches remain #9/#10/#11 under the owner-approved Issue #2 branch strategy. No later child issue was started, and master #14 was not modified.
