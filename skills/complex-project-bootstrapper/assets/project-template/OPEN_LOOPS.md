# Open Loops

| ID | Priority | Open item | Owner | Next action | Dependency | Due | Status |
|---|---|---|---|---|---|---|---|
| OL-002 | High | Bootstrap acceptance | Maintainer | None; #2 closed and PR #15 merged at 500a7205 | Completion evidence in #2 and master comments | Complete | Closed |
| OL-003 | High | Work-packet contract acceptance | Maintainer | None; #3 closed and PR #16 merged at e8dce903 | Completion evidence in #3 and master comments | Complete | Closed |
| OL-004 | Medium | Complete detailed domain variants | Maintainer | Follow the later domain issues without expanding Issue #6 | Master #14 sequence and issues #9/#10/#11 | Not set | Deferred to owning issues |
| OL-005 | Medium | Preserve audit clarifications | Maintainer | Validate the six delivered issue forms in #6; demonstrate automatic first task-graph generation in #13 | Requirements audit and owning issues | Not set | Deferred; master unchanged |
| OL-006 | High | Model-router acceptance | Maintainer | None; #4 closed and PR #17 merged at e7c7c9c4 | Completion evidence in #4 and master comments | Complete | Closed |
| OL-007 | High | Bounded-feedback acceptance | Maintainer | None; #5 closed through merged PR #18 at 7b4f88f9 | Completion evidence in #5 and master comments | Complete | Closed |
| OL-008 | High | GitHub ledger acceptance | Maintainer | None; #6 closed through merged PR #19 at 5e0a28c6 | Completion evidence in #6 and master comments | Complete | Closed |
| OL-009 | High | Bounded execution harness acceptance | Maintainer | None; #7 closed through merged PR #20 at b326dca1 | Completion evidence in #7 and master comments | Complete | Closed |
| OL-010 | Medium | Live harness run is operator-executed | Maintainer | None; four operator runs recorded in #7 and in docs/ISSUE_7_VALIDATION.md, labelled non-reproducible in CI | Local model availability | Complete | Closed; live runs remain operator actions by design |
| OL-012 | High | Independent review and acceptance gates | Maintainer | None; #8 closed through merged PR #21 at 226353c6 | Completion evidence in #8 and master comments | Complete | Closed |
| OL-013 | Medium | Same-model-family review of the template's own children | Maintainer | Structural gate delivered in #8: high/critical-risk acceptance refuses same-family review without a recorded waiver. Cross-family review in practice remains unexercised for #7 and #8 themselves; prefer a cross-family reviewer for a future child when practical | Master #14 goal 9; reviewer availability | Not set | Machinery closed in #8; practice remains open |
| OL-011 | Medium | Local model tier calibration | Maintainer | Carry the run-4 profile into #12; a 27B partially offloaded to system RAM ran a trivial packet in 9 iterations at roughly 7.5 tokens per second | Issue #12 | Not set | Deferred to owning issue |
| OL-014 | High | Complete software + hardware domain template | Maintainer | Start #9 in a fresh session from master #14 and #9 only | Issue #9 | Not set | Next unblocked child; not started |
| OL-015 | Medium | Stray maintainer files from a concurrent Claude session | Winston | Decide whether to commit `prompts/PROVISION_LOCAL_MODEL.md` (untracked in root and payload; looks like #12 input) and whether to keep `_claude-outputs-preserved/plm-v2-main.md` and `Claude outputs/Optimize-LocalAIStorage.ps1`; `Claude outputs/` is now gitignored and payload-excluded | Maintainer decision | Not set | Open; documented in #8's dogfood comment |
