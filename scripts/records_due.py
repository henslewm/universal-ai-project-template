#!/usr/bin/env python3
"""Stop / SessionEnd hook helper: say when the closeout records are behind the work.

Reads the hook's JSON on stdin. Default (Stop) mode prints one {"decision": "block", ...} object
when due; --session-end prints a one-line warning to stderr instead. It fails open: any error,
a missing git or a non-repository exits 0 silently, so it can never trap a session.
"""
from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import cli_exit

ROOT = Path(__file__).resolve().parent.parent
RECORDS = {"PROJECT_STATE.md", "OPEN_LOOPS.md", "DECISIONS.md", "SOURCE_INDEX.md",
           "RISK_REGISTER.md", "HANDOFF_CURRENT.md", "CHANGELOG.md"}
HANDOFF = "HANDOFF_CURRENT.md"


def git(root: Path, *args: str) -> str | None:
    """Stdout of a git call, or None when it fails."""
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def merge_base(root: Path) -> str | None:
    """The merge-base of HEAD with the default branch, or None when no base resolves."""
    candidates = []
    head = git(root, "rev-parse", "--abbrev-ref", "origin/HEAD")
    if head and head.strip():
        candidates.append(head.strip())
    candidates += ["origin/main", "main"]
    for base in candidates:
        mb = git(root, "merge-base", base, "HEAD")
        if mb and mb.strip():
            return mb.strip()
    return None


def changed_between(root: Path, start: str) -> set[str]:
    """Paths changed from `start` (a merge-base or commit) to HEAD."""
    out = git(root, "diff", "--name-only", "-z", f"{start}...HEAD")
    return {p for p in (out or "").split("\0") if p}


def committed_after_handoff(root: Path) -> set[str]:
    """Work paths committed after the last commit in HEAD's history that touched the handoff.

    The whole history, not only the branch, so work committed directly on the default branch,
    where the merge-base is HEAD itself, is still found (Codex round 2 on PR #118)."""
    last = (git(root, "log", "-1", "--format=%H", "HEAD", "--", HANDOFF) or "").strip()
    if not last:
        return set()
    return {p for p in changed_between(root, last) if p not in RECORDS}


def working_changes(root: Path) -> set[str]:
    """Tracked modifications and untracked, non-ignored files from `git status`."""
    out = git(root, "status", "--porcelain", "-z", "-uall")
    if out is None:
        raise RuntimeError("git status failed")
    paths: set[str] = set()
    entries = out.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.add(entry[3:])
        if entry[0] in "RC":  # -z lists the rename source as the next entry
            i += 1
    return paths


def evaluate(root: Path):
    """Return (branch, work_files) when the records are due, else None."""
    if git(root, "rev-parse", "--is-inside-work-tree") is None:
        return None
    working = working_changes(root)
    base = merge_base(root)
    changed = (changed_between(root, base) if base else set()) | working
    # A handoff edited in the working tree is newer than every commit; a committed one is behind
    # any work committed after it (Codex rounds 1 and 2 on PR #118).
    later = set() if HANDOFF in working else committed_after_handoff(root)
    work = sorted({p for p in changed if p not in RECORDS} | later)
    if not work:
        return None
    if HANDOFF in changed and not later:
        try:
            handoff_time = (root / HANDOFF).stat().st_mtime
        except OSError:
            handoff_time = 0.0
        newest = 0.0
        for rel in work:
            if rel in working:
                try:
                    newest = max(newest, (root / rel).stat().st_mtime)
                except OSError:
                    # A deleted file has no mtime. After a committed handoff the deletion is
                    # newer than it, so it is due; a handoff edited in the working tree may
                    # already account for it (Codex round 2 on PR #118).
                    if HANDOFF not in working:
                        newest = float("inf")
        if newest <= handoff_time:
            return None
    branch = (git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip() or "this branch"
    return branch, work


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-end", action="store_true", help="warn on stderr instead of blocking")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        try:
            data = json.loads(sys.stdin.read() or "{}")
        except (ValueError, OSError):
            data = {}
        if isinstance(data, dict) and data.get("stop_hook_active"):
            return 0
        root = args.root or Path(os.environ.get("CLAUDE_PROJECT_DIR") or ROOT)
        due = evaluate(root)
        if due is None:
            return 0
        branch, work = due
        if args.session_end:
            print(f"records are behind the work on {branch}; run /records next session", file=sys.stderr)
            return 0
        listed = ", ".join(work[:5]) + (f", and {len(work) - 5} more" if len(work) > 5 else "")
        reason = (f"The closeout records are behind the work on branch {branch}: {len(work)} changed "
                  f"file(s) since {HANDOFF} was last updated ({listed}). Run the /records skill "
                  f"(skills/records/SKILL.md) now, then finish. It edits local records only and never commits.")
        print(json.dumps({"decision": "block", "reason": reason}))
    except Exception:  # Fail open: a hook must never trap a session.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_exit.run(main))
