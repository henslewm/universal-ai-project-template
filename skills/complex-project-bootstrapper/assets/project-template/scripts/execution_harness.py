#!/usr/bin/env python3
"""Prepare and ingest bounded worker runs for a replaceable execution harness; never invoke a model."""
from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import hashlib
import json
import re
import stat
import sys
from decimal import ROUND_CEILING
from pathlib import Path, PureWindowsPath

import cli_colors
import cli_exit
import feedback
import model_router as router
import work_packet as wp

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDERS = {"provider", "model", "rules", "brief", "report", "workspace", "rundir"}
ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]{0,99}")
# Conservative shapes for material that must never reach configuration, briefs, reports or logs.
SECRETS = (
    re.compile(r"(?i)\b(api[_-]?key|secret|passwd|password|token|authorization|bearer)\b\s*[:=]"),
    re.compile(r"\b(sk|rk|pk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\baws_secret_access_key\b"),
)
REPORT_FIELDS = {"dispatch_id", "outcome", "summary", "scope_status", "architecture_conflict",
                 "validation", "evidence", "discoveries", "api_cost_usd", "cost_evidence"}
# Declared once: the brief renderer, the ledger-free verifier and the tests all read this.
LEGACY_BRIEF_FIELDS = {"schema_version", "dispatch_id", "binding", "harness", "paths", "bounds", "contract",
                       "architect_guidance", "prior_failures", "failure_groups", "review_rejections",
                       "worker_rule", "report_contract"}
BRIEF_FIELDS = LEGACY_BRIEF_FIELDS | {"startup"}
# A worker reads only its bounded rules and what its own contract names. Governing documents are
# architect/integrator material: the brief records which versions applied, never their text.
GOVERNANCE_DOCUMENTS = ("MASTER_INSTRUCTIONS.md", "AUTONOMY_CONTROL_PLANE.md", "PROJECT_CHARTER.md",
                        "WORK_PACKET_PROTOCOL.md", "EXECUTION_HARNESS_PROTOCOL.md")
WORKER_RULES_PATH = "templates/harness/BOUNDED_WORKER_RULES.md"
DEFAULT_STARTUP_MAX_CHARS = 12000
STARTUP_STEPS = (
    "Before editing, read startup.rules, then every startup.documents entry in order.",
    "Read contract, architect_guidance, prior_failures, failure_groups and review_rejections.",
    "Identify allowed and prohibited scope, required validation and stop conditions before implementation.",
    "startup.governance records which governing versions applied; it is provenance, not reading.",
    "Missing required input: stop and report BLOCKED. Conflict with governance: report ARCHITECTURE_CONFLICT.",
)
WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}


def check_fields():
    """The exact fields a reported validation check needs, read from the controller's own schema."""
    return sorted(feedback.SCHEMA["$defs"]["validation_check"]["required"])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def secret_free(value, where):
    text = value if isinstance(value, str) else wp.canonical(value)
    for pattern in SECRETS:
        require(pattern.search(text) is None, f"{where} must not contain credential-like material")
    return value


def startup_path(value):
    """Accept only explicit project-relative paths, on Windows and other hosts alike."""
    require(isinstance(value, str) and bool(value.strip()), "Startup document path must be nonblank")
    windows = PureWindowsPath(value)
    parts = value.replace("\\", "/").split("/")
    require(not windows.drive and not windows.root and not Path(value).is_absolute()
            and all(part not in ("", ".", "..") and ":" not in part for part in parts),
            "Startup document paths must be relative and contain no traversal")
    require(all(not part.endswith((" ", "."))
                and not any(ord(character) < 32 or character in '<>:"|?*' for character in part)
                and part.split(".", 1)[0].rstrip(" ").upper() not in WINDOWS_DEVICES for part in parts),
            "Startup document paths must not contain Win32 aliases, device names or invalid characters")
    return "/".join(parts)


