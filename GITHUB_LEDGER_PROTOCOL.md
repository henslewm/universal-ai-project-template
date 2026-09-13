# GitHub task ledger

GitHub is the durable home of each managed task. The master issue supplies approved outcomes and order. A task issue is the human entry point; its canonical versioned packet and full feedback events live in `.autonomy/ledger.json` on a dedicated state branch. Issue comments are append-only projections linking exact state commits. Implementation branches and PRs remain bounded to one task. Accepted artifact/merge commits and linked verification establish accepted state. Project documents retain decisions, risks, sources and navigation, not duplicate attempt narration.

This implements Issue #6. It publishes supplied records and checks GitHub metadata. It does not invoke models, authenticate the truth of validation evidence, perform independent substantive review, merge PRs, create issues, or grant dispatch authority. Live execution and independent acceptance remain #7/#8. Existing explicitly authorized template maintenance continues through child issue/PR evidence; the reusable template itself is not activated or migrated into a synthetic operational registry.

## Setup and authority

1. Install `requirements-work-packets.txt` and authenticate the GitHub CLI through its normal credential store. The adapter targets `github.com`; enterprise hosts are not supported by this version. No token belongs in configuration, records, packet sources or comments.
2. Copy `config/github-ledger.example.json` to project-specific configuration. Choose the exact repository, separate state and accepted branches, existing master issue, and allowed publisher logins. Enable only within the project's authorized GitHub write scope. Publication preflights the authenticated login against the allowlist before claiming or posting any comment. Comment receipts must also have an allowed author.
3. Before bootstrap approval, record `GitHub ledger configuration SHA-256: <digest>` in `CONNECTOR_PLAN.md`. Obtain the digest using `model_router.digest(config)` over the parsed configuration, not the file bytes. The bound document and configuration must identify authorized GitHub project writes. Review and approve the resulting bootstrap package normally. Changing the configuration or bound document requires renewed approval; do not copy an old approval.
4. `init` creates the dedicated state branch from the accepted branch and its initial registry. It refuses an existing branch. A partially initialized branch after an uncertain write must be inspected and repaired under existing repository authority; do not delete it or reset counters to retry. If the registry exists, read it and continue instead of initializing again.

All connector mutations require current ACTIVE approval and the bound configuration digest. The initial approval anchor remains fixed in the registry. An architecture change stops this registry's writes until an explicitly reviewed continuity/migration procedure preserves its history; silently creating a second registry is forbidden. Read-only audit/recovery works without activation. Recording local feedback after revocation still works under the feedback protocol; keep those pending records for authorized later publication.

```text
python scripts/github_ledger.py --config config/github-ledger.json --root . init
python scripts/github_ledger.py --config config/github-ledger.json --root . put task-row.json
python scripts/github_ledger.py --config config/github-ledger.json --root . publish
python scripts/github_ledger.py --config config/github-ledger.json audit
```

`--config` and `--root` precede the subcommand. The CLI returns 0 for success, 2 for detected drift, and 1 for refusal/unavailable or incomplete evidence. A failed network operation is never evidence that a write did not happen.

## One task, one issue

Create or select an existing task issue under the approved master, then register a row with exactly these fields:

```json
{
  "issue": 23,
  "packet": {"description": "Replace with the complete validated work-packet object"},
  "feedback": [],
  "branch": "task-parser-01",
  "pr": null,
  "acceptance": null,
  "discoveries": {}
}
```

The illustration is not a valid executable packet. Use `work_packet.py` to create/validate the complete packet. Populate `feedback` with the original parsed event files in sequence; never paste a shortened rendering in place of events. Once feedback exists, use its derived packet until it reaches `REVIEW_PENDING`. Only validated reviewer/integrator event extensions may follow that exact packet history; pending dispatches and human holds cannot be overridden by another valid-looking packet. Existing task/issue, implementation branch and PR bindings cannot be replaced. Branches must use the supported ASCII subset of valid Git ref names, including valid path components. No configured or registered branch may be a path-component prefix of another, because Git cannot hold `refs/heads/a` and `refs/heads/a/b` at the same time. Full packet and feedback history prefixes must remain intact. Every registry read and write validates all registered packets as one complete acyclic dependency graph. The registry holds exactly one domain profile, and registration, publication and closure require it to match the approved project's profile. Register prerequisites first; READY and later dependent packets require VERIFIED prerequisites. A prerequisite cannot regress while its dependents remain in an advanced state. Accepted rows are immutable; follow-up work gets a new task.

Issue creation is deliberately separate from atomic registration: search existing issues before creating one and reconcile an uncertain creation response before retrying. The registry rejects duplicate task homes and duplicate implementation branches/PRs within the managed project. Unregistered legacy issues are not silently converted into tasks. Use the task form for intake; machine packet validation and architect readiness remain required. Hand-edited issue prose is not a second authoritative contract. Revisions use the packet tool, then publish a new committed projection.

The six forms are architected task, blocker, escalation, risk, evidence gap, and architecture-change request. Related forms identify the canonical task/master, evidence, impact, owner and next action. They record proposals and holds; an architecture-change form is not approval. GitHub's form requirements do not replace packet/domain validation, particularly in private repositories. See [GitHub issue form syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms).

