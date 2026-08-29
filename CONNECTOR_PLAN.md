# Connector Plan

> Template defaults. Bootstrap replaces this file with a project-specific plan.

| Connector / source | Default | Use when | Access boundary | Write policy |
|---|---|---|---|---|
| GitHub | Required | Reading and maintaining project state | This repository and explicitly named related repos | Project-file writes only when requested; no force push |
| Web search | Conditional | Current public facts, official documentation, law, prices, schedules | Public sources; prefer primary authority | None |
| Google Drive | Conditional | Authoritative documents or large source folders live in Drive | Explicit files/folders or search scope | Read by default |
| Gmail | Conditional | Email is evidence, instruction, or an open-loop source | Relevant senders, recipients, dates, and terms | Search/read by default; no send without explicit request |
| Google Calendar | Conditional | Deadlines, hearings, meetings, availability | Relevant calendars and date windows | Read/free-busy by default |
| Google Contacts | Conditional | Identity or recipient resolution is needed | Named people or organizations | Read only |
| Specialist database | Conditional | Controlling legal, scientific, technical, or financial authority is needed | Named database and task scope | Read only |

## Rules

- Do not connect a system merely because it is available.
- Use the narrowest useful scope.
- Record material sources in `SOURCE_INDEX.md`.
- Treat connector output as source material, not automatically as controlling truth.
- Consequential writes require explicit authority and verification.