def safe_file(root, relative):
    """Locate a project file without following symbolic links or Windows reparse points."""
    relative = startup_path(relative)
    root = Path(root).absolute()
    path = root
    try:
        components = list(reversed(root.parents)) + [root]
        for component in relative.split("/"):
            path = path / component
            components.append(path)
        for component in components:
            metadata = component.lstat()
            require(not stat.S_ISLNK(metadata.st_mode)
                    and not (getattr(metadata, "st_file_attributes", 0) & 0x400),
                    f"Startup document path contains a symlink or reparse point: {relative}")
        require(stat.S_ISREG(metadata.st_mode), f"Startup document is not a regular file: {relative}")
        require(path.resolve(strict=True).is_relative_to(root.resolve(strict=True)),
                f"Startup document resolves outside the project: {relative}")
    except OSError as exc:
        raise ValueError(f"Startup document is missing or unreadable: {relative}") from exc
    return relative, path


def governance_reference(root, relative):
    """Record which governing version applied without handing its text to the worker."""
    relative, path = safe_file(root, relative)
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError(f"Startup document is missing or unreadable: {relative}") from exc
    return {"path": relative, "sha256": digest}


def startup_document(root, relative, remaining):
    """Read bounded UTF-8 text the worker must read in full, with its digest."""
    relative, path = safe_file(root, relative)
    remaining = max(remaining, 0)
    try:
        # UTF-8 needs at most four bytes per character. Read one excess byte to detect an
        # oversized source without loading an unbounded file before applying the limit.
        with path.open("rb") as stream:
            raw = stream.read(remaining * 4 + 1)
        content = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Startup document is missing or unreadable: {relative}") from exc
    require(len(raw) <= remaining * 4 and len(content) <= remaining,
            f"Startup instructions exceed startup_max_chars at {relative}")
    require(bool(content.strip()), f"Startup document is empty: {relative}")
    secret_free(content, f"Startup document {relative}")
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
            "content_lines": content.splitlines(keepends=True)}


def not_governance(relative):
    """A governing document travels as a digest only; naming it for embedding is refused.

    Compared case-insensitively so a Windows alias of the same file cannot slip through.
    """
    require(relative.casefold() not in {name.casefold() for name in GOVERNANCE_DOCUMENTS},
            f"Governing document {relative} cannot be a worker instruction; workers receive only its digest")
    return relative


def startup_max_chars(config):
    return config["limits"].get("startup_max_chars", DEFAULT_STARTUP_MAX_CHARS)


