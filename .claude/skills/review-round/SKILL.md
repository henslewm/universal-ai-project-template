---
name: review-round
description: Run one automated-review round on the current branch's pull request. Request a Codex review of the exact head, read the findings from GitHub, fix or decline each one, reply, resolve the threads and push, within the ADR-089 cap of 4 rounds. Use when the user says "review round", "@codex review", "answer the findings" or "get this PR reviewed".
disable-model-invocation: true
---

# Review Round

One round of the review loop that `MASTER_INSTRUCTIONS.md` → "Review findings and merge discipline" governs. That section is the authority for what counts as actionable, the round cap and the merge gate; this skill only sequences it. Never merge from this skill.

## 1. Locate the pull request

- `gh pr view --json number,url,headRefOid,isDraft,state` for the current branch. No open PR: stop and say so.
- The working tree must be clean and local `HEAD` must equal `headRefOid`. If not, stop and report what is uncommitted or unpushed. Never commit or push work this skill did not make: it may belong to the user or another agent (ADR-062), and committing it needs the user's authority.

## 2. Count the rounds

- Read `gh api --paginate repos/{owner}/{repo}/pulls/<n>/reviews` and `gh api --paginate repos/{owner}/{repo}/issues/<n>/comments`.
- A review is a commit reviewed by `chatgpt-codex-connector[bot]` or `coderabbitai[bot]`: a review's `commit_id`, or a clean-round comment naming `**Reviewed commit:** \`<sha>\``.
- A request is a `@codex review` or `@coderabbitai review` comment. The cap counts requests: the rounds used are the distinct commits that were reviewed or requested.
- Head already reviewed: go to step 4. A request for the head is still unanswered: do not request again; go to the polling in step 3. Four rounds used and the head is unreviewed and unrequested: answer the findings already received, then stop and ask the maintainer how to proceed (ADR-089).

## 3. Request the review

- `gh pr comment <n> --body "@codex review <head sha>"`, naming round K of 4.
- Poll the two endpoints above no more than every 2 minutes, for up to 30 minutes. No review by then: stop, report the pending request and its SHA, and tell the user to run `/review-round` again later. The re-run resumes polling; it does not request again.

## 4. Read the findings

- Inline findings: `gh api --paginate repos/{owner}/{repo}/pulls/<n>/comments`, keeping those on the reviewed commit. Also read the review bodies and the clean-round comment.
- GitHub is the only source. Never read findings from email or chat.

## 5. Answer each finding

- Classify it with the actionability test in "Review findings and merge discipline". Do not reopen settled scope unless new code or evidence changes the classification; say what changed.
- Actionable: fix it with a regression test that fails before the fix, or give a reasoned decline. At most 2 fix attempts per finding (ADR-089 B); then stop and escalate with the evidence.
- Not actionable: a reasoned decline. If genuinely material, record it in `OPEN_LOOPS.md` rather than widening the change.
- Commit as `Answer Codex round K on PR #<n>: <one-line summary>`.

## 6. Verify

- `python scripts/validate_project.py`; `python -m unittest discover -s tests -p "test_*.py"`; in the template repository also `python scripts/sync_skills.py --check`. All pass before anything is pushed.

## 7. Push, reply, resolve

- Push the branch (never force) and confirm `origin` has the new head, so every reply can cite a commit that is already on GitHub. Pushing the fix commits this skill made is part of the round the user started.
- Reply on each thread with the fix commit or the decline reason: `gh api repos/{owner}/{repo}/pulls/<n>/comments/<id>/replies -f body=...`.
- Resolve each answered thread with the GraphQL `resolveReviewThread` mutation.

## 8. Report

Round K of 4; each finding fixed (commit) or declined (reason); the new head SHA; validation results; and the next step: run `/review-round` again for the new head, or the PR awaits the merge gate.
