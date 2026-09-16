#!/usr/bin/env python3
"""Family-law domain rules: keep alleged and inferred claims distinct from verified fact.

This module owns nothing the controllers already own. It adds structure to a family-law
contract's `domain` block, decides which validations are machine-runnable and which must be
observed by a non-implementer against a primary source, and derives the fact status a task has
actually earned from its acceptance ledger. It executes nothing and invokes no model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    raise SystemExit("Domain tools require: python -m pip install -r requirements-work-packets.txt")

ROOT = Path(__file__).resolve().parent.parent
PROFILE = "family-law"
SCHEMA = json.loads((ROOT / "config/domains/family-law.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
# The ladder, lowest rung first. structural and citation_linked are reproduced by re-executing a
# declared command; primary_source_verified exists only as a non-implementer's observation of a
# primary source, which no command can reproduce.
LEVELS = tuple(SCHEMA["$defs"]["validation_level"]["enum"])
MACHINE_LEVELS = frozenset(LEVELS[:-1])
SOURCE_LEVELS = frozenset(LEVELS[-1:])
WORKSTREAMS = tuple(SCHEMA["$defs"]["workstream"]["enum"])
UNVERIFIED, VERIFIED, NOT_ASSERTING = "UNVERIFIED_FACT", "VERIFIED_FACT", "NOT_FACT_ASSERTING"
CONTRADICTED = "CONTRADICTED_BY_SOURCE"
DIGEST_PREFIX = "source-record:sha256="
# Lines a primary_source_verified attestation must carry; each is derived from the bound record.
# dispatch_id and artifact_sha256 bind the attestation to the ledger's current submission at
# append time, not only when a record is later re-verified. validation_id binds it to the check
# it is attesting: without it, a schema-valid record for one primary-source check could be
# appended unchanged for a different one, since level/source_type/citation/observed_at/outcome/
# operator/dispatch_id/artifact_sha256 can all legitimately match across two checks in the same
# submission (the class the software-hardware profile found only after several review rounds).
EVIDENCE_KEYS = ("level", "source_type", "citation", "observed_at", "outcome", "operator",
                 "dispatch_id", "artifact_sha256", "validation_id")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


FORMATS = FormatChecker()
RFC3339 = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?"
                      r"(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])")


def parse_timestamp(value: str) -> datetime:
    """An RFC 3339 string as a real calendar value; the pattern alone would admit 2026-99-99."""
    if not RFC3339.fullmatch(value):
        raise ValueError(f"not an RFC 3339 timestamp: {value!r}")
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00"))


@FORMATS.checks("date-time", raises=ValueError)
def valid_timestamp(value):
    """An RFC 3339 timestamp that is also a real calendar value; the pattern alone admits 2026-99-99."""
    if not isinstance(value, str):
        return True  # The schema's type rule reports nonstrings.
    parse_timestamp(value)
    return True


def _validator(name):
    return Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{name}"}, format_checker=FORMATS)


def _no_duplicate_keys(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}; a record cannot carry two values for one field")
        seen.add(key)
    return dict(pairs)


def load_record(text: str) -> dict:
    """The one way a source verification record is read from text: a JSON object with no
    duplicate key at any depth. `json.loads` would keep the last of duplicates, resolving a
    contradiction by position instead of refusing it."""
    def no_constants(name):
        raise ValueError(f"{name} is not a JSON value a record may carry")

    value = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=no_constants)
    if not isinstance(value, dict):
        raise ValueError("a source verification record is a JSON object")
    canonical(value)  # an overflowing literal parses to infinity, which no canonical form admits
    return value


def _schema_errors(name, value) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}"
            for e in sorted(_validator(name).iter_errors(value), key=lambda e: str(list(e.absolute_path)))]


def _strings(value, path="domain"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _strings(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _strings(child, f"{path}/{index}")


def validate_contract_domain(contract: dict) -> list[str]:
    """Cross-field rules over a schema-valid common contract; returns error strings."""
    domain = contract.get("domain")
    errors = _schema_errors("contract_domain", domain)
    # The block is closed by schema, so every string it can carry is enumerable; none may assert
    # the status only the ledger can earn, whichever field it is written into.
    errors.extend(f"{path}: {VERIFIED} is earned in the acceptance ledger, never authored"
                  for path, text in _strings(domain) if re.search(rf"\b{VERIFIED}\b", text))
    if errors:
        return errors
    sources = {entry["id"] for entry in contract["sources"]}
    validation_ids = [check["id"] for check in contract["validation"]]
    levels = domain["validation_levels"]
    mapped, declared = set(levels), set(validation_ids)
    if mapped != declared:
        missing, extra = sorted(declared - mapped), sorted(mapped - declared)
        if missing:
            errors.append("validation_levels: every validation needs exactly one rung; unmapped: " + ", ".join(missing))
        if extra:
            errors.append("validation_levels: names validations the contract does not declare: " + ", ".join(extra))
    for check in contract["validation"]:
        level = levels.get(check["id"])
        if level is None:
            continue
        has_command = check.get("command") is not None
        if level in MACHINE_LEVELS and not has_command:
            errors.append(f"validation/{check['id']}: a {level} check must declare a command; "
                          "attestation cannot stand in for a runnable check")
        if level in SOURCE_LEVELS and has_command:
            errors.append(f"validation/{check['id']}: a {level} check must not declare a command; "
                          "a re-executed command is a structural check, not a review of the primary source")
    for index, item in enumerate(domain["fact_assertions"]):
        if item["source_id"] not in sources:
            errors.append(f"fact_assertions/{index}: unknown source {item['source_id']}")
    for index, item in enumerate(domain["source_references"]):
        if item not in sources:
            errors.append(f"source_references/{index}: unknown source {item}")
    for index, item in enumerate(domain.get("adverse_authority", [])):
        if item["source_id"] not in sources:
            errors.append(f"adverse_authority/{index}: unknown source {item['source_id']}")
    fact_asserting = bool(domain["fact_assertions"])
    source_checks = sorted(v for v, level in levels.items() if level in SOURCE_LEVELS)
    if fact_asserting:
        if domain["fact_basis"] != UNVERIFIED:
            errors.append(f"fact_basis: a packet with fact assertions is {UNVERIFIED} until the ledger earns otherwise")
        if not domain["source_references"]:
            errors.append("source_references: a packet with fact assertions must cite the sources those claims rely on")
    else:
        if domain["fact_basis"] != NOT_ASSERTING:
            errors.append(f"fact_basis: a packet with no fact assertions is {NOT_ASSERTING}; "
                          "declare the assertions if a material fact matters")
        if source_checks:
            errors.append("validation_levels: a packet with no fact assertions cannot carry a primary-source check: "
                          + ", ".join(source_checks))
    propositions = [i["assertion"] for i in domain["fact_assertions"] if i["fact_status"] == "LEGAL_PROPOSITION"]
    if propositions and not domain.get("adverse_authority"):
        errors.append("adverse_authority: a packet asserting a legal proposition must cite the strongest "
                      "authority against its own position")
    return errors


def evidence_digest(record: dict) -> str:
    return hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()


def validate_source_record(record: dict) -> dict:
    errors = _schema_errors("source_verification_record", record)
    if errors:
        raise ValueError("source verification record: " + "; ".join(errors))
    canonical(record)
    return record


def evidence_lines(record: dict) -> list[str]:
    """The attestation evidence an operator hands to `acceptance.py attest` for this record."""
    validate_source_record(record)
    values = {"level": record["level"], "source_type": record["source_type"],
              "citation": record["citation"], "observed_at": record["observed_at"],
              "outcome": record["outcome"], "operator": record["operator"],
              "dispatch_id": record["dispatch_id"], "artifact_sha256": record["artifact_sha256"],
              "validation_id": record["validation_id"]}
    return [DIGEST_PREFIX + evidence_digest(record)] + [f"{key}={values[key]}" for key in EVIDENCE_KEYS]


def parsed_evidence(lines) -> tuple[str | None, dict]:
    """The digest and the recognized key=value lines of an attestation; see `parsed_evidence_strict`."""
    return parsed_evidence_strict(lines)[:2]


def parsed_evidence_strict(lines) -> tuple[str | None, dict, list[str]]:
    """The digest, the recognized key=value lines, and every other line an attestation carries.

    A recognized key that appears more than once is refused: keeping the first (or last) value
    would let a contradictory line ride along unverified. Every other line is returned so a
    primary-source attestation can refuse it: a line is recognized exactly or not at all, so
    ` outcome=contradicts` with a leading space is an unrecognized line, never a second outcome.
    """
    digests, values, unrecognized = [], {}, []
    for line in lines:
        if line.startswith(DIGEST_PREFIX):
            digests.append(line[len(DIGEST_PREFIX):])
            continue
        key, separator, value = line.partition("=")
        if separator and key in EVIDENCE_KEYS:
            if key in values:
                raise ValueError(f"Attestation carries more than one {key}= line; each attested line is "
                                 "verified, so a duplicate cannot be resolved by choosing one")
            values[key] = value
        else:
            unrecognized.append(line)
    return (digests[0] if len(digests) == 1 else None), values, unrecognized


def validate_attestation(contract: dict, attestation: dict, attested_at: str,
                         dispatch_id: str, artifact_sha256: str, submitted_at: str) -> None:
    """Refuse a primary-source attestation that does not bind a supporting source record.

    `attested_at` is the ATTESTATION event's own timestamp: an observation cannot be attested
    before it happened, so a declared `observed_at` later than the event that attests it is
    refused, whether or not a source verification record is ever supplied to re-verify it.

    `dispatch_id` and `artifact_sha256` are the ledger's current submission: contract identity
    survives a RESUBMIT unchanged, so without checking these here an operator could re-attest an
    unchanged, rejected record and have it reported VERIFIED_FACT on the attestation basis alone,
    never reaching record_problems's equivalent check.

    `submitted_at` is when the current result and artifact were submitted (the ledger's INIT, or
    its latest RESUBMIT): checking dispatch_id/artifact_sha256 alone still lets a genuinely
    matching record predate the submission it claims to observe, so `observed_at` must fall
    between this lower bound and `attested_at`, the upper bound.
    """
    level = contract["domain"]["validation_levels"].get(attestation["validation_id"])
    if level not in SOURCE_LEVELS:
        return  # A machine rung has a command; the controller already refuses attesting over it.
    broken = [line for line in attestation["evidence"] if "\n" in line or "\r" in line]
    if broken:
        raise ValueError(f"A {level} attestation element is one line; these carry a line break: "
                         + "; ".join(repr(line) for line in broken))
    digest, values, unrecognized = parsed_evidence_strict(attestation["evidence"])
    if digest is None or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError(f"A {level} attestation must carry exactly one {DIGEST_PREFIX}<digest> line "
                         "binding its source verification record")
    if unrecognized:
        raise ValueError(f"A {level} attestation carries only the digest line and the "
                         f"{len(EVIDENCE_KEYS)} lines `source-record` prints for its record; every "
                         "line is verified, so these are refused: " + "; ".join(repr(l) for l in unrecognized))
    missing = [key for key in EVIDENCE_KEYS if not values.get(key, "").strip()]
    if missing:
        raise ValueError(f"A {level} attestation must carry the bound record's " + ", ".join(missing))
    if values["level"] != level:
        raise ValueError(f"Source evidence was recorded at {values['level']} but the contract requires {level}")
    if values["validation_id"] != attestation["validation_id"]:
        # Without this, a schema-valid record for one primary-source check could be appended
        # unchanged for a different check at the same rung -- level, source_type, citation,
        # observed_at, outcome, operator, dispatch_id and artifact_sha256 can all legitimately
        # match across two checks in the same submission.
        raise ValueError(f"Source evidence was recorded for {values['validation_id']} but this "
                         f"attestation is for {attestation['validation_id']}")
    if values["outcome"] not in ("supports", "contradicts", "inconclusive"):
        raise ValueError(f"Source evidence carries an unrecognized outcome {values['outcome']!r}")
    # Unlike a hardware pass/fail, a primary source can legitimately contradict the claim it was
    # consulted to check, or be inconclusive: both are attested exactly like a supporting review,
    # so the finding is structurally bound to the ledger rather than left to unstructured prose.
    # `status` derives CONTRADICTED_BY_SOURCE (or an unverified reason for inconclusive) from the
    # attested outcome; it never lets either upgrade the fact basis to VERIFIED_FACT.
    if values["operator"].strip().casefold() != attestation["operator"].strip().casefold():
        raise ValueError("The attesting operator must be the operator who reviewed the primary source")
    observed = parse_timestamp(values["observed_at"])
    if observed > parse_timestamp(attested_at):
        raise ValueError(f"Source evidence observed_at {values['observed_at']} is after the "
                         f"attestation recording it at {attested_at}; an observation cannot be "
                         "attested before it happens")
    if observed < parse_timestamp(submitted_at):
        raise ValueError(f"Source evidence observed_at {values['observed_at']} is before the "
                         f"current result and artifact were submitted at {submitted_at}; an "
                         "observation of a resubmission cannot predate it")
    if values["dispatch_id"] != dispatch_id:
        raise ValueError(f"Source evidence was recorded for result {values['dispatch_id']} but "
                         f"the ledger's current result is {dispatch_id}; a resubmission clears "
                         "prior attestations and must be observed again")
    if values["artifact_sha256"] != artifact_sha256:
        raise ValueError(f"Source evidence was recorded for artifact {values['artifact_sha256']} "
                         f"but the ledger's current artifact is {artifact_sha256}")


def _find_record(evidence_dir: Path, digest: str):
    """The file whose canonical digest the attestation bound, whatever it contains; verification is
    separate. A file the loader refuses is named rather than skipped, so a contradictory record
    cannot hide behind "no matching record"."""
    refused = []
    for path in sorted(evidence_dir.glob("*.json")):
        try:
            record = load_record(path.read_text(encoding="utf-8-sig"))
            matched = evidence_digest(record) == digest
        except (OSError, ValueError) as exc:
            refused.append(f"{path.name}: {exc}")
            continue
        if matched:
            return path, record, refused
    return None, None, refused


# What a found record must agree with: the ledger binding, the contract, and every line the
# attestation carried. A digest proves the bytes; it does not prove they are a source record.
RECORD_FIELDS = {"source_type": "source_type", "citation": "citation", "observed_at": "observed_at",
                 "operator": "operator", "level": "level", "outcome": "outcome",
                 "dispatch_id": "dispatch_id", "artifact_sha256": "artifact_sha256",
                 "validation_id": "validation_id"}


def record_problems(record, binding, validation_id, level, attestation) -> list[str]:
    """Why a digest-matched record does not verify the attestation; empty means it does."""
    try:
        validate_source_record(record)
    except ValueError as exc:
        return [f"record found by digest is not a valid source verification record ({exc})"]
    problems = []
    if record["task_id"] != binding["task_id"]:
        problems.append(f"record task_id {record['task_id']} is not {binding['task_id']}")
    if record["revision"] != binding["revision"]:
        # A revised contract keeps the same task_id and can keep the same validation_id and rung,
        # so nothing else here would refuse a record made against a different, changed revision.
        problems.append(f"record revision {record['revision']} is not the ledger's {binding['revision']}")
    if record["contract_hash"] != binding["contract_hash"]:
        # Revision numbers are lineage-local: two independently revised variants of the same task
        # can both be "revision 2" with different content, so the exact contract is checked too.
        problems.append(f"record contract_hash {record['contract_hash']} is not the ledger's {binding['contract_hash']}")
    if record["dispatch_id"] != binding["dispatch_id"]:
        # Contract identity does not identify which draft was reviewed: a rejected result can be
        # resubmitted under the same contract and revision, clearing prior attestations, and an
        # unchanged record must not silently re-verify the new one.
        problems.append(f"record dispatch_id {record['dispatch_id']} is not the ledger's {binding['dispatch_id']}")
    if record["artifact_sha256"] != binding["artifact_sha256"]:
        problems.append(f"record artifact_sha256 {record['artifact_sha256']} is not the ledger's "
                         f"{binding['artifact_sha256']}")
    if record["validation_id"] != validation_id:
        problems.append(f"record validation_id {record['validation_id']} is not {validation_id}")
    if record["level"] != level:
        problems.append(f"record level {record['level']} is not the contract's {level}")
    # A record's outcome is not itself a problem: unlike a hardware pass/fail, a primary source
    # can legitimately contradict the claim it was consulted to check, or be inconclusive.
    # `status` reads the outcome to classify the earned finding; it never lets a non-"supports"
    # outcome verify as VERIFIED_FACT regardless of how well everything else here agrees.
    if record["operator"].strip().casefold() != attestation["operator"].strip().casefold():
        problems.append("record operator is not the attesting operator")
    attested = parsed_evidence(attestation["evidence"])[1]
    for key in ("source_type", "citation", "observed_at", "level", "outcome", "dispatch_id",
               "artifact_sha256", "validation_id"):
        # Exact: a citation or source type that differs in case is a different source.
        if attested.get(key) != str(record[RECORD_FIELDS[key]]):
            problems.append(f"attested {key} differs from the record's {RECORD_FIELDS[key]}")
    if attested.get("operator", "").strip().casefold() != record["operator"].strip().casefold():
        problems.append("attested operator differs from the record's operator")
    return problems


def status(ledger, evidence_dir=None) -> dict:
    """Derive the fact basis a task has earned; repetition never upgrades it."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import acceptance  # noqa: E402 — lazily, so the domain module never imports the controllers eagerly.
    state = acceptance.replay(ledger)[0]
    binding = state["binding"]
    # Contract identity alone does not identify which draft was reviewed: a rejected result can
    # be resubmitted under the same contract and revision, so record verification also binds the
    # observation to the submission the ledger currently holds.
    submission = {**binding, "dispatch_id": state["result"]["dispatch_id"],
                  "artifact_sha256": acceptance.artifact_identity(state["artifact"])}
    if binding["domain_profile"] != PROFILE:
        raise ValueError(f"Ledger profile is {binding['domain_profile']}, not {PROFILE}")
    if state.get("domain_shortfall"):
        raise ValueError("Ledger contract predates the family-law domain rules and yields no fact "
                         "status; it replays for audit and acceptance only: " + "; ".join(state["domain_shortfall"]))
    domain = state["contract"]["domain"]
    levels = domain["validation_levels"]
    gate = acceptance.deterministic_status(state)
    checks = []
    problems = []
    contradicted = []
    inconclusive = []
    for check in state["contract"]["validation"]:
        identifier = check["id"]
        entry = {"validation_id": identifier, "level": levels[identifier], "gate": gate[identifier],
                 "machine_runnable": levels[identifier] in MACHINE_LEVELS, "evidence_digest": None,
                 "evidence_verified": None, "evidence_path": None, "attested_outcome": None}
        attestation = state["attestations"].get(identifier)
        if attestation is not None:
            if attestation.get("domain_shortfall"):  # stored before the rule that would refuse it
                entry["evidence_verified"] = False
                problems.append(f"{identifier}: stored attestation fails the current rule: {attestation['domain_shortfall']}")
                checks.append(entry)
                continue
            digest, values = parsed_evidence(attestation["evidence"])
            entry["evidence_digest"] = digest
            if levels[identifier] in SOURCE_LEVELS:
                # The attestation's own declared outcome, trusted at the same level hardware
                # trusts an attested digest: reported as attested, not record-verified, unless
                # --evidence-dir re-derives it from the bound record below.
                entry["attested_outcome"] = values.get("outcome")
            if evidence_dir is not None and levels[identifier] in SOURCE_LEVELS:
                path, record, refused = _find_record(Path(evidence_dir), entry["evidence_digest"] or "")
                # The digest proves which bytes were bound. Verification then requires those bytes to
                # be a valid source verification record for this task, validation and rung, recorded
                # by the attesting operator, and saying exactly what the attestation's lines say -- a
                # matching digest over anything else is not verification. A record's own outcome is
                # not itself a mismatch: a genuine contradiction or inconclusive finding still
                # verifies as the record it is, and is classified below.
                if record is None:
                    found = [f"{identifier}: no source verification record with the attested digest"
                             + (f" (refused: {'; '.join(refused)})" if refused else "")]
                else:
                    found = [f"{identifier}: {problem}" for problem in
                             record_problems(record, submission, identifier, levels[identifier], attestation)]
                    if not found:
                        entry["attested_outcome"] = record["outcome"]
                entry["evidence_verified"] = not found
                entry["evidence_path"] = str(path) if path else None
                problems.extend(found)
            if entry["evidence_verified"] is not False:
                if entry["attested_outcome"] == "contradicts":
                    contradicted.append(identifier)
                elif entry["attested_outcome"] == "inconclusive":
                    inconclusive.append(identifier)
        checks.append(entry)
    source_ids = [c["validation_id"] for c in checks if not c["machine_runnable"]]
    # What the verdict rests on. Without an evidence directory the ledger's attestations are the
    # only stream read: the digests they declare are reported, not re-verified against records.
    basis = "record" if evidence_dir is not None else "attestation"
    if domain["fact_basis"] == NOT_ASSERTING:
        earned, reason = NOT_ASSERTING, "The contract asserts no material fact."
    elif state["status"] != "ACCEPTED":
        earned, reason = UNVERIFIED, f"Acceptance ledger is {state['status']}, not ACCEPTED."
    elif not source_ids:
        earned, reason = UNVERIFIED, "No validation reaches primary_source_verified; machine-runnable checks cannot verify a factual claim."
    elif problems:
        earned, reason = UNVERIFIED, "; ".join(problems)
    elif contradicted:
        # A primary source that contradicts the claim is a material finding in its own right, and
        # is surfaced ahead of every other reason so it can never be read as merely unverified.
        earned, reason = CONTRADICTED, "; ".join(f"{v}: bound source contradicts the claim" for v in contradicted)
    elif inconclusive:
        earned, reason = UNVERIFIED, "; ".join(f"{v}: primary source review was inconclusive" for v in inconclusive)
    elif not all(gate[v] == "ATTESTED" for v in source_ids):
        earned, reason = UNVERIFIED, "A primary_source_verified validation lacks an attestation."
    elif domain.get("synthetic"):
        # synthetic:true declares every input fictional, establishing no real case fact. Checked
        # last, only once nothing else disqualifies the contract, so this refuses the upgrade to
        # VERIFIED_FACT (or the CONTRADICTED_BY_SOURCE finding) specifically -- a genuine mismatch
        # still reports its own reason above -- rather than masking real problems.
        earned, reason = UNVERIFIED, ("The contract declares synthetic: true; every input is fictional and "
                                      "establishes no real case fact, so this profile refuses to derive "
                                      "VERIFIED_FACT for it.")
    else:
        earned = VERIFIED
        reason = ("Accepted with every primary_source_verified validation attested and supporting the claim; "
                  "each attestation's declared outcome and digest are reported as attested, not "
                  "record-verified (no --evidence-dir was supplied)."
                  if basis == "attestation" else
                  "Accepted with every primary_source_verified validation attested, supporting the claim, "
                  "and every bound record re-verified by digest, task, validation, rung and operator.")
    # A primary-source rung counts as satisfied only when its outcome supports the claim; a rung
    # that contradicts, is inconclusive, or whose record did not verify is not satisfied. For a
    # synthetic contract a source rung never counts here either, for the same reason it never
    # earns VERIFIED_FACT above.
    satisfied = [c["level"] for c in checks
                 if c["gate"] == "PASSED"
                 or (c["gate"] == "ATTESTED" and c["evidence_verified"] is not False
                     and c["attested_outcome"] == "supports" and not domain.get("synthetic"))]
    highest = max(satisfied, key=LEVELS.index) if satisfied else None
    return {"task_id": binding["task_id"], "revision": binding["revision"], "ledger_status": state["status"],
            "declared_fact_basis": domain["fact_basis"], "earned_fact_basis": earned,
            "evidence_basis": basis, "reason": reason, "workstream": domain["workstream"],
            "highest_level_satisfied": highest, "validations": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate-contract", help="Apply the domain rules to a contract JSON")
    check.add_argument("contract", type=Path)
    evidence = commands.add_parser("source-record",
                                   help="Validate a source verification record and print the attestation lines it binds")
    evidence.add_argument("record", type=Path)
    evidence.add_argument("--validation-id", help="Refuse a record recorded for a different validation")
    derive = commands.add_parser("status", help="Derive the earned fact basis from an acceptance ledger")
    derive.add_argument("ledger", type=Path)
    derive.add_argument("--evidence-dir", type=Path,
                        help="Re-verify every attested digest against the record files here; without it the "
                             "status rests on the ledger's attestations alone and says so")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-contract":
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import work_packet as wp
            contract = wp.read_json(args.contract)
            errors = wp.validate_contract(contract, PROFILE)
            if errors:
                raise ValueError("; ".join(errors))
            domain = contract["domain"]
            result = {"valid": True, "workstream": domain["workstream"],
                      "declared_fact_basis": domain["fact_basis"],
                      "validation_levels": domain["validation_levels"],
                      "note": "Structure only; no check was executed and no fact is established."}
        elif args.command == "source-record":
            record = load_record(args.record.read_text(encoding="utf-8-sig"))
            validate_source_record(record)
            if args.validation_id and record["validation_id"] != args.validation_id:
                raise ValueError(f"Record is for {record['validation_id']}, not {args.validation_id}")
            result = {"valid": True, "digest": evidence_digest(record), "outcome": record["outcome"],
                      "attest_evidence": evidence_lines(record),
                      "note": "An operator declaration the controller cannot authenticate; the digest binds it."}
        else:
            result = status(args.ledger, args.evidence_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Domain rule refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
