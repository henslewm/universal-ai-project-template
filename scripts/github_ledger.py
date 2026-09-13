#!/usr/bin/env python3
"""Publish and recover canonical task records using GitHub; never execute workers."""
from __future__ import annotations

import argparse
import base64
import copy
import json
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote

import feedback
import model_router as router
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
PATH = ".autonomy/ledger.json"
MAX_BYTES = 900_000  # GitHub Contents API returns embedded content below 1 MB.
SHA = re.compile(r"[0-9a-f]{40}")
# Rotating publishers or disabling writes must not make an existing registry unreadable.
BINDING = ("schema_version", "repository", "state_branch", "accepted_branch", "master_issue")
TASK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


def exact(value, keys):
    feedback.exact(value, keys)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) is int and value > 0


def valid_branch(value):
    # Restricted ASCII subset of git check-ref-format --branch, with portable dots.
    return (isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", value)
            and value != "HEAD" and ".." not in value and "//" not in value
            and all(part and not part.startswith(".") and not part.endswith((".lock", ".")) for part in value.split("/")))


def ref_conflict(name, existing):
    # Git stores refs as paths, so refs/heads/a and refs/heads/a/b cannot both exist.
    return any(other.startswith(name + "/") or name.startswith(other + "/") for other in existing)


def config_valid(config):
    schema = wp.read_json(ROOT / "config/github-ledger.schema.json")
    errors = wp.schema_errors(wp.Draft202012Validator(schema), config)
    require(not errors, "; ".join(errors))
    require(type(config["schema_version"]) is int, "Configuration version must be an integer")
    require(number(config["master_issue"]), "Master issue must be a positive integer")
    require(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*(\[bot\])?", login) for login in config["publishers"]), "Unsafe publisher login")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9._-]{0,99}", config["repository"]), "Unsafe repository name")
    require(config["state_branch"] != config["accepted_branch"], "State and accepted branches must differ")
    require(not ref_conflict(config["state_branch"], {config["accepted_branch"]}), "Configured branch refs conflict; one is a path prefix of the other")
    for branch in (config["state_branch"], config["accepted_branch"]):
        require(valid_branch(branch), "Unsafe branch name")


def authority(config, root, profile=None):
    config_valid(config)
    require(config["enabled"], "GitHub ledger writes are disabled")
    anchor = feedback.active_anchor(root, profile)
    project = wp.read_json(Path(root) / "config/project.json")
    permissions = project.get("connector_permissions", {})
    require(isinstance(permissions, dict) and permissions.get("github") == "read-and-project-write",
            "Project configuration must explicitly permit GitHub project writes")
    marker = "GitHub ledger configuration SHA-256: " + router.digest(config)
    require(marker in (Path(root) / "CONNECTOR_PLAN.md").read_text(encoding="utf-8"),
            "Approve the exact GitHub configuration in the bound CONNECTOR_PLAN.md before writes")
    return anchor


def feedback_state(events):
    if not events:
        return None
    with tempfile.TemporaryDirectory(prefix="autonomy-replay-") as temporary:
        for index, event in enumerate(events, 1):
            wp.write_new(Path(temporary) / f"{index:08d}.json", json.dumps(event, allow_nan=False))
        return feedback.replay(temporary)[0]


def prefix(old, new, description):
    require(len(new) >= len(old) and new[:len(old)] == old, f"{description} must preserve its existing prefix")


def packet_extends(old, new):
    require(old["task_id"] == new["task_id"] and old["domain_profile"] == new["domain_profile"], "Packet identity changed")
    prefix(old["revision_history"], new["revision_history"], "Packet revisions")
    prefix(old["events"], new["events"], "Packet events")


