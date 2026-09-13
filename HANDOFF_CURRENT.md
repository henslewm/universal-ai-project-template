# Current Handoff

- **Prepared:** 2026-09-13 UTC
- **Repository:** `henslewm/universal-ai-project-template`
- **Branch:** issue-6-github-ledger
- **Scope:** Issue #6 only; master #14 is unchanged.

Start from repository instructions and live [master #14](https://github.com/henslewm/universal-ai-project-template/issues/14), then [Issue #6](https://github.com/henslewm/universal-ai-project-template/issues/6) and [PR #19](https://github.com/henslewm/universal-ai-project-template/pull/19). Issues #2 through #5 are closed; latest accepted merge is PR #18 at `7b4f88f982f32db97c9b7ad17b4c042c4503f8fe` with 157 passing GitHub tests. Completion and review evidence are linked in the issues.

Four automatic review rounds and one independent review have been answered in place. The independent review of `a74a980` found two P1 dead ends (a PR closed without merging, and a lost publication-claim write) plus two P2 and three P3 defects; all are corrected on this branch under ADR-008, with the reviewer's own test-design finding closed as well. `docs/ISSUE_6_VALIDATION.md` records each round and `GITHUB_LEDGER_PROTOCOL.md` states the resulting rules. The registry row gained `superseded_prs` and each publication entry gained `released`, so any registry written before this change must be re-read through the current validator.

Next action: confirm current-head GitHub CI and review, answer any remaining findings the same way, then merge PR #19, close #6 with evidence, and reread master #14 before #7. Continue through #13 one child at a time. Live GitHub records determine acceptance, not these documents.

Open limitation to carry forward: the independent review was performed by the same model family as the implementer and without live GitHub access, not by a different strong model as master #14 prefers. A Codex pass on the final head is still wanted, and the remote-semantics questions it could not settle — percent-encoding of refs, Contents-API SHA rejection, compare status values, PATCH idempotence — remain verified only against documentation and the synthetic fake.

Local tooling note: this checkout has no repository virtualenv; `jsonschema` is installed into a disposable interpreter outside the repository. A venv inside the working tree makes `scripts/validate_project.py` fail on vendored `.pem` files, so keep it outside.

The template remains unactivated. Connector tests use synthetic isolated GitHub fixtures and supplied feedback evidence, not live model execution or substantive independent acceptance. Preserve publication claims after uncertain writes and release one only on proven absence; recovery exports are not dispatch authority. Live harness enforcement remains #7 and acceptance machinery #8. No master edits, credentials, permission changes or branch deletion are part of #6.
