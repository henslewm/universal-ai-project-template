# Security and Permissions

## Repository visibility

Use a private repository for legal, personal, regulated, proprietary, or identifying information. A private repository is still a third-party system; apply the project's actual data-handling requirements.

## Never commit

- Passwords, API keys, tokens, cookies, private keys, seed phrases, or credentials.
- `.env` files containing secrets.
- Unredacted restricted personal data unless the repository is explicitly approved for it.
- Original evidence when a controlled source system is the safer canonical store.

## Evidence pattern

- Originals: controlled Drive/local/evidence system.
- Repository: source index, immutable hash, metadata, chronology, redacted copy, derived analysis, and links.
- Derived files must never overwrite originals.

## Agent permissions

- Read-only is the default.
- Repository writes are scoped to the active project.
- External sends, filings, publishing, purchases, deletions, permission changes, and force pushes require explicit current authorization.
- Review checked-in skills, MCP servers, hooks, and settings before trusting a repository.