def row_valid(task_id, row, anchor):
    exact(row, {"issue", "packet", "feedback", "branch", "pr", "superseded_prs", "acceptance", "discoveries"})
    require(number(row["issue"]), "Canonical issue must be a positive integer")
    wp.require_valid(row["packet"])
    require(task_id == row["packet"]["task_id"] and TASK.fullmatch(task_id), "Task identity differs")
    require(isinstance(row["feedback"], list), "Feedback must be an event array")
    state = feedback_state(row["feedback"])
    if state:
        require(state["anchor"] == anchor, "Feedback approval differs from this registry")
        packet_extends(state["packet"], row["packet"])
        if state["packet"] != row["packet"]:
            require(state["status"] == "REVIEW_PENDING" and not state["pending"], "Cannot extend a held or unfinished feedback packet")
            require(state["packet"]["revision_history"] == row["packet"]["revision_history"], "Review cannot revise the feedback contract")
            for event in row["packet"]["events"][len(state["packet"]["events"]):]:
                require(event["role"] in {"reviewer", "integrator"}, "Only review/integration may extend completed feedback")
    require(row["branch"] is None or valid_branch(row["branch"]), "Invalid implementation branch")
    require(row["pr"] is None or number(row["pr"]), "Invalid PR number")
    if row["pr"]:
        require(row["branch"] is not None, "PR requires a branch")
    superseded = row["superseded_prs"]
    require(isinstance(superseded, list) and all(number(value) for value in superseded) and
            len(set(superseded)) == len(superseded) and row["pr"] not in superseded,
            "Superseded PRs must be distinct positive integers and exclude the current PR")
    if superseded:
        require(row["branch"] is not None, "A superseded PR requires the task branch")
    receipt = row["acceptance"]
    if receipt is not None:
        exact(receipt, {"commit", "evidence", "review"})
        require(isinstance(receipt["commit"], str) and SHA.fullmatch(receipt["commit"]), "Acceptance needs an exact commit SHA")
        for name in ("evidence", "review"):
            require(isinstance(receipt[name], list) and 0 < len(receipt[name]) <= 20 and
                    all(isinstance(item, str) and 0 < len(item.strip()) <= 2000 for item in receipt[name]), "Acceptance needs bounded verification and review evidence")
        require(row["packet"]["state"] == "VERIFIED", "Acceptance requires a VERIFIED packet")
        require(state is None or state["status"] == "REVIEW_PENDING", "Feedback is not ready for acceptance")
    require(isinstance(row["discoveries"], dict), "Discovery mappings must be an object")
    known = {router.digest(item) for item in state["discoveries"]} if state else set()
    require(set(row["discoveries"]) <= known, "Unknown discovery mapping")
    require(all(number(value) and value != row["issue"] for value in row["discoveries"].values()), "Unrelated discoveries need separate issues")
    if receipt is not None:
        require(known <= set(row["discoveries"]), "Map every discovery before freezing an accepted task")
    return state


def entry_for(task_id, row):
    state = feedback_state(row["feedback"])
    revision = wp.current(row["packet"])
    receipt = row["acceptance"]
    preview = None if receipt is None else {"commit": receipt["commit"], "evidence_hash": router.digest(receipt),
        "evidence_count": len(receipt["evidence"]), "review_count": len(receipt["review"]),
        "evidence_preview": [item[:200] for item in receipt["evidence"][:2]],
        "review_preview": [item[:200] for item in receipt["review"][:2]]}
    summary = {"task_id": task_id, "issue": row["issue"], "revision": revision["version"],
               "contract_hash": revision["hash"], "packet_state": row["packet"]["state"],
               "feedback_status": state["status"] if state else None,
               "attempts": len(state["attempts"]) if state else 0,
               "pending_dispatch": state["pending"] if state else None,
               "event_count": len(row["feedback"]), "row_hash": router.digest(row),
               "acceptance": preview, "pr": row["pr"], "superseded_prs": list(row["superseded_prs"])}
    return {"id": router.digest(summary), "summary": summary, "status": "new", "claim": None,
            "comment": None, "released": []}


def registry_profile(state):
    profiles = {row["packet"]["domain_profile"] for row in state["tasks"].values()}
    require(len(profiles) <= 1, "Registered packets must share one approved domain profile")
    return next(iter(profiles), None)


