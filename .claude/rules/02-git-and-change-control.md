# Git and Change Control

- Inspect branch and working-tree status before editing.
- Keep changes scoped and reviewable.
- Do not force-push, hard-reset, rewrite history, or delete evidence without explicit authority.
- Run the project validator before completing material changes.
- Never claim a commit or push succeeded without verifying it. Push and ready-merge go through `scripts/closeout.py` (`MASTER_INSTRUCTIONS.md` → "Automatic closeout (ADR-094)").
- Merge and review discipline: apply `MASTER_INSTRUCTIONS.md` → "Review findings and merge discipline" exactly as stated (current-head review, every actionable finding answered, findings read from GitHub); it is deliberately not restated here.