def embedded_valid(document, where):
    """Check one embedded document's shape and digest; return its length in characters."""
    require(isinstance(document, dict), f"{where} must be an object")
    feedback.exact(document, {"path", "sha256", "content_lines"})
    relative = startup_path(document["path"])
    require(relative == document["path"], f"{where} path must use its canonical relative spelling")
    lines = document["content_lines"]
    require(isinstance(lines, list) and bool(lines) and all(isinstance(line, str) and line for line in lines),
            f"{where} content_lines must be a nonempty array of strings")
    content = "".join(lines)
    require(bool(content.strip()), f"{where} is empty: {relative}")
    secret_free(content, where)
    require(isinstance(document["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", document["sha256"]) is not None,
            f"{where} sha256 must be a lowercase SHA256 digest")
    require(hashlib.sha256(content.encode("utf-8")).hexdigest() == document["sha256"],
            f"{where} digest does not match its content: {relative}")
    return len(content)


def startup_valid(startup, contract, config):
    """Check a brief's startup block for shape and integrity; this never proves the worker read it."""
    require(isinstance(startup, dict), "Worker brief 1.1 requires its startup block")
    feedback.exact(startup, {"role", "steps", "rules", "governance", "documents"})
    require(startup["role"] == "worker", "Startup role must be worker")
    # Shape, not today's wording: a brief prepared before the steps or the governing-document list
    # changed must stay verifiable. The digests are the integrity guarantee.
    steps = startup["steps"]
    require(isinstance(steps, list) and bool(steps) and all(isinstance(step, str) and step.strip() for step in steps),
            "Startup steps must be a nonempty array of nonblank strings")
    size = embedded_valid(startup["rules"], "Bounded worker rules")
    require(startup["rules"]["path"] == WORKER_RULES_PATH, "Startup rules must be the bounded worker rules")
    governance = startup["governance"]
    require(isinstance(governance, list) and bool(governance), "Startup governance must be a nonempty array")
    for item in governance:
        require(isinstance(item, dict), "Governance reference must be an object")
        feedback.exact(item, {"path", "sha256"})
        require(startup_path(item["path"]) == item["path"], "Governance reference path must be canonical")
        require(isinstance(item["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None,
                "Governance reference sha256 must be a lowercase SHA256 digest")
    require(len({item["path"] for item in governance}) == len(governance), "Duplicate governance reference")
    documents = startup["documents"]
    require(isinstance(documents, list)
            and [item.get("path") if isinstance(item, dict) else None for item in documents]
            == [startup_path(path) for path in contract.get("worker_instructions", [])],
            "Startup documents must be exactly the contract's worker_instructions, in order")
    # The invariant is about text, not names: no embedded document may carry a governing
    # document's bytes, whatever path reached them (a case alias, a hard link or a copy).
    governing = {item["sha256"] for item in governance}
    for item in documents:
        size += embedded_valid(item, "Worker instruction")
        not_governance(item["path"])
        require(item["sha256"] not in governing,
                f"Worker instruction {item['path']} has the same content as a governing document; "
                "workers receive only its digest")
    require(size <= startup_max_chars(config),
            f"Startup instructions total {size} characters, over startup_max_chars {startup_max_chars(config)}")
    return startup


def startup_bundle(root, contract, config):
    """Supply the worker's rules and the packet's architect-curated instructions, nothing wider.

    Built before a reservation is spent, so a missing or unsafe source never costs an attempt.
    """
    remaining = startup_max_chars(config)
    rules = startup_document(ROOT, WORKER_RULES_PATH, remaining)
    remaining -= sum(len(line) for line in rules["content_lines"])
    documents = []
    for relative in contract.get("worker_instructions", []):
        document = startup_document(root, not_governance(startup_path(relative)), remaining)
        remaining -= sum(len(line) for line in document["content_lines"])
        documents.append(document)
    governance = [governance_reference(root, name) for name in GOVERNANCE_DOCUMENTS]
    return startup_valid({"role": "worker", "steps": list(STARTUP_STEPS), "rules": rules,
                          "governance": governance, "documents": documents}, contract, config)


def config_valid(config):
    schema = wp.read_json(ROOT / "config/execution-harness.schema.json")
    errors = wp.schema_errors(wp.Draft202012Validator(schema), config)
    require(not errors, "; ".join(errors))
    secret_free(config, "Harness configuration")
    ids = [harness["id"] for harness in config["harnesses"]]
    require(len(set(ids)) == len(ids), "Duplicate harness id")
    for harness in config["harnesses"]:
        for argument in [harness["command"]] + harness["argv"]:
            for name in re.findall(r"\{([^{}]*)\}", argument):
                require(name in PLACEHOLDERS, f"Unsupported placeholder {{{name}}}; allowed: " + ", ".join(sorted(PLACEHOLDERS)))
        require("{" not in harness["command"], "The harness command itself cannot be templated")
        require(any("{brief}" in argument for argument in harness["argv"]), "The harness must receive the brief")
        require(any("{report}" in argument for argument in harness["argv"]), "The harness must write a report")
    resources = [binding["resource_id"] for binding in config["bindings"]]
    require(len(set(resources)) == len(resources), "Duplicate routed resource binding")
    for binding in config["bindings"]:
        require(binding["harness_id"] in set(ids), "Binding names an unknown harness")
        require(binding["credential_env"] is None or ENV_NAME.fullmatch(binding["credential_env"]),
                "A credential must be referenced by environment-variable name only")
        require(binding["api_base"] is None or re.fullmatch(r"https?://[A-Za-z0-9.:_/-]{1,280}", binding["api_base"]),
                "Unsafe API base URL")
    return config


def binding_for(config, routing):
    require(config["enabled"], "Execution harness dispatch is disabled")
    decision = routing["decision"]
    require(decision["status"] == "ROUTED", "Only a routed dispatch can be prepared for a worker")
    resource = decision["selected"]["resource_id"]
    matches = [binding for binding in config["bindings"] if binding["resource_id"] == resource]
    require(len(matches) == 1, f"No harness binding for routed resource {resource}")
    binding = matches[0]
    harness = next(item for item in config["harnesses"] if item["id"] == binding["harness_id"])
    return binding, harness


def routed_resource(router_config, routing):
    identifier = routing["decision"]["selected"]["resource_id"]
    matches = [item for item in router_config["resources"] if item["id"] == identifier]
    require(len(matches) == 1, f"Routed resource {identifier} is not in the router configuration")
    return matches[0]


def bindings_consistent(config, router_config):
    """Refuse a binding that claims more context than its routed resource declares.

    This needs no reservation, so it runs before one is spent: a configuration contradiction
    must not cost a bounded attempt and escalate the task to an architect decision.
    """
    declared = {resource["id"]: int(resource["context_window"]) for resource in router_config["resources"]}
    for binding in config["bindings"]:
        window = binding["served_context_window"]
        limit = declared.get(binding["resource_id"])
        require(window is None or limit is None or int(window) <= limit,
                f"Binding states {window} served context tokens for resource "
                f"{binding['resource_id']}, more than the {limit} it declares")
    return config


def context_estimate(config, harness, binding, resource, request, brief_chars, rules_chars):
    """Estimate whether everything the worker must read fits the window it is actually served.

    The router already checks the architect's declared token estimate against the resource's
    declared window. It cannot check what the harness adds afterwards: the rendered brief, the
    worker rules, and the harness's own system prompt. A local server also serves a model in a
    window it was loaded with, which can be far smaller than the model family's declared window,
    so a binding may state the served window and may never claim more than the resource declares.
    """
    divisor = router.dec(config["limits"]["chars_per_token"])

    def tokens(chars):
        return int((router.dec(chars) / divisor).to_integral_value(rounding=ROUND_CEILING))

    declared = int(resource["context_window"])
    served = binding["served_context_window"]
    window = declared if served is None else int(served)
    require(window <= declared, f"Binding states {window} served context tokens for resource "
                                f"{resource['id']}, more than the {declared} it declares")
    estimate = {"declared_context_window": declared, "served_context_window": window,
                "chars_per_token": config["limits"]["chars_per_token"],
                "harness_overhead_tokens": int(harness["context_overhead_tokens"]),
                "brief_tokens": tokens(brief_chars), "rules_tokens": tokens(rules_chars),
                "reserved_output_tokens": int(request["output_tokens"])}
    estimate["growth_reserve_tokens"] = int(config["limits"]["context_growth_reserve_tokens"])
    estimate["required_tokens"] = sum(estimate[key] for key in
                                      ("harness_overhead_tokens", "brief_tokens", "rules_tokens",
                                       "reserved_output_tokens", "growth_reserve_tokens"))
    estimate["headroom_tokens"] = window - estimate["required_tokens"]
    return estimate


def brief(context, routing, binding, dispatch_id, paths, startup):
    """Render only what the packet already permits, plus the report contract.

    Every path the worker needs is substituted here. A brief that still carries a
    `{placeholder}` forces the worker to guess where to write, which is not its job.
    """
    contract = context["contract"]
    document = {
        "schema_version": "1.1",
        "dispatch_id": dispatch_id,
        "binding": context["binding"],
        "harness": {"resource_id": binding["resource_id"], "provider": binding["provider"],
                    "model": binding["model"], "routed_model": routing["decision"]["selected"]["model"],
                    "tier": routing["decision"]["selected"]["tier"],
                    "reasoning_effort": routing["decision"]["selected"]["reasoning_effort"]},
        "paths": {"workspace": str(paths["workspace"]), "brief": str(paths["brief"]),
                  "rules": str(paths["rules"]), "report": str(paths["report"])},
        "bounds": {"remaining_task_attempts": context["remaining_task_attempts"],
                   "tier_counts": context["tier_counts"], "tier_caps": context["tier_caps"],
                   "controller_status": context["controller_status"]},
        "contract": contract,
        "architect_guidance": context["architect_guidance"],
        "prior_failures": context["recent_failures"],
        "failure_groups": context["failure_groups"],
        "review_rejections": context.get("review_rejections", []),
        "worker_rule": context["worker_rule"],
        "startup": startup,
        "report_contract": {
            "write_to": str(paths["report"]),
            "required_fields": sorted(REPORT_FIELDS),
            "validation_check_fields": check_fields(),
            "outcomes": ["PASS", "FAIL", "BLOCKED", "NEEDS_ESCALATION",
                         "ARCHITECTURE_CONFLICT", "PROVIDER_UNAVAILABLE"],
            "scope_status_values": ["within", "violated", "unknown"],
            "rules": [
                "Write the report at exactly the write_to path; another location is not found and not accepted.",
                "Report exactly these fields as one JSON object; any other field is refused.",
                "dispatch_id must be the value above; a report without it is refused.",
                "Report one validation check per contract validation id, and no other ids.",
                "Each validation check is an object with exactly the fields in validation_check_fields."
                " The contract's validation id goes in check_id, not id. passed is a boolean."
                " failure_code, expected and actual are strings and may be empty. evidence is a list of strings.",
                "outcome is one of outcomes; scope_status is one of scope_status_values.",
                "api_cost_usd is a number and cost_evidence is a string; state them plainly.",
                "Claim PASS only when every check passed and scope_status is within.",
                "Record anything outside this contract as a discovery; never widen scope or edit the contract.",
                "Never include credentials, tokens or private keys in any field.",
            ],
        },
    }
    # Measure and scan the canonical form, but hand the worker an indented file: a line-based
    # reader truncates one very long line, and a worker must not need a workaround to read its brief.
    return document, wp.canonical(document), json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def run_paths(destination):
    """The run-directory layout, defined once for dispatch and the operator launcher."""
    destination = Path(destination)
    return {"rundir": destination, "brief": destination / "brief.json",
            "rules": destination / "BOUNDED_WORKER_RULES.md",
            "report": destination / "report.json", "workspace": destination / "workspace"}


def invocation(harness, binding, paths):
    values = {"provider": binding["provider"], "model": binding["model"],
              "rules": str(paths["rules"]), "brief": str(paths["brief"]),
              "report": str(paths["report"]), "workspace": str(paths["workspace"]),
              "rundir": str(paths["rundir"])}
    argv = [harness["command"]] + [argument.format(**values) for argument in harness["argv"]]
    environment = [binding["credential_env"]] if binding["credential_env"] else []
    return {"argv": argv, "required_environment": environment, "api_base": binding["api_base"],
            "adapter": harness["adapter"], "harness_id": harness["id"]}


def dispatch(directory, config, router_config, request, root, destination):
    """Reserve one bounded attempt and write the worker brief; never run the harness.

    Deliberately no progress reporting (#27): dispatch prepares an invocation and returns;
    it never runs the harness command or waits on a worker, so a "worker running" spinner
    here would be showing progress for something that has not started.
    """
    config_valid(config)
    require(config["enabled"], "Execution harness dispatch is disabled")
    bindings_consistent(config, router_config)
    destination = Path(destination)
    # Refuse a reused run directory before spending anything, but create it only once an
    # attempt actually exists: a refused reservation must not leave a directory that blocks retry.
    if destination.exists():
        raise FileExistsError(f"Run directory already exists: {destination}")
    # Missing or unsafe instructions are knowable before an attempt is spent. Every harness
    # receives the rules through its required {brief}, even one that takes no {rules} path.
    contract = wp.current(feedback.replay(directory)[0]["packet"])["contract"]
    startup = startup_bundle(root, contract, config)
    rules = "".join(startup["rules"]["content_lines"])
    reserved = feedback.reserve(directory, router_config, request, root)
    if reserved["status"] != "DISPATCH":
        return {"status": reserved["status"], "reason": reserved["reason"], "dispatch_id": reserved["dispatch_id"],
                "prepared": False, "destination": str(destination)}
    destination.mkdir(parents=True, exist_ok=False)
    paths = run_paths(destination)
    try:
        binding, harness = binding_for(config, reserved["routing"])
        require(reserved["context"]["contract"] == contract,
                "The contract changed between startup preparation and reservation")
        document, rendered, readable = brief(reserved["context"], reserved["routing"], binding,
                                             reserved["dispatch_id"], paths, startup)
        # Bound and scan the artifact the worker actually receives, not only its canonical form.
        require(max(len(readable), len(rendered)) <= config["limits"]["brief_max_chars"],
                "Brief exceeds its configured bound")
        secret_free(rendered, "Worker brief")
        secret_free(readable, "Worker brief")
        require("{" not in document["report_contract"]["write_to"], "The report path must be substituted")
        # The rules are already inside the brief. Count them again only for a harness told to read
        # the separate rules file as well, because that worker then reads them twice.
        separate_rules = any("{rules}" in argument for argument in harness["argv"])
        estimate = context_estimate(config, harness, binding, routed_resource(router_config, reserved["routing"]),
                                    request, len(readable), len(rules) if separate_rules else 0)
        require(estimate["headroom_tokens"] >= 0,
                f"Brief, rules, harness prompt, reserved output and the declared growth reserve need about "
                f"{estimate['required_tokens']} tokens, but {binding['resource_id']} is served a "
                f"{estimate['served_context_window']}-token window; enlarge the served window, "
                "route a larger resource, or decompose the contract")
    except ValueError as exc:
        # The reservation is already spent, so close it with honest evidence rather than leaving it pending.
        feedback.complete(directory, {
            "dispatch_id": reserved["dispatch_id"], "outcome": "PROVIDER_UNAVAILABLE",
            "summary": "Harness preparation refused; no worker was dispatched and no model was invoked.",
            "scope_status": "unknown", "architecture_conflict": False, "validation": [],
            "evidence": [f"harness-preparation-refused: {exc}"], "discoveries": [],
            "api_cost_usd": 0, "cost_evidence": "No provider call was made; preparation failed first."})
        return {"status": "HARNESS_UNAVAILABLE", "reason": str(exc), "dispatch_id": reserved["dispatch_id"],
                "prepared": False, "attempt_closed": True, "destination": str(destination),
                "executed": False, "execution_authorized": False}
    paths["workspace"].mkdir()
    wp.write_new(paths["brief"], readable)
    wp.write_new(paths["rules"], rules)
    plan = invocation(harness, binding, paths)
    wp.write_new(destination / "invocation.json", json.dumps(plan, indent=2, ensure_ascii=False))
    return {"status": "PREPARED", "reason": reserved["reason"], "dispatch_id": reserved["dispatch_id"],
            "deadline": reserved["deadline"], "prepared": True, "destination": str(destination),
            "invocation": plan, "brief_chars": len(rendered), "context_estimate": estimate,
            "validation_ids": [check["id"] for check in document["contract"]["validation"]],
            "executed": False, "execution_authorized": False}


def report_valid(report, contract, dispatch_id, limits, size):
    require(size <= limits["report_max_bytes"], "Worker report exceeds its configured bound")
    feedback.exact(report, REPORT_FIELDS)
    require(isinstance(report["evidence"], list) and report["evidence"], "A worker report requires evidence")
    # Scan before the schema: a schema error quotes the rejected value, and that message reaches
    # stderr and logs, so credential-like material must be refused before it can be echoed.
    secret_free(report, "Worker report")
    # The controller's own result schema, before any nested field is read: both `ingest` and
    # `verify-report` must refuse a report whose nested types are wrong (`passed: "false"` is truthy).
    feedback.shape("result", report)
    require(report["dispatch_id"] == dispatch_id, "Report does not match the reserved dispatch")
    expected = [check["id"] for check in contract["validation"]]
    reported = [check["check_id"] for check in report["validation"]]
    require(len(set(reported)) == len(reported), "Duplicate validation id in the worker report")
    require(set(reported) == set(expected), "Report every contract validation check and no other id")
    if report["outcome"] == "PASS":
        require(all(check["passed"] for check in report["validation"]), "PASS requires every validation check to pass")
        require(report["scope_status"] == "within", "PASS requires scope_status within")
        require(not report["architecture_conflict"], "An architecture conflict cannot be reported as PASS")
    return report


def ingest(directory, config, report_path):
    """Validate a worker report against its contract, then record it in the task ledger."""
    config_valid(config)
    state = feedback.replay(directory)[0]
    require(state["pending"], "No reserved dispatch is awaiting a report")
    path = Path(report_path)
    # A worker that wrote nothing is a real outcome, but never an inferred one: say so with `abandon`.
    require(path.is_file(), f"No worker report at {path}; record the attempt with abandon instead of inferring it")
    report = wp.read_json(path)
    report_valid(report, wp.current(state["packet"])["contract"], state["pending"],
                 config["limits"], path.stat().st_size)
    recorded = feedback.complete(directory, report)
    return {"status": recorded["status"], "outcome": report["outcome"], "reason": recorded["reason"],
            "dispatch_id": report["dispatch_id"],
            "attempts_used": len(recorded["attempts"]), "remaining_task_attempts": recorded["total_cap"] - len(recorded["attempts"]),
            "evidence_preserved": bool(recorded["attempts"][-1].get("fingerprint")) or report["outcome"] == "PASS",
            "independent_acceptance": False}


def verify_report(config, brief_path, report_path):
    """Validate a worker report against its own brief, without a task ledger.

    Used for an operator-run harness demonstration: it proves the report contract holds
    for a real worker run, and deliberately records nothing and accepts nothing.
    """
    config_valid(config)
    document = wp.read_json(Path(brief_path))
    version = document.get("schema_version") if isinstance(document, dict) else None
    # A 1.0 brief predates the startup block and stays verifiable as a historical artifact.
    feedback.exact(document, LEGACY_BRIEF_FIELDS if version == "1.0" else BRIEF_FIELDS)
    require(version in ("1.0", "1.1"), "Unsupported worker brief schema_version")
    if version == "1.1":
        startup_valid(document["startup"], document["contract"], config)
    path = Path(report_path)
    report = wp.read_json(path)
    report_valid(report, document["contract"], document["dispatch_id"],
                 config["limits"], path.stat().st_size)
    return {"valid": True, "dispatch_id": report["dispatch_id"], "outcome": report["outcome"],
            "scope_status": report["scope_status"],
            "validation_ids": sorted(check["check_id"] for check in report["validation"]),
            "checks_passed": sum(1 for check in report["validation"] if check["passed"]),
            "checks_total": len(report["validation"]), "discoveries": len(report["discoveries"]),
            "recorded_in_ledger": False, "independent_acceptance": False}


def abandon(directory, config, reason):
    """Close a dispatched attempt that produced no usable report, with an explicit recorded reason.

    Absence of a report is never interpreted on its own. The operator states what happened, the
    attempt is recorded as a failure with that evidence and its fingerprint, and the feedback
    controller decides whether the budget allows another attempt or the architect is needed.
    """
    config_valid(config)
    state = feedback.replay(directory)[0]
    require(state["pending"], "No reserved dispatch is awaiting a report")
    text = str(reason).strip()
    require(20 <= len(text) <= 2000, "Abandoning an attempt requires a specific recorded reason")
    secret_free(text, "Abandonment reason")
    recorded = feedback.complete(directory, {
        "dispatch_id": state["pending"], "outcome": "FAIL",
        "summary": "Dispatched worker produced no usable report; the attempt was abandoned with a recorded reason.",
        "scope_status": "unknown", "architecture_conflict": False, "validation": [],
        "evidence": [f"attempt-abandoned: {text}"], "discoveries": [], "api_cost_usd": 0,
        "cost_evidence": "The worker reported no accounting, so no cost is asserted."})
    return {"status": recorded["status"], "outcome": "FAIL", "dispatch_id": state["pending"],
            "attempts_used": len(recorded["attempts"]),
            "remaining_task_attempts": recorded["total_cap"] - len(recorded["attempts"]),
            "fingerprint": recorded["attempts"][-1].get("fingerprint"),
            "evidence_preserved": True, "independent_acceptance": False}


# Every non-PASS report outcome (config/feedback.schema.json) is an adverse worker
# result, not merely an unaccepted one, and a dispatch stopped at one of these
# ledger statuses needs reconciliation or architect action, not "in progress."
_REFUSAL_OUTCOMES = {"FAIL", "BLOCKED", "NEEDS_ESCALATION", "ARCHITECTURE_CONFLICT", "PROVIDER_UNAVAILABLE"}
# feedback.plan() returns only DISPATCH/BLOCKED/NEEDS_ARCHITECT; feedback.reserve() can also
# short-circuit straight to NEEDS_DECISION when the bootstrap approval no longer matches this
# task's anchor (an architect decision is required before any reservation can be attempted).
_REFUSAL_DISPATCH_STATUSES = {"BLOCKED", "NEEDS_ARCHITECT", "NEEDS_DECISION"}


def status_style(command, result):
    """Classify a command's result into a human status kind and an explicit message.

    A prepared reservation, a schema-valid `verify-report`, or an ingested worker
    report is never styled as success: none of them is an independent acceptance
    decision, only the acceptance controller's ledger can report that.
    """
    if command == "abandon":
        return cli_colors.ABANDONED, "attempt closed with a recorded reason; no report was produced"
    if command == "validate-config":
        return cli_colors.SUCCESS, "harness configuration is valid"
    if command == "dispatch":
        status = result.get("status")
        if status == "PREPARED":
            return cli_colors.PENDING, "prepared for an operator-run harness; not executed, not accepted"
        if status == "HARNESS_UNAVAILABLE" or status in _REFUSAL_DISPATCH_STATUSES:
            return cli_colors.REFUSAL, result.get("reason", f"reservation stopped at {status}")
        return cli_colors.PENDING, f"reservation stopped at {status}; nothing was dispatched"
    if command == "ingest":
        timed_out = result.get("reason") == "ATTEMPT_TIMEOUT"
        if timed_out or result.get("outcome") in _REFUSAL_OUTCOMES:
            # A timed-out PASS is recorded as FAIL by feedback.apply_result even though the
            # worker's own report still says PASS; the ledger's reason is the honest signal.
            label = result["reason"] if timed_out else result.get("outcome")
            return cli_colors.REFUSAL, f"worker report recorded as {label}"
        return cli_colors.PENDING, "worker report recorded in the ledger; independent acceptance is separate"
    if command == "verify-report":
        if result.get("outcome") in _REFUSAL_OUTCOMES:
            return cli_colors.REFUSAL, f"report outcome is {result.get('outcome')}, not a passing result"
        return cli_colors.PENDING, "report is schema-valid; this proves the contract holds, it does not accept the work"
    return cli_colors.PENDING, "command completed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-config")
    prepare = commands.add_parser("dispatch")
    prepare.add_argument("ledger", type=Path)
    prepare.add_argument("destination", type=Path)
    prepare.add_argument("--router-config", required=True, type=Path)
    prepare.add_argument("--request", required=True, type=Path)
    take = commands.add_parser("ingest")
    take.add_argument("ledger", type=Path)
    take.add_argument("report", type=Path)
    give_up = commands.add_parser("abandon")
    give_up.add_argument("ledger", type=Path)
    give_up.add_argument("--reason", required=True)
    check = commands.add_parser("verify-report")
    check.add_argument("brief", type=Path)
    check.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        config = wp.read_json(args.config)
        if args.command == "validate-config":
            config_valid(config)
            result = {"valid": True, "harnesses": [item["id"] for item in config["harnesses"]],
                      "enabled": config["enabled"], "credentials_embedded": False}
        elif args.command == "abandon":
            result = abandon(args.ledger, config, args.reason)
        elif args.command == "verify-report":
            result = verify_report(config, args.brief, args.report)
        elif args.command == "dispatch":
            result = dispatch(args.ledger, config, wp.read_json(args.router_config),
                              wp.read_json(args.request), args.root, args.destination)
        else:
            result = ingest(args.ledger, config, args.report)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        kind, message = status_style(args.command, result)
        cli_colors.write_status(kind, f"{args.command}: {message}")
        return 0 if result.get("valid", True) and result.get("status") != "BLOCKED" else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        cli_colors.write_status(cli_colors.REFUSAL, f"Execution harness refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(cli_exit.run(main))
