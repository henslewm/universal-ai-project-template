# Git and Change Control

- Inspect branch and working-tree status before editing.
- Keep changes scoped and reviewable.
- Do not force-push, hard-reset, rewrite history, or delete evidence without explicit authority.
- Run the project validator before completing material changes.
- Never claim a commit or push succeeded without verifying it.
- Never merge a pull request until a Codex review exists whose `commit_id` matches the current head; a moved head needs re-review naming the new SHA, and every actionable finding (a concrete defect the change introduced/exposed, or an unmet explicit requirement) is answered first. Record an optional-improvement or pre-existing-condition finding separately instead of expanding the task to fix it.
- Never start or continue the next child issue while the current one has unanswered actionable review findings.
- Review findings are read from GitHub with `gh api`, never from email.