def validate(state, config, prior=None):
    exact(state, {"schema_version", "config", "anchor", "tasks", "outbox"})
    require(type(state["schema_version"]) is int and state["schema_version"] == 1, "Unsupported registry version")
    config_valid(config)
    config_valid(state["config"])
    require(all(state["config"][key] == config[key] for key in BINDING), "Registry identity configuration differs")
    require(isinstance(state["anchor"], str) and re.fullmatch(r"[0-9a-f]{64}", state["anchor"]), "Invalid approval anchor")
    require(isinstance(state["tasks"], dict) and isinstance(state["outbox"], list), "Invalid registry collections")
    homes, branches, prs = set(), set(), set()
    for task_id, row in state["tasks"].items():
        row_valid(task_id, row, state["anchor"])
        require(row["issue"] != config["master_issue"] and row["issue"] not in homes, "Duplicate or master issue home")
        homes.add(row["issue"])
        if row["branch"]:
            taken = branches | {config["state_branch"], config["accepted_branch"]}
            require(row["branch"] not in taken, "Duplicate or reserved implementation branch")
            require(not ref_conflict(row["branch"], taken), "Implementation branch ref conflicts; one name is a path prefix of another")
            branches.add(row["branch"])
        for value in ([row["pr"]] if row["pr"] else []) + row["superseded_prs"]:
            require(value not in prs, "Duplicate PR home")
            prs.add(value)
    registry_profile(state)
    if state["tasks"]:
        wp.graph_order([row["packet"] for row in state["tasks"].values()])
    reserved_homes = homes | {config["master_issue"]}
    discovery_homes = set()
    for row in state["tasks"].values():
        require(not (set(row["discoveries"].values()) & reserved_homes),
                "Discovery homes must be separate from the master and all canonical task issues")
        for issue in row["discoveries"].values():
            require(issue not in discovery_homes, "Every discovery needs its own separate issue")
            discovery_homes.add(issue)
    ids = set()
    for item in state["outbox"]:
        exact(item, {"id", "summary", "status", "claim", "comment", "released"})
        require(item["id"] == router.digest(item["summary"]) and item["id"] not in ids, "Duplicate or corrupt publication id")
        require(len(json.dumps(item["summary"], ensure_ascii=False).encode("utf-8")) < 55_000, "Publication exceeds its safe comment size")
        ids.add(item["id"])
        require(item["summary"]["task_id"] in state["tasks"] and item["summary"]["issue"] == state["tasks"][item["summary"]["task_id"]]["issue"], "Publication has no canonical home")
        require(item["status"] in {"new", "claimed", "done"}, "Invalid publication state")
        require(isinstance(item["released"], list) and len(set(item["released"])) == len(item["released"]) and
                all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32}", value) for value in item["released"]) and
                item["claim"] not in item["released"], "Released claims must be distinct and retired")
        require((item["status"] == "new" and item["claim"] is None and item["comment"] is None) or
                (item["status"] != "new" and isinstance(item["claim"], str) and re.fullmatch(r"[0-9a-f]{32}", item["claim"]) and
                 ((item["status"] == "claimed" and item["comment"] is None) or (item["status"] == "done" and number(item["comment"])))), "Invalid publication claim/receipt")
    for task_id, row in state["tasks"].items():
        projections = [item for item in state["outbox"] if item["summary"]["task_id"] == task_id]
        require(projections and projections[-1]["summary"] == entry_for(task_id, row)["summary"],
                "The newest publication for a task must project its committed row")
    if prior:
        require(state["anchor"] == prior["anchor"], "Approval cannot be replaced inside an existing registry")
        require(set(prior["tasks"]) <= set(state["tasks"]), "Tasks cannot be removed")
        for task_id, old in prior["tasks"].items():
            new = state["tasks"][task_id]
            require(new["issue"] == old["issue"], "Canonical task home cannot change")
            packet_extends(old["packet"], new["packet"])
            prefix(old["feedback"], new["feedback"], "Feedback events")
            if old["acceptance"]:
                require(new == old, "Accepted task is immutable; create a new task for follow-up work")
            require(old["branch"] is None or new["branch"] == old["branch"], "Existing branch binding cannot change")
            prefix(old["superseded_prs"], new["superseded_prs"], "Superseded PRs")
            if old["pr"] is not None and new["pr"] != old["pr"]:
                # A PR closed without merging is recorded, then may be replaced or cleared.
                require(new["superseded_prs"][len(old["superseded_prs"]):] == [old["pr"]],
                        "Record the superseded PR before replacing or clearing the binding")
            else:
                require(new["superseded_prs"] == old["superseded_prs"],
                        "Superseded PRs change only when the PR binding changes")
            require(all(new["discoveries"].get(key) == value for key, value in old["discoveries"].items()), "Discovery homes cannot be replaced")
        require(len(state["outbox"]) >= len(prior["outbox"]), "Publication history cannot be removed")
        for item in state["outbox"][len(prior["outbox"]):]:
            added = item["summary"]["task_id"]
            require(added in state["tasks"] and item["summary"] == entry_for(added, state["tasks"][added])["summary"],
                    "A new publication must project the row being committed")
        for old, new in zip(prior["outbox"], state["outbox"]):
            require(old["id"] == new["id"] and old["summary"] == new["summary"], "Publication history changed")
            require((old["status"], new["status"]) in {("new", "new"), ("new", "claimed"), ("claimed", "claimed"),
                                                       ("claimed", "done"), ("done", "done"), ("claimed", "new")}, "Publication state regressed")
            if (old["status"], new["status"]) == ("claimed", "new"):
                # Releasing a claim retires it permanently; the operation itself proves no comment exists.
                require(new["claim"] is None and new["comment"] is None and
                        new["released"] == old["released"] + [old["claim"]],
                        "A released claim must be recorded and cleared together")
            else:
                require(new["released"] == old["released"], "Release history cannot change")
                if old["claim"]:
                    require(new["claim"] == old["claim"], "Publication claim changed")
                if old["comment"]:
                    require(new["comment"] == old["comment"], "Publication receipt changed")
    require(len(wp.canonical(state).encode("utf-8")) <= MAX_BYTES, "Registry capacity reached; preserve it and propose a storage migration before more work")
    return state


