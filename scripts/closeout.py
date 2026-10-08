#!/usr/bin/env python3
"""Automatic closeout (ADR-094): push, machine-checked merge readiness, and issue/open-loop mirroring.

`push` pushes the current branch (never forced, never to a protected branch). `ready` decides
whether the branch's pull request may merge: validator and tests green, an automated review on
the exact head (ADR-074), every review thread resolved, and the ADR-089 cap of 4 rounds. `merge`
merges only when `ready` passes, then deletes the branch locally and remotely, returns to the
base branch, pulls and verifies a clean tree. `issue` opens a GitHub issue mirroring an
`OPEN_LOOPS.md` row; `sync-loops` keeps the pair's open/closed state in step. OPEN_LOOPS.md is
the record of truth; the issue is its tracker mirror.

Merging with open or stale review findings is deliberately not granted: `merge` refuses it.
"""

from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import cli_exit

ROOT = Path(__file__).resolve().parent.parent
REVIEW_BOTS = ("chatgpt-codex-connector[bot]", "coderabbitai[bot]")
REVIEW_CAP = 4  # automated-review rounds per pull request (ADR-089)
PROTECTED = {"main", "master"}
REVIEWED = re.compile(r"\*\*Reviewed commit:\*\*\s*`([0-9a-f]{7,40})`")
# A Codex round with no findings posts no review: it only marks its summary comment's row Completed
# for the commit it reviewed (the comment is edited in place, so it names the latest round only).
SUMMARY_COMPLETED = re.compile(r"\*\*Completed\*\*[^|\n]*\|\s*`([0-9a-f]{7,40})`")
ISSUE_LINK = re.compile(r"\[#(\d+)\]\((https://github\.com/[^)\s]+/issues/(\d+))\)")
THREADS_QUERY = """query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) {
    reviewThreads(first: 100) { nodes { isResolved path comments(first: 1) { nodes { author { login } } } } }
  } }
}"""


class Refused(Exception):
    """A handled refusal: exit 1 with the reason."""


