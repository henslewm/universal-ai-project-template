# Decision Log

Append material decisions. Do not rewrite prior decisions without recording supersession.

| ID | Date | Decision | Rationale | Alternatives considered | Consequences | Status |
|---|---|---|---|---|---|---|
| ADR-000 | 2026-08-29 | Use GitHub as the durable project state and native instruction files as platform adapters | Enables cross-model continuity and reviewable history | Chat-only memory; separate vendor projects | Requires disciplined closeout and commits | Accepted |
| ADR-001 | 2026-09-12 | Separate generation, foundation review and explicit activation; bind approval to configuration, governing documents, domain and workflow as well as architecture | Closes normal bootstrap and stale-approval bypass paths in Issue #2 | Treating generated files as activation; binding only architecture JSON | Re-review is required after bound changes; initialized-project rebootstrap is refused to preserve records | Accepted within Issue #2 |
| ADR-002 | 2026-09-12 | Hash governing Markdown as UTF-8 text with normalized LF line endings | Normal Git checkout/clone must preserve accepted authority across Windows and Linux | Raw-byte document hashes | Content changes invalidate approval while line-ending normalization alone does not | Accepted within Issue #2 |