class APIError(ValueError):
    pass


class GitHub:
    """Use gh's existing credential store; never accept tokens or shell commands."""
    def __init__(self, repository):
        self.repository = repository

    def call(self, method, endpoint, data=None):
        return self.request(method, f"repos/{self.repository}/{endpoint}", data)

    def identity(self):
        return self.request("GET", "user")["login"]

    def request(self, method, endpoint, data=None):
        args = ["gh", "api", "--hostname", "github.com", "--method", method,
                "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28",
                endpoint]
        if data is not None:
            args += ["--input", "-"]
        try:
            result = subprocess.run(args, input=json.dumps(data) if data is not None else None,
                                    text=True, encoding="utf-8", capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as exc:
            raise APIError("GitHub response timed out; write outcome is uncertain. Reconcile before retrying.") from exc
        if result.returncode:
            # Do not echo arbitrary API/CLI output, which can include private material.
            status = re.search(r"HTTP (\d{3})", result.stderr)
            raise APIError(f"GitHub {method} failed ({status.group(1) if status else 'unknown outcome'}); read/reconcile before retrying")
        return json.loads(result.stdout)

    def pages(self, endpoint):
        output = []
        for page in range(1, 1001):
            values = self.call("GET", endpoint + ("&" if "?" in endpoint else "?") + f"per_page=100&page={page}")
            require(isinstance(values, list), "Expected a complete paginated list")
            output.extend(values)
            if len(values) < 100:
                return output
        raise ValueError("Pagination safety bound exceeded; incomplete data cannot validate state")


class Ledger:
    def __init__(self, config, api=None):
        config_valid(config)
        self.config = config
        self.api = api or GitHub(config["repository"])

    def head(self):
        return self.api.call("GET", "git/ref/heads/" + quote(self.config["state_branch"], safe="/"))["object"]["sha"]

    def read(self, commit=None):
        commit = commit or self.head()
        require(isinstance(commit, str) and SHA.fullmatch(commit), "Exact state commit required")
        blob = self.api.call("GET", f"contents/{PATH}?ref={commit}")
        require(blob.get("encoding") == "base64" and isinstance(blob.get("content"), str), "Missing/oversize state content")
        decoded = base64.b64decode(blob["content"], validate=False)
        require(len(decoded) <= MAX_BYTES, "Missing/oversize state content")
        raw = decoded.decode("utf-8")
        # Reuse strict JSON handling (duplicate keys and nonfinite numbers fail).
        with tempfile.TemporaryDirectory(prefix="autonomy-state-") as temporary:
            path = Path(temporary) / "state.json"
            path.write_text(raw, encoding="utf-8")
            state = wp.read_json(path)
        validate(state, self.config)
        return state, blob["sha"], commit

    def save(self, state, expected_blob=None, prior=None):
        validate(state, self.config, prior)
        payload = {"message": "Record autonomous task ledger " + router.digest(state)[:12],
                   "branch": self.config["state_branch"],
                   "content": base64.b64encode(wp.canonical(state).encode("utf-8")).decode("ascii")}
        if expected_blob is not None:
            payload["sha"] = expected_blob
        # GitHub Contents API rejects a stale file SHA; no force or automatic retry.
        response = self.api.call("PUT", "contents/" + PATH, payload)
        return response["commit"]["sha"]

    def initialize(self, root):
        anchor = authority(self.config, root)
        self.issue(self.config["master_issue"])
        base = self.api.call("GET", "git/ref/heads/" + quote(self.config["accepted_branch"], safe="/"))["object"]["sha"]
        self.api.call("POST", "git/refs", {"ref": "refs/heads/" + self.config["state_branch"], "sha": base})
        state = {"schema_version": 1, "config": self.config, "anchor": anchor, "tasks": {}, "outbox": []}
        return self.save(state)

    def issue(self, number):
        value = self.api.call("GET", f"issues/{number}")
        require(value.get("number") == number and "pull_request" not in value, "Expected a canonical issue, not a PR")
        return value

    def live_row(self, row, closing=False):
        issue = self.issue(row["issue"])
        require(issue["state"] == "open" or row["acceptance"] is not None, "Closed task has no accepted state/evidence")
        pr = None
        if row["pr"]:
            pr = self.api.call("GET", f"pulls/{row['pr']}")
            require(pr["head"]["ref"] == row["branch"] and pr["head"]["repo"]["full_name"].lower() == self.config["repository"].lower() and
                    pr["base"]["ref"] == self.config["accepted_branch"], "PR repository/branch binding differs")
            if not row["acceptance"]:
                require(pr["state"] == "open", "Closed PR has no accepted ledger evidence; supersede it or record acceptance")
        for number_ in row["superseded_prs"]:
            superseded = self.api.call("GET", f"pulls/{number_}")
            require(superseded["state"] == "closed" and not superseded["merged"],
                    "A superseded PR must be closed without having been merged")
        receipt = row["acceptance"]
        if receipt:
            if pr:
                require(pr["merged"] and pr["merge_commit_sha"] == receipt["commit"], "Acceptance does not match the merged PR commit")
            comparison = self.api.call("GET", f"compare/{receipt['commit']}...{quote(self.config['accepted_branch'], safe='/')}")
            require(comparison["status"] in {"ahead", "identical"}, "Accepted commit is not on the accepted branch")
        for related in row["discoveries"].values():
            self.issue(related)
        if closing:
            require(receipt is not None, "Cannot close without accepted commit and verification/review evidence")
            state = feedback_state(row["feedback"])
            require(not state or {router.digest(item) for item in state["discoveries"]} <= set(row["discoveries"]), "Untracked discoveries prevent closure")
        return issue

    def put_task(self, row, root):
        anchor = authority(self.config, root, row["packet"]["domain_profile"])
        state, blob, _ = self.read()
        require(state["anchor"] == anchor, "Current approval differs; registry migration requires a decision")
        prior = copy.deepcopy(state)
        task_id = row["packet"]["task_id"]
        state["tasks"][task_id] = copy.deepcopy(row)
        entry = entry_for(task_id, row)
        if entry["id"] not in {item["id"] for item in state["outbox"]}:
            state["outbox"].append(entry)
        validate(state, self.config, prior)
        self.live_row(row)
        if state == prior:
            return self.head()
        return self.save(state, blob, prior)

    def body(self, entry, commit):
        summary = json.dumps(entry["summary"], ensure_ascii=False, indent=2)
        fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", summary)), default=0))
        return (f"<!-- autonomy-ledger:{entry['id']} -->\nCanonical task record; supplied evidence still requires independent acceptance.\n\n"
                f"{fence}json\n{summary}\n{fence}\n\n"
                f"Full packet and immutable attempt evidence: https://github.com/{self.config['repository']}/blob/{commit}/{PATH}\n")

    def matches(self, entry):
        marker = f"<!-- autonomy-ledger:{entry['id']} -->"
        comments = self.api.pages(f"issues/{entry['summary']['issue']}/comments")
        matches = [comment for comment in comments if marker in comment.get("body", "")]
        require(len(matches) <= 1, "Duplicate publication markers require reconciliation")
        if not matches:
            return None
        comment = matches[0]
        require(comment["user"]["login"].lower() in {name.lower() for name in self.config["publishers"]}, "Untrusted publication author")
        match = re.search(r"/blob/([0-9a-f]{40})/\.autonomy/ledger\.json\n$", comment["body"])
        require(match is not None and comment["body"] == self.body(entry, match[1]), "Publication content was edited or corrupted")
        recorded = self.read(match[1])[0]
        require(any(item["id"] == entry["id"] and item["summary"] == entry["summary"] for item in recorded["outbox"]), "Receipt points to unrelated state")
        return comment

    def publish(self, root, reconcile_only=False):
        anchor = authority(self.config, root)
        login = self.api.identity()
        require(login.lower() in {name.lower() for name in self.config["publishers"]},
                "Authenticated publisher is not allowed; no publication claim was made")
        state, _, _ = self.read()
        require(state["anchor"] == anchor, "Current approval differs")
        require(authority(self.config, root, registry_profile(state)) == anchor, "Approved project profile differs from the registry")
        # Exactly one publisher holds each operation. Unknown POST results never retry.
        for entry_id in [item["id"] for item in state["outbox"] if item["status"] != "done"]:
            state, blob, commit = self.read()
            prior = copy.deepcopy(state)
            item = next(item for item in state["outbox"] if item["id"] == entry_id)
            if item["status"] == "done":
                continue
            comment = self.matches(item)
            if item["status"] == "new":
                require(comment is None, "Unclaimed publication already exists; investigate before adopting")
                if reconcile_only:
                    continue
                item["status"], item["claim"] = "claimed", uuid.uuid4().hex
                commit = self.save(state, blob, prior)  # CAS claim before POST.
                self.api.call("POST", f"issues/{item['summary']['issue']}/comments", {"body": self.body(item, commit)})
                comment = self.matches(item)
                require(comment is not None, "POST outcome is not visible; preserve claim and reconcile later")
            else:
                require(comment is not None, "Claimed publication has no visible receipt; do not retry an uncertain POST")
            state, blob, _ = self.read()
            prior = copy.deepcopy(state)
            current = next(value for value in state["outbox"] if value["id"] == entry_id)
            require(current["claim"] == item["claim"], "Publication ownership changed")
            current["status"], current["comment"] = "done", comment["id"]
            self.save(state, blob, prior)
        return self.head()

    def release(self, root, entry=None):
        """Retire a publication claim only on positive evidence that no comment exists."""
        anchor = authority(self.config, root)
        login = self.api.identity()
        require(login.lower() in {name.lower() for name in self.config["publishers"]},
                "Authenticated publisher is not allowed; no claim was released")
        state, _, _ = self.read()
        require(state["anchor"] == anchor, "Current approval differs")
        require(authority(self.config, root, registry_profile(state)) == anchor, "Approved project profile differs from the registry")
        targets = [item["id"] for item in state["outbox"]
                   if item["status"] == "claimed" and (entry is None or item["id"] == entry)]
        require(entry is None or targets, "No claimed publication has that id")
        released = []
        for entry_id in targets:
            state, blob, _ = self.read()
            prior = copy.deepcopy(state)
            item = next(value for value in state["outbox"] if value["id"] == entry_id)
            if item["status"] != "claimed":
                continue
            require(self.matches(item) is None,
                    "A visible receipt exists; complete the publication instead of releasing its claim")
            item["released"] = item["released"] + [item["claim"]]
            item["status"], item["claim"] = "new", None
            self.save(state, blob, prior)
            released.append(entry_id)
        return {"released": released, "commit": self.head()}

    def close(self, task_id, root):
        anchor = authority(self.config, root)
        state, _, _ = self.read()
        require(state["anchor"] == anchor, "Current approval differs")
        require(authority(self.config, root, registry_profile(state)) == anchor, "Approved project profile differs from the registry")
        row = state["tasks"][task_id]
        self.live_row(row, closing=True)
        entry = next(item for item in state["outbox"] if item["id"] == entry_for(task_id, row)["id"])
        comment = self.matches(entry) if entry["status"] == "done" else None
        require(comment is not None and comment["id"] == entry["comment"], "Publish verified completion evidence before closing")
        return self.api.call("PATCH", f"issues/{row['issue']}", {"state": "closed", "state_reason": "completed"})

    def audit(self, packets=None, workspace=None, task_id=None, project_state=None):
        state, _, commit = self.read()
        errors = []
        try:
            self.issue(self.config["master_issue"])
        except ValueError as exc:
            errors.append(str(exc))
        for key, row in state["tasks"].items():
            try:
                issue = self.live_row(row, closing=bool(row["acceptance"]))
                require(not row["acceptance"] or issue["state"] == "closed", "Accepted task is still open; complete closure")
                controller = feedback_state(row["feedback"])
                require(not controller or {router.digest(item) for item in controller["discoveries"]} <= set(row["discoveries"]), "Untracked discovery needs its own issue")
            except ValueError as exc:
                errors.append(f"{key}: {exc}")
        for item in state["outbox"]:
            try:
                require(item["status"] == "done", "Unpublished or uncertain task evidence")
                require(self.matches(item)["id"] == item["comment"], "Missing or replaced comment receipt")
            except (ValueError, TypeError) as exc:
                errors.append(f"{item['summary']['task_id']} publication {item['id'][:12]}: {exc}")
        if packets is not None:
            seen = set()
            for packet in packets:
                wp.require_valid(packet)
                key = packet["task_id"]
                if key in seen:
                    errors.append(f"Duplicate local packet: {key}")
                seen.add(key)
                if key not in state["tasks"] or packet != state["tasks"][key]["packet"]:
                    errors.append(f"Untracked or unpublished local packet: {key}")
        if workspace is not None:
            require(task_id in state["tasks"], "Workspace requires its registered task id")
            def git(*args):
                return subprocess.run(["git", "-C", str(workspace), *args], capture_output=True, text=True, check=True, timeout=30).stdout.strip()
            origin = git("remote", "get-url", "origin")
            remote = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([A-Za-z0-9-]+/[A-Za-z0-9._-]+?)(?:\.git)?/?", origin)
            if not remote or remote[1].lower() != self.config["repository"].lower():
                errors.append("Workspace origin differs from the configured GitHub repository")
            head = git("rev-parse", "HEAD")
            if git("branch", "--show-current") != state["tasks"][task_id]["branch"]:
                errors.append("Workspace branch differs from the task's registered branch")
            elif state["tasks"][task_id]["branch"]:
                remote_head = self.api.call("GET", "git/ref/heads/" + quote(state["tasks"][task_id]["branch"], safe="/"))["object"]["sha"]
                if head != remote_head:
                    errors.append("Workspace HEAD differs from the published task branch")
            if git("status", "--porcelain", "--untracked-files=all"):
                errors.append("Workspace contains uncommitted or untracked work")
        projection = project_projection(state, commit)
        if project_state is not None and project_state != projection:
            errors.append("Project-state index is stale or contradicts the current registry")
        return {**projection, "errors": errors, "valid": not errors}


def project_projection(state, commit):
    return {"state_commit": commit, "repository": state["config"]["repository"],
            "master_issue": state["config"]["master_issue"],
            "tasks": {key: {"issue": row["issue"], "state": row["packet"]["state"],
                             "accepted_commit": row["acceptance"]["commit"] if row["acceptance"] else None}
                      for key, row in state["tasks"].items()}}


def recover(state, destination, config=None):
    # The embedded configuration is remote-supplied; prefer the operator's own when available.
    validate(state, config if config is not None else state["config"])
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    wp.write_new(destination / "registry.json", json.dumps(state, indent=2, ensure_ascii=False))
    for task_id, row in state["tasks"].items():
        # Hash the identity to avoid case, trailing-dot and device-name collisions.
        task = destination / ("task-" + router.digest(task_id))
        task.mkdir()
        wp.write_new(task / "packet.json", json.dumps(row["packet"], indent=2, ensure_ascii=False))
        if row["feedback"]:
            (task / "feedback").mkdir()
            for index, event in enumerate(row["feedback"], 1):
                wp.write_new(task / "feedback" / f"{index:08d}.json", json.dumps(event, indent=2, ensure_ascii=False))
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "publish", "reconcile"):
        commands.add_parser(name)
    free = commands.add_parser("release")
    free.add_argument("--entry")
    put = commands.add_parser("put")
    put.add_argument("row", type=Path)
    close = commands.add_parser("close")
    close.add_argument("task_id")
    restore = commands.add_parser("recover")
    restore.add_argument("destination", type=Path)
    restore.add_argument("--commit")
    audit = commands.add_parser("audit")
    audit.add_argument("--packets", nargs="*", type=Path)
    audit.add_argument("--workspace", type=Path)
    audit.add_argument("--task-id")
    audit.add_argument("--project-state", type=Path)
    project = commands.add_parser("project-state")
    project.add_argument("destination", type=Path)
    offline = commands.add_parser("validate-state")
    offline.add_argument("state", type=Path)
    args = parser.parse_args(argv)
    try:
        ledger = Ledger(wp.read_json(args.config))
        if args.command == "validate-state":
            validate(wp.read_json(args.state), ledger.config)
            result = {"valid": True, "external_state_verified": False}
        elif args.command == "init":
            result = {"commit": ledger.initialize(args.root)}
        elif args.command == "put":
            result = {"commit": ledger.put_task(wp.read_json(args.row), args.root)}
        elif args.command in {"publish", "reconcile"}:
            result = {"commit": ledger.publish(args.root, args.command == "reconcile")}
        elif args.command == "release":
            result = ledger.release(args.root, args.entry)
        elif args.command == "close":
            result = {"state": ledger.close(args.task_id, args.root)["state"]}
        elif args.command == "recover":
            state, _, commit = ledger.read(args.commit)
            result = {"destination": str(recover(state, args.destination, ledger.config)),
                      "state_commit": commit, "execution_authorized": False}
        elif args.command == "project-state":
            state, _, commit = ledger.read()
            wp.write_new(args.destination, json.dumps(project_projection(state, commit), indent=2))
            result = {"destination": str(args.destination), "state_commit": commit}
        else:
            result = ledger.audit([wp.read_json(path) for path in args.packets] if args.packets is not None else None,
                                  args.workspace, args.task_id,
                                  wp.read_json(args.project_state) if args.project_state else None)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("valid", True) else 2
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"GitHub ledger refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