def run(cmd: list[str], check: bool = True) -> str:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if check and result.returncode != 0:
        raise Refused(f"`{' '.join(cmd[:3])}` failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def gh_json(args: list[str]):
    return json.loads(run(["gh", *args]) or "null")


# --- readiness (pure) -------------------------------------------------------------------------

def review_signals(reviews: list[dict], comments: list[dict]) -> list[str]:
    """Commit SHAs (full or abbreviated) an automated reviewer reviewed, oldest first. A review
    carries its commit_id; a clean Codex round is an issue comment naming the reviewed commit."""
    signals = [(r.get("submitted_at") or "", r["commit_id"]) for r in reviews
               if r.get("user", {}).get("login") in REVIEW_BOTS and r.get("commit_id")]
    for c in comments:
        if c.get("user", {}).get("login") not in REVIEW_BOTS:
            continue
        body = c.get("body") or ""
        if match := REVIEWED.search(body):
            signals.append((c.get("created_at") or "", match.group(1)))
        for match in SUMMARY_COMPLETED.finditer(body):
            signals.append((c.get("updated_at") or c.get("created_at") or "", match.group(1)))
    return [sha for _, sha in sorted(signals)]


def assess(head: str, signals: list[str], unresolved: int) -> list[str]:
    """Reasons the head is not ready to merge; an empty list means ready."""
    reasons = []
    rounds = len({sha[:7] for sha in signals})
    if not any(head.startswith(sha) or sha.startswith(head) for sha in signals):
        if rounds >= REVIEW_CAP:
            reasons.append(f"review cap reached ({rounds} rounds, ADR-089): answer the findings received and ask the owner how to proceed")
        else:
            reasons.append(f"no automated review on head {head[:7]} (stale or missing, ADR-074): comment `@codex review` "
                           f"naming {head[:7]} (round {rounds + 1} of {REVIEW_CAP})")
    if unresolved:
        reasons.append(f"{unresolved} unresolved review thread(s): answer each actionable finding (fix with a regression, "
                       "or a reasoned decline) and resolve the thread")
    return reasons


# --- OPEN_LOOPS mirroring (pure) --------------------------------------------------------------

def _row_index(lines: list[str], loop_id: str) -> int:
    for i, line in enumerate(lines):
        if line.startswith(f"| {loop_id} |"):
            return i
    raise Refused(f"OPEN_LOOPS.md has no row {loop_id}")


def link_issue(text: str, loop_id: str, number: int, url: str) -> str:
    """Append the issue link to the row's 'Open item' cell."""
    lines = text.split("\n")
    i = _row_index(lines, loop_id)
    if ISSUE_LINK.search(lines[i]):
        raise Refused(f"{loop_id} already mirrors an issue")
    cells = lines[i].strip().strip("|").split("|")
    cells[2] = f"{cells[2].rstrip()} [#{number}]({url}) "
    lines[i] = "|" + "|".join(cells) + "|"
    return "\n".join(lines)


def close_loop(text: str, loop_id: str, status: str) -> str:
    """Move an open row to the end of the '## Closed' table with the given status."""
    lines = text.split("\n")
    i = _row_index(lines, loop_id)
    cells = lines.pop(i).strip().strip("|").split("|")
    cells[-1] = f" {status} "
    row = "|" + "|".join(cells) + "|"
    start = lines.index("## Closed")
    last = end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        if lines[end].startswith("|"):
            last = end
        end += 1
    lines.insert(last + 1, row)
    return "\n".join(lines)


def mirrored_rows(text: str) -> list[tuple[str, str, int]]:
    """(loop id, 'Open' or 'Closed', issue number) for every row that links an issue."""
    out, section = [], ""
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("| OL-") and (match := ISSUE_LINK.search(line)):
            out.append((line.split("|")[1].strip(), section, int(match.group(1))))
    return out


# --- commands ---------------------------------------------------------------------------------

def current_branch() -> str:
    branch = run(["git", "branch", "--show-current"])
    if not branch:
        raise Refused("detached HEAD; switch to a branch first")
    return branch


def require_clean() -> None:
    if run(["git", "status", "--porcelain"]):
        raise Refused("working tree is not clean; commit the coherent unit first")


def cmd_push(args) -> int:
    branch = current_branch()
    if branch in PROTECTED:
        raise Refused(f"'{branch}' is protected; push a feature branch and merge it through `closeout.py merge`")
    require_clean()
    run(["git", "push", "-u", "origin", branch])
    head = run(["git", "rev-parse", "HEAD"])
    remote = run(["git", "ls-remote", "origin", f"refs/heads/{branch}"]).split("\t")[0]
    if remote != head:
        raise Refused(f"push not verified: origin/{branch} is {remote[:7] or 'missing'}, local is {head[:7]}")
    print(f"PUSHED: {branch} at {head[:7]} (verified on origin)")
    return 0


def readiness(pr: str | None) -> tuple[dict, list[str]]:
    view = gh_json(["pr", "view", *([pr] if pr else []), "--json", "number,headRefName,headRefOid,state,isDraft,baseRefName,url"])
    reasons = []
    if view["state"] != "OPEN":
        raise Refused(f"PR #{view['number']} is {view['state'].lower()}")
    if view["isDraft"]:
        reasons.append("the pull request is a draft")
    if run(["git", "status", "--porcelain"]):
        reasons.append("working tree is not clean")
    if run(["git", "rev-parse", "HEAD"]) != view["headRefOid"]:
        reasons.append("local HEAD differs from the pull request head; push or pull first")
    if subprocess.run([sys.executable, "scripts/validate_project.py"], cwd=ROOT, capture_output=True).returncode:
        reasons.append("validate_project.py fails")
    if (ROOT / "tests").is_dir() and subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=ROOT, capture_output=True).returncode:
        reasons.append("the unit test suite fails")
    number = view["number"]
    reviews = gh_json(["api", "--paginate", "--slurp", f"repos/{{owner}}/{{repo}}/pulls/{number}/reviews"])
    comments = gh_json(["api", "--paginate", "--slurp", f"repos/{{owner}}/{{repo}}/issues/{number}/comments"])
    repo = gh_json(["repo", "view", "--json", "owner,name"])
    threads = gh_json(["api", "graphql", "-f", f"query={THREADS_QUERY}", "-F", f"owner={repo['owner']['login']}",
                       "-F", f"name={repo['name']}", "-F", f"number={number}"])
    nodes = threads["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    unresolved = sum(1 for node in nodes if not node["isResolved"])
    signals = review_signals([r for page in reviews for r in page], [c for page in comments for c in page])
    return view, reasons + assess(view["headRefOid"], signals, unresolved)


def cmd_ready(args) -> int:
    view, reasons = readiness(args.pr)
    if reasons:
        print(f"NOT READY: PR #{view['number']} at {view['headRefOid'][:7]}")
        for reason in reasons:
            print(f"- {reason}")
        return 2
    print(f"READY: PR #{view['number']} at {view['headRefOid'][:7]}")
    return 0


def cmd_merge(args) -> int:
    view, reasons = readiness(args.pr)
    if reasons:
        print(f"NOT MERGED: PR #{view['number']} is not ready")
        for reason in reasons:
            print(f"- {reason}")
        return 2
    number, branch, base = str(view["number"]), view["headRefName"], view["baseRefName"]
    run(["gh", "pr", "merge", number, "--merge", "--delete-branch", "--match-head-commit", view["headRefOid"]])
    if current_branch() != base:
        run(["git", "switch", base])
    run(["git", "pull", "--ff-only"])
    if run(["git", "branch", "--list", branch]):
        run(["git", "branch", "-D", branch])
    if run(["git", "ls-remote", "--heads", "origin", branch]):
        run(["git", "push", "origin", "--delete", branch])
    if run(["git", "status", "--porcelain"]):
        raise Refused(f"merged, but the working tree on {base} is not clean")
    merged = gh_json(["pr", "view", number, "--json", "mergeCommit"])["mergeCommit"]["oid"]
    if subprocess.run(["git", "merge-base", "--is-ancestor", merged, "HEAD"], cwd=ROOT, capture_output=True).returncode:
        raise Refused(f"merged as {merged[:7]}, but local {base} does not contain it")
    print(f"MERGED: PR #{number} as {merged[:7]}; {branch} deleted locally and on origin; {base} clean")
    return 0


def cmd_issue(args) -> int:
    loops = ROOT / "OPEN_LOOPS.md"
    text = loops.read_text(encoding="utf-8")
    link_issue(text, args.loop, 0, "https://github.com/x/y/issues/0")  # refuse before creating anything
    body = (Path(args.body_file).read_text(encoding="utf-8") if args.body_file else args.body or "").strip()
    body += f"\n\n---\nMirrors `OPEN_LOOPS.md` {args.loop}, the record of truth. Closing either closes the other (ADR-094)."
    url = run(["gh", "issue", "create", "--title", f"[{args.kind}] {args.title}", "--body", body]).splitlines()[-1]
    number = int(url.rstrip("/").rsplit("/", 1)[-1])
    loops.write_text(link_issue(text, args.loop, number, url), encoding="utf-8")
    print(f"ISSUE: #{number} mirrors {args.loop} ({url}); commit OPEN_LOOPS.md with the work")
    return 0


def cmd_sync_loops(args) -> int:
    loops = ROOT / "OPEN_LOOPS.md"
    text = loops.read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()
    changed = False
    for loop_id, section, number in mirrored_rows(text):
        state = gh_json(["issue", "view", str(number), "--json", "state"])["state"]
        if section == "Open" and state == "CLOSED":
            text, changed = close_loop(text, loop_id, f"Closed {today}: issue #{number} closed"), True
            print(f"CLOSED LOOP: {loop_id} (issue #{number} was closed)")
        elif section == "Closed" and state == "OPEN":
            run(["gh", "issue", "close", str(number), "--comment", f"Closed with `OPEN_LOOPS.md` {loop_id} (ADR-094)."])
            print(f"CLOSED ISSUE: #{number} ({loop_id} is closed)")
    if changed:
        loops.write_text(text, encoding="utf-8")
    print("SYNCED: OPEN_LOOPS.md and its issues agree")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("push", help="push the current branch (never forced, never a protected branch)")
    for name in ("ready", "merge"):
        sub = commands.add_parser(name, help=f"{name} the current branch's pull request")
        sub.add_argument("--pr", help="pull request number (default: the current branch's)")
    issue = commands.add_parser("issue", help="open a GitHub issue mirroring an OPEN_LOOPS.md row")
    issue.add_argument("--loop", required=True, help="the OPEN_LOOPS.md row, such as OL-037")
    issue.add_argument("--kind", required=True, choices=["bug", "feature"])
    issue.add_argument("--title", required=True)
    issue.add_argument("--body", help="report, evidence and acceptance shape")
    issue.add_argument("--body-file")
    commands.add_parser("sync-loops", help="close the issue of a closed loop, and the loop of a closed issue")
    args = parser.parse_args()
    handler = {"push": cmd_push, "ready": cmd_ready, "merge": cmd_merge, "issue": cmd_issue, "sync-loops": cmd_sync_loops}
    try:
        return handler[args.command](args)
    except Refused as exc:
        print(f"Closeout refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(cli_exit.run(main))
