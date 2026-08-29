# Quality Gates

Before completion verify:

- Required control files and native entrypoints exist.
- Generated projects have no unresolved `{{PLACEHOLDER}}` tokens.
- JSON and TOML configuration parses.
- `CLAUDE.md` imports resolve.
- Canonical skill and native copies match.
- Connector scopes and write boundaries are explicit.
- Skill selections have a reason and status.
- Source index and handoff exist.
- Sensitive files and secrets are not tracked.
- Repository validator passes.
- Commit and push claims are verified with actual identifiers/status.