Unrelated discoveries retain their raw feedback records. Map each `model_router.digest(discovery)` over the complete discovery entry from feedback `status` (including controller provenance fields) to a separately created issue number in `discoveries`. Every discovery must be mapped before acceptance makes the row immutable. Discovery targets cannot be the master or any canonical task home; registering a new task on an existing discovery home is also refused. Each discovery needs its own separate issue: two discovery mappings, in one row or across tasks, cannot share a home. Audit and closure flag unmapped discoveries. Do not broaden the current packet or create ad hoc passdown documents.

## Publication and interruption recovery

Each update commits the whole bounded registry through the [Contents API](https://docs.github.com/en/rest/repos/contents). The prior file SHA is required for replacement; a stale writer stops, reads the winning version, and deliberately reconstructs its change. It cannot trim histories or overwrite another task. The state branch is separate from accepted implementation and must never be merged as task output. Ledger-only pushes are excluded from the repository validation workflow to avoid redundant runs.

Each changed task creates a deterministic publication intent. The publisher first commits an exclusive claim using the same file-SHA comparison, then posts one comment. Its marker, author, exact body and pinned state-commit reference are verified across all comment pages. A successful receipt is then committed. A second publisher cannot claim the same operation.

```text
python scripts/github_ledger.py --config config/github-ledger.json --root . reconcile
```

If GitHub accepted the comment but its response was lost, reconciliation finds it and records the receipt without posting again. If a claimed operation has no visible comment, it stays uncertain and **is not automatically retried**. Wait for visibility and reconcile; if it remains absent, an operator must investigate with GitHub evidence before any explicit repair. Conflicting, edited, deleted, duplicated or untrusted receipts fail audit. The adapter never deletes/edits comments or silently releases claims. API failures, truncated pagination and size limits fail closed. These guarantees cover supported clients, not a repository administrator rewriting history or hostile credentials.

The registry is limited to 900,000 UTF-8 bytes so the Contents API can return complete embedded JSON. Raw evidence is never truncated to fit. Comments contain bounded evidence previews and digests; the exact committed registry contains the originals. Near capacity, stop and propose a reviewed storage migration retaining all history. This is a bounded initial storage format, not an unlimited event archive.

## Handoff, reconstruction and drift

Start a new session by reading repository instructions, the live master, the active canonical issue and its newest committed record. Fetch the registry at an exact state commit; recover into a new directory:

```text
python scripts/github_ledger.py --config config/github-ledger.json recover recovered-state
python scripts/github_ledger.py --config config/github-ledger.json recover historical-state --commit FULL_STATE_COMMIT_SHA
```

Recovery creates `registry.json` plus `task-<task-id-digest>/packet.json` and the original `feedback/00000001.json` sequence inside each task directory. Directory names use the full SHA-256 of the canonical JSON task ID to remain distinct across case-insensitive filesystems and Windows path rules; the packet and registry retain the readable task ID. It validates full packet histories and replays every feedback event before export. Existing destinations are refused. Pending reservations, cumulative budgets and holds survive; recovery authorizes no execution. An executor must check freshness against the current GitHub registry, current dependencies/permissions and bootstrap before taking any next action. An old pinned snapshot is historical evidence, not a fresh dispatch source.

`audit` checks live issues, registered PR bindings, accepted branch ancestry, receipt integrity, publication gaps and untracked discoveries. Optional `--packets path...` detects unregistered, duplicate or unpublished local packets. Optional `--workspace PATH --task-id ID` checks the GitHub origin (HTTPS or Git SSH), registered branch, existing commit, uncommitted/untracked files and whether HEAD matches the live published task branch. Missing origins or unpublished branches fail rather than certify a clean checkout. Unseen local work, arbitrary prose and unregistered legacy issues cannot be inferred from GitHub alone.

```text
python scripts/github_ledger.py --config config/github-ledger.json project-state project-state-new.json
python scripts/github_ledger.py --config config/github-ledger.json audit --project-state project-state-new.json
```

The generated JSON index records the exact state commit and task/issue/status/accepted-commit mapping. Link that generated index from `PROJECT_STATE.md` in an initialized project, and refresh it through normal repository work. `--project-state` detects stale snapshots and contradictory structured statuses. Do not maintain duplicate editable task status prose. The index command writes a new file; it does not automatically overwrite or commit project documents.

## Accepted state and closure

Publish a final row only after the canonical packet reaches `VERIFIED` through its independent reviewer/integrator history. Add `acceptance` with the exact 40-character accepted commit and nonempty `evidence` and `review` reference arrays. These references belong to the exact current packet revision/hash (bound in the publication), not an earlier result. If there is a PR, it must be merged from the registered repository/branch into the configured accepted branch and its merge commit must match. For a non-code task, commit the accepted artifact to the accepted branch and supply its verification/review references; no fictitious PR is required. In both cases the commit must be reachable from the accepted branch. Substantive truth and risk-proportionate review remain the acceptance controller's responsibility.

```text
python scripts/github_ledger.py --config config/github-ledger.json --root . put verified-task-row.json
python scripts/github_ledger.py --config config/github-ledger.json --root . publish
python scripts/github_ledger.py --config config/github-ledger.json --root . close TASK_ID
python scripts/github_ledger.py --config config/github-ledger.json audit
```

`close` requires the committed final row, a verified completion comment and all discovery homes. It is idempotent at the issue-state level; an uncertain PATCH is resolved by reading the issue, not by assuming closure. The PR template records the canonical issue/revision, bounded change, validation and review. Auto-closing GitHub PR keywords can briefly close an issue before final ledger publication; audit reports that mismatch until the verified final record is published. Return to the master and select the next unblocked issue only after closure evidence is complete.
