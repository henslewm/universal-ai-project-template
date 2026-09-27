# Automatic worker startup validation

Date: 2026-09-18. Branch: `codex/automatic-worker-startup`, based on `main` at `3eeba90`.
Authority: the user's explicit request to make instruction loading automatic in this architecture.
This is separate from the Issue #10 family-law work packet and its independent review.

## Behavior

Every prepared worker dispatch carries version 1.1 startup governance in the brief, with complete
UTF-8 instruction text, source paths and SHA-256 digests. Missing, empty, unreadable, unsafe,
credential-like or oversized required sources fail before an attempt is reserved. The existing
serialized-brief and model-capacity checks also apply. Supplemental instruction paths are explicit;
the loader does not infer path applicability from prose scope or expand the task's edit permissions.

The existing contract, architect guidance, failure history and review rejections are retained.
Report fields and acceptance controllers are unchanged, and exact legacy 1.0 briefs remain
verifiable. Restricted reviewer packets receive no worker startup bundle. The standing instructions
also define manual-worker startup and distinguish the dispatcher-owned bootstrap preflight from
contract-owned worker validation.

## Local validation

- Focused execution-harness suite: 35 tests passed.
- Repository validation: 81 required paths passed.
- Real template governance fits the updated example's 100,000-character brief limit, with room for
  a contract; the smaller model context-window limit can still refuse dispatch.
- Full unittest discovery: 372 tests passed in 193.874 seconds. Existing acceptance-process tests
  emitted ResourceWarnings for unclosed test pipes; there were no failures or errors.
- Distribution synchronization is checked on a metadata-free export of this worktree. The existing
  sync script treats a worktree's `.git` pointer as an ordinary file; its transient copied pointer
  is removed from the payload, and Git metadata is excluded from the export. This avoids changing
  the unrelated packaging mechanism or shipping local worktree metadata.
  The standard `scripts/sync_skills.py --check` on that export passed: **0 files differed**.

Regressions cover full-text delivery to a replacement harness receiving only the brief, ordering
and content digests, absence/unreadability, UTF-8 and credential refusal, cumulative size limits,
case-sensitive path identities, traversal and Win32 aliases, reparse points, malformed/tampered
startup snapshots, exact legacy/new brief shapes, contract preservation and existing capacity gates.
These are synthetic local runs; no provider was called and no model comprehension is authenticated.

The template remains intentionally unactivated: bootstrap validation reports missing
`config/bootstrap.json`. Work was explicitly authorized template maintenance. The documented old
Python environment was unavailable; Python 3.12.14 and the pinned `jsonschema==4.26.0` were installed
outside the repository worktree. No repository virtualenv was added.

## Integration boundary

No commit, push, PR, merge or external publication has occurred. The Issue #10 working tree remains
unchanged. Integrate this branch only through the repository's normal review and merge policy.
Instruction integrity checks do not authenticate authors or prove that a model understood the text.
