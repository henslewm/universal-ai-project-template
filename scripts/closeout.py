#!/usr/bin/env python3
"""Automatic closeout (ADR-094): push, machine-checked merge readiness, and issue/open-loop mirroring.

`push` pushes the current branch (never forced, never to a protected branch). `ready` decides
whether the branch's pull request may merge: validator and tests green, an automated review on
the exact head (ADR-074), every review thread resolved, and the ADR-089 cap of 4 rounds. `merge`
merges only when `ready` passes, then deletes the branch locally and remotely, returns to the
base branch, pulls and verifies a clean tree; rerun after a queued merge lands, it only cleans
up. `issue` opens a GitHub issue mirroring an
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
ISSUE_URL = re.compile(r"https://github\.com/\S+/issues/(\d+)")
COMMAND_TIMEOUT = 300  # seconds; a credential prompt or network stall becomes a refusal, not a hang
TEST_TIMEOUT = 1800
ISSUE_LINK = re.compile(r"\[#(\d+)\]\((https://github\.com/[^)\s]+/issues/(\d+))\)")
THREADS_QUERY = """query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) {
    reviewThreads(first: 100) { pageInfo { hasNextPage } nodes { isResolved path comments(first: 1) { nodes { author { login } } } } }
  } }
}"""


class Refused(Exception):
    """A handled refusal: exit 1 with the reason."""


def run(cmd: list[str], check: bool = True, timeout: int = COMMAND_TIMEOUT) -> str:
    try:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Refused(f"`{' '.join(cmd[:3])}` did not finish within {timeout} seconds")
    if check and result.returncode != 0:
        raise Refused(f"`{' '.join(cmd[:3])}` failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def passes(cmd: list[str], timeout: int) -> bool:
    try:
        return subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def gh_json(args: list[str]):
    return json.loads(run(["gh", *args]) or "null")


# --- readiness (pure) -------------------------------------------------------------------------

def is_round(review: dict) -> bool:
    """A bot review that is a review round. A reply in a review thread is filed as a COMMENTED review
    with an empty body on the then head: it is neither a round nor a review of that head."""
    return (review.get("user", {}).get("login") in REVIEW_BOTS and bool(review.get("commit_id"))
            and (bool((review.get("body") or "").strip()) or review.get("state") != "COMMENTED"))


def review_rounds(reviews: list[dict], comments: list[dict]) -> int:
    """Automated review rounds: each bot review round, and each bot comment naming a reviewed commit
    (a clean Codex round). Repeat rounds on one commit count separately; the edited-in-place summary
    comment never counts, because it only restates the latest round."""
    return (sum(1 for r in reviews if is_round(r))
            + sum(1 for c in comments if c.get("user", {}).get("login") in REVIEW_BOTS
                  and REVIEWED.search(c.get("body") or "")))


def changes_requested(reviews: list[dict], head: str) -> bool:
    """True when a bot review of the head asks for changes: a body-only finding has no thread to resolve."""
    return any(r.get("user", {}).get("login") in REVIEW_BOTS and r.get("state") == "CHANGES_REQUESTED"
               and head.startswith(r.get("commit_id") or "-") for r in reviews)


def review_signals(reviews: list[dict], comments: list[dict]) -> list[str]:
    """Commit SHAs (full or abbreviated) an automated reviewer reviewed, oldest first. A review
    carries its commit_id; a clean Codex round is an issue comment naming the reviewed commit."""
    signals = [(r.get("submitted_at") or "", r["commit_id"]) for r in reviews if is_round(r)]
    for c in comments:
        if c.get("user", {}).get("login") not in REVIEW_BOTS:
            continue
        body = c.get("body") or ""
        if match := REVIEWED.search(body):
            signals.append((c.get("created_at") or "", match.group(1)))
        for match in SUMMARY_COMPLETED.finditer(body):
            signals.append((c.get("updated_at") or c.get("created_at") or "", match.group(1)))
    return [sha for _, sha in sorted(signals)]


def assess(head: str, signals: list[str], unresolved: int, rounds: int | None = None,
           more_threads: bool = False, changes: bool = False) -> list[str]:
    """Reasons the head is not ready to merge; an empty list means ready."""
    reasons = []
    rounds = len({sha[:7] for sha in signals}) if rounds is None else rounds
    if rounds > REVIEW_CAP:
        # ADR-089: past the cap the maintainer decides, even when the latest round covers the head.
        reasons.append(f"review cap exceeded ({rounds} rounds, ADR-089): the maintainer decides how to proceed")
    elif not any(head.startswith(sha) or sha.startswith(head) for sha in signals):
        if rounds >= REVIEW_CAP:
            reasons.append(f"review cap reached ({rounds} rounds, ADR-089): answer the findings received and ask the owner how to proceed")
        else:
            reasons.append(f"no automated review on head {head[:7]} (stale or missing, ADR-074): comment `@codex review` "
                           f"naming {head[:7]} (round {rounds + 1} of {REVIEW_CAP})")
    if unresolved:
        reasons.append(f"{unresolved} unresolved review thread(s): answer each actionable finding (fix with a regression, "
                       "or a reasoned decline) and resolve the thread")
    if more_threads:
        reasons.append("more than 100 review threads: not every thread could be checked")
    if changes:
        reasons.append("an automated review of the head requests changes: answer its findings")
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
    if "## Closed" not in lines:
        # Generated projects start with only an Open table.
        lines += ["", "## Closed", "", "| ID | Priority | Open item | Owner | Next action | Dependency | Due | Status |",
                  "|---|---|---|---|---|---|---|---|"]
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


def pr_view(pr: str | None) -> dict:
    return gh_json(["pr", "view", *([pr] if pr else []), "--json",
                    "number,headRefName,headRefOid,state,isDraft,baseRefName,url,isCrossRepository,mergeCommit"])


def readiness(pr: str | None, view: dict | None = None) -> tuple[dict, list[str]]:
    view = view or pr_view(pr)
    reasons = []
    if view["state"] != "OPEN":
        raise Refused(f"PR #{view['number']} is {view['state'].lower()}")
    if view["isDraft"]:
        reasons.append("the pull request is a draft")
    if view.get("isCrossRepository"):
        reasons.append("cross-repository pull request: its branch is not this repository's to delete; merge it by hand")
    if run(["git", "status", "--porcelain"]):
        reasons.append("working tree is not clean")
    if run(["git", "rev-parse", "HEAD"]) != view["headRefOid"]:
        reasons.append("local HEAD differs from the pull request head; push or pull first")
    if not passes([sys.executable, "scripts/validate_project.py"], COMMAND_TIMEOUT):
        reasons.append("validate_project.py fails")
    if (ROOT / "tests").is_dir() and not passes(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], TEST_TIMEOUT):
        reasons.append("the unit test suite fails")
    number = view["number"]
    reviews = gh_json(["api", "--paginate", "--slurp", f"repos/{{owner}}/{{repo}}/pulls/{number}/reviews"])
    comments = gh_json(["api", "--paginate", "--slurp", f"repos/{{owner}}/{{repo}}/issues/{number}/comments"])
    repo = gh_json(["repo", "view", "--json", "owner,name"])
    threads = gh_json(["api", "graphql", "-f", f"query={THREADS_QUERY}", "-F", f"owner={repo['owner']['login']}",
                       "-F", f"name={repo['name']}", "-F", f"number={number}"])
    page = threads["data"]["repository"]["pullRequest"]["reviewThreads"]
    unresolved = sum(1 for node in page["nodes"] if not node["isResolved"])
    reviews = [r for p in reviews for r in p]
    comments = [c for p in comments for c in p]
    head = view["headRefOid"]
    return view, reasons + assess(head, review_signals(reviews, comments), unresolved,
                                  rounds=review_rounds(reviews, comments),
                                  more_threads=page["pageInfo"]["hasNextPage"],
                                  changes=changes_requested(reviews, head))


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
    view = pr_view(args.pr)
    if merged := merged_commit(view):
        # The rerun a queued merge asks for: GitHub has merged it, so only the cleanup is left.
        return clean_up(view, merged)
    view, reasons = readiness(args.pr, view)
    if reasons:
        print(f"NOT MERGED: PR #{view['number']} is not ready")
        for reason in reasons:
            print(f"- {reason}")
        return 2
    number, branch = str(view["number"]), view["headRefName"]
    # No --delete-branch: with a merge queue or pending required checks, `gh pr merge` can succeed by
    # queuing the pull request, and deleting its branch then would close it unmerged.
    run(["gh", "pr", "merge", number, "--merge", "--match-head-commit", view["headRefOid"]])
    merged = merged_commit(gh_json(["pr", "view", number, "--json", "state,mergeCommit"]))
    if not merged:
        print(f"QUEUED: PR #{number} is accepted for merge but not merged yet; {branch} is kept. "
              "Run `closeout.py merge` again after it merges to clean up.")
        return 0
    return clean_up(view, merged)


def clean_up(view: dict, merged: str) -> int:
    """Delete a merged pull request's branch locally and on origin, return to the base branch, pull
    and verify a clean tree. A protected branch is never deleted; a branch that is not at the merged
    head holds other work and is kept."""
    number, branch, base, head = view["number"], view["headRefName"], view["baseRefName"], view["headRefOid"]
    if branch in PROTECTED:
        raise Refused(f"PR #{number} merged; its head {branch} is protected and is never deleted")
    if view.get("isCrossRepository"):
        raise Refused(f"PR #{number} came from another repository: its branch is not this repository's to delete")
    require_clean()
    local = run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)
    remote = run(["git", "ls-remote", "origin", f"refs/heads/{branch}"]).split("\t")[0]
    for where, tip in (("local", local), ("origin", remote)):
        if tip and tip != head:
            raise Refused(f"PR #{number} merged; {where} {branch} is at {tip[:7]}, not the merged head {head[:7]}, so it is kept")
    if current_branch() != base:
        run(["git", "switch", base])
    run(["git", "pull", "--ff-only"])
    if local:
        run(["git", "branch", "-D", branch])
    if remote:
        run(["git", "push", "origin", "--delete", branch])
    if run(["git", "status", "--porcelain"]):
        raise Refused(f"merged, but the working tree on {base} is not clean")
    if not passes(["git", "merge-base", "--is-ancestor", merged, "HEAD"], COMMAND_TIMEOUT):
        raise Refused(f"merged as {merged[:7]}, but local {base} does not contain it")
    print(f"MERGED: PR #{number} as {merged[:7]}; {branch} deleted locally and on origin; {base} clean")
    return 0


def merged_commit(view: dict) -> str | None:
    """The merge commit when GitHub reports the pull request MERGED; None while it is queued or pending."""
    commit = view.get("mergeCommit") or {}
    return commit.get("oid") if view.get("state") == "MERGED" and commit.get("oid") else None


def cmd_issue(args) -> int:
    loops = ROOT / "OPEN_LOOPS.md"
    text = loops.read_text(encoding="utf-8")
    link_issue(text, args.loop, 0, "https://github.com/x/y/issues/0")  # refuse before creating anything
    body = (Path(args.body_file).read_text(encoding="utf-8") if args.body_file else args.body or "").strip()
    body += f"\n\n---\nMirrors `OPEN_LOOPS.md` {args.loop}, the record of truth. Closing either closes the other (ADR-094)."
    output = run(["gh", "issue", "create", "--title", f"[{args.kind}] {args.title}", "--body", body])
    match = ISSUE_URL.search(output)
    if not match:
        raise Refused(f"an issue may have been created, but its URL was not found in: {output[-200:]}; link it by hand")
    url, number = match.group(0), int(match.group(1))
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
