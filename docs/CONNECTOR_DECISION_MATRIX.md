# Connector Decision Matrix

| Need | Connector | Enable? | Default authority | Notes |
|---|---|---|---|---|
| Durable project files, commits, issues, history | GitHub | Usually yes | Read; scoped write when requested | Canonical project state |
| Large document collection or authoritative working files | Google Drive | When sources live there | Read | Track exact file/folder in source index |
| Communications as evidence or open loops | Gmail | When email matters | Search/read | Do not send without explicit request |
| Deadlines, hearings, meetings, availability | Google Calendar | When schedule matters | Read/free-busy | Writes require explicit scheduling instruction |
| Resolve a named person or recipient | Google Contacts | When identity is ambiguous | Read | Use narrow searches |
| Current public facts or changing rules | Web search | When current verification matters | Read | Prefer primary sources |
| Controlling case law or specialist authority | Legal/scientific/technical database | Domain-specific | Read | Record jurisdiction/version/date |
| Work tracking already lives elsewhere | Linear/Jira/Asana/etc. | Only if canonical | Read; scoped writes | Avoid parallel competing task systems |

## Selection test

Enable a connector only when at least one project deliverable depends on data that is more authoritative, current, or complete in that system than in the repository.

## Write test

A write is permitted only when all are true:

1. The current user request explicitly asks for the action or the project policy clearly delegates it.
2. The target, content, and consequence are known.
3. The action is reversible or the user accepted the irreversible consequence.
4. The result can be verified and recorded.
