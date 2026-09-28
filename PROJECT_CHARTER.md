# Project Charter

## Project

- **Name:** Universal AI Project Template
- **Slug:** universal-ai-project-template
- **Domain:** (inferred) Multi-model AI project control plane, as a reusable template. Worked domains: legal work, and serial hardware and hardware/software interfaces.
- **Risk tier:** Not set
- **Sensitivity:** Not set. The repository is public.
- **Owner:** henslewm
- **Target date:** Not set

## Problem statement

All AI models hallucinate, drift and deviate from requests, goals, requirements and specs, so the controls must prevent that (endorsed "1000%"). (inferred) Having the strongest model do all the work costs too much, and one chat's memory does not carry across models or sessions.

## Desired outcome

A reusable, repo-backed control plane that makes complex, high-stakes AI-assisted work efficient: the owner is "spending money now to save money later." An architect model (Fable, Opus 5.5/6) must delegate intelligently to cheaper or local models under an explicit contract and monitor them effectively.

## Definition of done (inferred)

- Cheaper cloud or local models execute architect-written packets within settings-ledger limits, monitored through the ledger.
- The evidence ledger, the authorities corpus and court-ready export work end to end.
- Savings are demonstrated through telemetry (#12) and dry runs (#13).
- Every conflict under Pending decisions (A–D, F) is resolved by an ADR with owner sign-off, and E and G are built.

## Required deliverables

- **Continuity:** GitHub as durable memory for ChatGPT, Codex, Claude, Claude Code and Mistral.
- **Packets:** the strong model writes bounded, machine-checkable packets; cheaper cloud or local models execute them.
- **Ledgers** (CSV, SQL or a database; the owner has no preference). The owner wants everything in a single ledger (D, question 2); the split below is (inferred) and only groups what it must record:
  - *Settings:* rules, instructions, permissions and settings in about 3–5 plain lines, watched and changed on the fly, not dense markdown or JSON across many files. Holds the review cap and the worker-attempt default. Pending ADR (D).
  - *Runs:* every review round; this ledger enforces the review cap (owner). (inferred) Worker attempts are also recorded here. Pending ADR (A, B).
  - *Actions:* documents every create, modify and delete. Pending ADR (C).
  - *Evidence:* dates, cited statutes, a short description, parties, conduit of acquisition, SHA hash (SHA-256, as the repository uses), chain of custody, and so on. The owner already keeps Excel ledgers.
  - *Authorities* (inferred as a ledger): all evidence cited to current, citable authority (Rules of Professional Conduct, General Statutes, other laws). Initial bootstrap loads the local rules of civil and criminal procedure and the state and federal rules of evidence from a curated rules corpus the owner designates. Roadmap; not built (E).
- **Human interface:** clean, intuitive entry, summary, and export in court-ready formats with chain of custody. First exports (owner, 2026-09-28): exhibit index, chronology, citation table; the custody report follows. This charter asserts no formats.
- **Domain templates:** ESP32/PlatformIO is only one example of serial hardware and hardware/software human interfaces.

## Scope

### In scope

- (inferred) The template: control files, scripts, schemas, ledger designs, fictional examples and model entrypoints.
- Legal-work support (roadmap), to make representation accessible to people who can't afford a law degree.

### Out of scope

- Case data in this repository. The owner decided (2026-09-28) that ledger schemas, templates and scripts live here and case data lives in a separate private case repository or stays local.

## Constraints

- Preserve authoritative source material and provenance. Keep secrets and restricted material out of Git.
- Filing and sending require explicit owner approval. Until a superseding ADR on C is recorded with owner sign-off, the current rules' other explicit-authority gates, including those for deletions and consequential external writes, also apply.
- No real party or case identity in this public repository. In the private case repository, only public-record case documents (court filings) may be committed; before committing anything case-related, run the owner's privacy-redaction gate (the privacy-redaction-gate skill: PII, minors, sealed material, public uploads).
- Simulations or guesses are never acceptable as verification (owner, stated with the domain-template requirement).

## Decision rights

- The owner (henslewm) owns goals, scope, legal/business choices, and consequential external actions.
- AI tools may research, analyze, draft, organize, validate, and make reversible repository changes within granted permissions.
- Each conflict between an owner requirement and a current rule needs an ADR in `DECISIONS.md` and owner sign-off; until then the current rule applies.
- Unresolved conflicts, material adverse facts, and high-impact assumptions must be surfaced rather than hidden.

## Owner requirements (2026-09-28)

Stated directly by the owner. **Pending ADR** marks a target that conflicts with a current rule. It is not in force: the rule named under Pending decisions applies until a superseding ADR with owner sign-off is recorded.

- Review cap: an AI response or rival-AI review goes through at most 3–4 reviews, then is cut off and work moves forward. Adjustable in settings. Default decided: 4 per pull request. Pending ADR (A).
- Worker attempts: first a hard limit of 2 turns; the owner then said it "can be softer", so 2 is an adjustable default in the settings ledger. Pending ADR (B).
- Review rounds are tracked in a ledger, which also enforces the cap. Pending ADR (A, D).
- Filing and sending require explicit owner approval. In force; current rules already require it.
- Deleting, creating and modifying are not to need owner approval, but each must be recorded in a ledger documenting what happened. Decided: deleting or overwriting original evidence still needs explicit approval; git history rewrites, force pushes and remote deletes do not, but are ledgered. Pending ADR (C).
- Everything is tracked in a single ledger. Pending ADR (D).
- Savings must be demonstrable: telemetry (#12) and dry runs (#13). Open (G).

## Pending decisions

Owner target → current rule, which keeps applying → what is needed.

- **A. Review cap.** 4 per pull request by default, adjustable, ledger-enforced → ADR-063 rejects a numeric cap on review rounds; the only numeric cap, `max_review_attempts` (3 in `config/acceptance.example.json`), bounds the formal acceptance controller, not PR review (ADR-074) → an ADR superseding ADR-063's rejection and stating how a cut-off interacts with ADR-074 and the merge discipline (review on the current head; every actionable finding answered before merge).
- **B. Worker attempts.** Default 2, adjustable → `FEEDBACK_PROTOCOL.md`: 3/3/2/2/1 attempts at tiers T0–T4 (`config/feedback.example.json`), frozen at task initialization (ADR-006) → an ADR on the default and where it is set.
- **C. Approvals.** Only filing, sending and original-evidence deletion or overwrite gated; everything else ledgered → `MASTER_INSTRUCTIONS.md` (Work standard: no overwriting originals; explicit authority for deletions, force pushes, permission changes, purchases and consequential external writes; Connector selection: writes need an explicit request), `.claude/rules/04-permissions.md` (also publishing and modifying external records), `.claude/rules/02-git-and-change-control.md` (hard-reset, history rewrite, evidence deletion) and `AGENTS.md` → an ADR drawing that boundary, settling the gated actions the owner did not address (purchases, permission changes, publishing), and defining the action ledger.
- **D. Single ledger.** One ledger of record plus a 3–5 line settings ledger → state split across per-purpose control files (`PROJECT_STATE.md`, `OPEN_LOOPS.md`, `DECISIONS.md`, others) and the acceptance and feedback JSON ledgers; rules across many instruction and config files; permission changes need explicit authority (`MASTER_INSTRUCTIONS.md` Work standard, `MASTER_CLAUDE_CODE.md`), and `config/project.json` is fingerprint-bound at bootstrap → an ADR naming the canonical ledger (question 2) and what a settings-ledger edit may change without approval.
- **E. Rules at bootstrap (gap).** Load the procedure and evidence rules → not built; no authoritative source in the repository → the owner designates the corpus, then a design and an ADR.
- **F. Delegation.** The architect delegates to workers automatically (owner's handoff) → ADR-073: only an operator-run `launch` executes a reserved attempt, `dispatch` stays preparation-only, and no controller invokes `launch` → a superseding ADR (#36, #37, #40, #41).
- **G. Savings (gap).** Demonstrable → #12 and #13 open; `FEEDBACK_PROTOCOL.md` has no aggregate telemetry → finish #12 and #13.

Open question for the owner: 2. Which ledger is the canonical chronology? (Questions 1 and 3–5 were answered on 2026-09-28 and are recorded above.)
