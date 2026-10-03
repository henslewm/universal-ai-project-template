#!/usr/bin/env python3
"""North Carolina civil-rights domain rules: claim-by-claim, defendant-by-defendant matrices whose
every cell rests on declared assertions, each verifiable only against a declared primary source.

This module owns nothing the controllers already own. It adds structure to a civil-rights-nc
contract's `domain` block, decides which validations are machine-runnable and which must be
observed by a non-implementer against a primary source, and derives the status each assertion
and the packet's claim have actually earned from the acceptance ledger. It executes nothing and
invokes no model.

The binding chain is made only of declared, hash-bound fields and never of free text: a source
verification record names an `assertion_id`, which must equal the contract's
`validation_targets[validation_id]`; the claim and its defendant reference assertions by id. It
applies the family-law lessons (ADR-060, ADR-067, ADR-068, ADR-069) by construction rather than
by later review rounds.
"""
from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import cli_exit

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    raise SystemExit("Domain tools require: python -m pip install -r requirements-work-packets.txt")

ROOT = Path(__file__).resolve().parent.parent
PROFILE = "civil-rights-nc"
SCHEMA = json.loads((ROOT / "config/domains/civil-rights-nc.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
# The ladder, lowest rung first. structural and citation_linked are reproduced by re-executing a
# declared command; primary_source_verified exists only as a non-implementer's observation of a
# primary source, which no command can reproduce.
LEVELS = tuple(SCHEMA["$defs"]["validation_level"]["enum"])
MACHINE_LEVELS = frozenset(LEVELS[:-1])
SOURCE_LEVELS = frozenset(LEVELS[-1:])
WORKSTREAMS = tuple(SCHEMA["$defs"]["workstream"]["enum"])
# Declared (claim_basis) and earned claim statuses.
UNVERIFIED_CLAIM, VERIFIED_CLAIM, NOT_ASSERTING = "UNVERIFIED_CLAIM", "SOURCE_VERIFIED_CLAIM", "NOT_CLAIM_ASSERTING"
CONTRADICTED = "CONTRADICTED_BY_SOURCE"
# Earned per-assertion statuses.
SOURCE_VERIFIED, UNVERIFIED, INCONCLUSIVE, UNKNOWN = "SOURCE_VERIFIED", "UNVERIFIED", "INCONCLUSIVE", "UNKNOWN"
# The earned "verified" statuses; a contract may carry neither literal anywhere in its block.
EARNED = re.compile(r"\bSOURCE_VERIFIED(?:_CLAIM)?\b")
LP = "LEGAL_PROPOSITION"
# Statuses the profile treats as elevated risk: independent model review is part of their floor.
ELEVATED_STATUSES = frozenset({"DISPUTED_FACT", LP})
# PROFILE.md: high-stakes legal conclusions require strong-model review; T3 is independent review.
MIN_LEGAL_REVIEWER_TIER = 3
# Only primary law can verify a characterization of what the law says.
LEGAL_SOURCE_TYPES = frozenset({"constitutional_provision", "statute", "regulation_or_ordinance",
                                "court_rule", "case_law", "court_order"})
DIGEST_PREFIX = "source-record:sha256="
# Lines a primary_source_verified attestation must carry; each is derived from the bound record.
# dispatch_id and artifact_sha256 bind it to the ledger's current submission at append time;
# validation_id binds it to the check it attests; assertion_id binds it to the one assertion the
# contract says that check verifies, so a record for one assertion cannot be attested for another.
EVIDENCE_KEYS = ("level", "source_type", "citation", "observed_at", "outcome", "operator",
                 "dispatch_id", "artifact_sha256", "validation_id", "assertion_id")


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


def claim_roles(claim, defendants=None) -> dict[str, list[str]]:
    """Every assertion id the claim rests on, mapped to its role(s) in the claim's matrix.

    The keys are R(c): the claim's defendant's identity assertions, its governing and adverse
    authority, element support, threshold defenses, remedies, limitations, justiciability, and any
    adequate-state-remedy or entity-liability analysis. Nothing outside these keys can make or
    break the claim's earned status."""
    roles: dict[str, list[str]] = {}

    def add(refs, role):
        for ref in refs:
            roles.setdefault(ref, []).append(role)

    if defendants is not None and claim["defendant_id"] in defendants:
        add(defendants[claim["defendant_id"]]["assertion_ids"], f"defendant {claim['defendant_id']}")
    add(claim["governing_authority"], "governing_authority")
    for element in claim["elements"]:
        add(element["supported_by"], f"element {element['id']}")
    for defense in claim["threshold_defenses"]:
        add(defense["assertion_ids"], f"threshold_defense {defense['id']}")
    for adverse in claim["adverse_authority"]:
        add([adverse["assertion_id"]], f"adverse_authority {adverse['id']}")
    for index, remedy in enumerate(claim["remedies"]):
        add(remedy["assertion_ids"], f"remedy {index} ({remedy['kind']})")
    add(claim["limitations"]["assertion_ids"], "limitations")
    add(claim["justiciability"]["assertion_ids"], "justiciability")
    for slot in ("adequate_state_remedy", "entity_liability"):
        if slot in claim:
            add(claim[slot]["assertion_ids"], slot)
    return roles


def _duplicate_ids(items, path) -> list[str]:
    seen, errors = {}, []
    for index, item in enumerate(items):
        if item["id"] in seen:
            errors.append(f"{path}/{index}: duplicates the id of {path}/{seen[item['id']]} ({item['id']})")
        seen.setdefault(item["id"], index)
    return errors


def validate_contract_domain(contract: dict) -> list[str]:
    """Cross-field rules over a schema-valid common contract; returns error strings."""
    domain = contract.get("domain")
    errors = _schema_errors("contract_domain", domain)
    # The block is closed by schema, so every string it can carry is enumerable; none may assert
    # a status only the ledger can earn, whichever field it is written into.
    errors.extend(f"{path}: {EARNED.search(text).group(0)} is earned in the acceptance ledger, never authored"
                  for path, text in _strings(domain) if EARNED.search(text))
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

    # Assertions: the only unit a record verifies, bound by id. Text is unique too (ADR-069): two
    # ids for one statement would be the same assertion declared twice.
    errors.extend(_duplicate_ids(domain["assertions"], "assertions"))
    assertions = {}
    for item in domain["assertions"]:
        assertions.setdefault(item["id"], item)
    seen_text = {}
    for index, item in enumerate(domain["assertions"]):
        if item["assertion"] in seen_text:
            errors.append(f"assertions/{index}: duplicates the assertion text of assertions/{seen_text[item['assertion']]}; "
                          "each assertion is declared once, with every source that can verify it in verified_by")
        seen_text.setdefault(item["assertion"], index)
    for index, item in enumerate(domain["assertions"]):
        if item["source_id"] not in sources:
            errors.append(f"assertions/{index}: unknown source {item['source_id']}")
        for source in item["verified_by"]:
            if source not in sources:
                errors.append(f"assertions/{index}/verified_by: unknown source {source}")
        # A legal proposition characterizes one authority, and only reading that authority verifies
        # it: a secondary source listed beside it could otherwise cover it unread (ADR-068, tightened).
        if item["fact_status"] == LP and item["verified_by"] != [item["source_id"]]:
            errors.append(f"assertions/{index}/verified_by: a legal proposition is verified only by its own "
                          f"authority; verified_by must be exactly [{item['source_id']}]")
        # The filing that makes an allegation is its provenance, never its proof.
        if item["fact_status"] == "ALLEGATION" and item["source_id"] in item["verified_by"]:
            errors.append(f"assertions/{index}/verified_by: an allegation cannot be verified by the filing "
                          f"that alleges it ({item['source_id']})")
    for index, item in enumerate(domain["source_references"]):
        if item not in sources:
            errors.append(f"source_references/{index}: unknown source {item}")
    if domain["assertions"] and not domain["source_references"]:
        errors.append("source_references: a packet with assertions must cite the sources they rely on")

    def status_of(ref):
        return assertions[ref]["fact_status"] if ref in assertions else None

    # Defendants: identity and role are themselves sourced, and capacity follows the defendant's kind.
    errors.extend(_duplicate_ids(domain["defendants"], "defendants"))
    defendants = {}
    for item in domain["defendants"]:
        defendants.setdefault(item["id"], item)
    for index, item in enumerate(domain["defendants"]):
        if item["kind"] == "entity" and item["capacities"] != ["entity"]:
            errors.append(f"defendants/{index}/capacities: an entity is analyzed only in entity capacity")
        if item["kind"] == "natural_person" and "entity" in item["capacities"]:
            errors.append(f"defendants/{index}/capacities: a natural person has no entity capacity")
        for ref in item["assertion_ids"]:
            if ref not in assertions:
                errors.append(f"defendants/{index}/assertion_ids: unknown assertion {ref}")

    # Each primary-source check names the one assertion it verifies; the attestation and the bound
    # record must name the same one, so a record can never be applied to an assertion by text.
    source_checks = sorted(v for v, level in levels.items() if level in SOURCE_LEVELS)
    targets = domain["validation_targets"]
    if not domain["assertions"] and source_checks:
        errors.append("validation_levels: a packet with no assertions cannot carry a primary-source check: "
                      + ", ".join(source_checks))
    untargeted, stray = sorted(set(source_checks) - set(targets)), sorted(set(targets) - set(source_checks))
    if untargeted:
        errors.append("validation_targets: every primary_source_verified validation names the assertion it "
                      "verifies; missing: " + ", ".join(untargeted))
    if stray:
        errors.append("validation_targets: names validations that are not primary_source_verified: " + ", ".join(stray))
    for validation_id, target in sorted(targets.items()):
        if target not in assertions:
            errors.append(f"validation_targets/{validation_id}: unknown assertion {target}")
        elif status_of(target) == "UNKNOWN":
            errors.append(f"validation_targets/{validation_id}: {target} is declared UNKNOWN; no record can "
                          "verify an unresolved assertion")
    targeted = set(targets.values())

    for index, claim in enumerate(domain["claims"]):
        at = f"claims/{index}"
        defendant = defendants.get(claim["defendant_id"])
        if defendant is None:
            errors.append(f"{at}/defendant_id: unknown defendant {claim['defendant_id']}")
        elif claim["capacity"] not in defendant["capacities"]:
            errors.append(f"{at}/capacity: {claim['defendant_id']} is not analyzed in {claim['capacity']} capacity")
        for ref in claim_roles(claim):
            if ref not in assertions:
                errors.append(f"{at}: unknown assertion {ref}")
        for field in ("elements", "threshold_defenses", "adverse_authority"):
            errors.extend(_duplicate_ids(claim[field], f"{at}/{field}"))
        element_ids = {element["id"] for element in claim["elements"]}
        for gap_index, gap in enumerate(claim["missing_evidence"]):
            if gap["element_id"] not in element_ids:
                errors.append(f"{at}/missing_evidence/{gap_index}: {gap['element_id']} is not an element of this claim")
        governing = set(claim["governing_authority"])
        adverse = {item["assertion_id"] for item in claim["adverse_authority"]}
        for ref in sorted(governing):
            if ref in assertions and status_of(ref) != LP:
                errors.append(f"{at}/governing_authority: {ref} is not a {LP}")
        for adverse_index, item in enumerate(claim["adverse_authority"]):
            if item["assertion_id"] in assertions and status_of(item["assertion_id"]) != LP:
                errors.append(f"{at}/adverse_authority/{adverse_index}: {item['assertion_id']} is not a {LP}")
        if governing & adverse:
            errors.append(f"{at}: the same proposition cannot be both governing and adverse authority: "
                          + ", ".join(sorted(governing & adverse)))
        # A citation that resolves is not a reading of the authority: every governing and adverse
        # proposition is the target of a primary-source check (ADR-065, applied per authority).
        for ref in sorted(governing | adverse):
            if ref in assertions and ref not in targeted:
                errors.append(f"{at}: authority {ref} must be the target of a primary_source_verified validation")
        for element_index, element in enumerate(claim["elements"]):
            refs = element["supported_by"]
            if all(ref in assertions for ref in refs) and all(status_of(ref) == LP for ref in refs):
                errors.append(f"{at}/elements/{element_index}: an element is tied to evidence; at least one "
                              f"supporting assertion must not be a {LP}")
        slots = [(f"threshold_defenses/{i}", item["assertion_ids"]) for i, item in enumerate(claim["threshold_defenses"])]
        slots += [(name, claim[name]["assertion_ids"])
                  for name in ("limitations", "justiciability", "adequate_state_remedy", "entity_liability")
                  if name in claim]
        for name, refs in slots:
            if all(ref in assertions for ref in refs) and not any(status_of(ref) == LP for ref in refs):
                errors.append(f"{at}/{name}: a legal conclusion needs its legal basis; at least one assertion "
                              f"must be a {LP}")
        # Structural triggers only: what the claim type or capacity requires to be analyzed, never
        # what the analysis concludes.
        if claim["claim_type"] == "NC_CORUM" and "adequate_state_remedy" not in claim:
            errors.append(f"{at}: an NC_CORUM claim must analyze adequate_state_remedy")
        if claim["capacity"] == "entity" and "entity_liability" not in claim:
            errors.append(f"{at}: an entity-capacity claim must state its entity_liability (policy-or-custom) theory")
        for name in ("limitations", "adequate_state_remedy"):
            if (name in claim and claim[name]["posture"] == "undetermined"
                    and not any(status_of(ref) == "UNKNOWN" for ref in claim[name]["assertion_ids"])):
                errors.append(f"{at}/{name}: an undetermined posture must declare what is unknown as an UNKNOWN assertion")

    if domain["claims"] and domain["claim_basis"] != UNVERIFIED_CLAIM:
        errors.append(f"claim_basis: a packet with a claim is {UNVERIFIED_CLAIM} until the ledger earns otherwise")
    if not domain["claims"] and domain["claim_basis"] != NOT_ASSERTING:
        errors.append(f"claim_basis: a packet with no claim is {NOT_ASSERTING}")
    # Elevated risk: a disputed fact or a legal proposition needs independent model review in its
    # acceptance floor, and a legal proposition needs strong-model (tier 3) review.
    statuses = {item["fact_status"] for item in domain["assertions"]}
    elevated = sorted(statuses & ELEVATED_STATUSES)
    if elevated:
        import work_packet as wp  # lazily, as elsewhere in the domain modules
        if "model_review" not in wp.effective_gates(contract):
            errors.append("risk: a packet asserting " + ", ".join(elevated) + " must carry at least medium risk "
                          "(or a review block requiring model_review) so independent model review gates its acceptance")
    if LP in statuses and contract["routing"]["reviewer_tier"] < MIN_LEGAL_REVIEWER_TIER:
        errors.append(f"routing/reviewer_tier: a packet asserting a {LP} requires reviewer tier "
                      f"{MIN_LEGAL_REVIEWER_TIER} or above (strong-model review)")
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
    return [DIGEST_PREFIX + evidence_digest(record)] + [f"{key}={record[key]}" for key in EVIDENCE_KEYS]


def parsed_evidence(lines) -> tuple[str | None, dict]:
    """The digest and the recognized key=value lines of an attestation; see `parsed_evidence_strict`."""
    return parsed_evidence_strict(lines)[:2]


def parsed_evidence_strict(lines) -> tuple[str | None, dict, list[str]]:
    """The digest, the recognized key=value lines, and every other line an attestation carries.

    A recognized key that appears more than once is refused: keeping the first (or last) value
    would let a contradictory line ride along unverified. Every other line is returned so a
    primary-source attestation can refuse it: a line is recognized exactly or not at all.
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

    `attested_at` is the ATTESTATION event's own timestamp and `submitted_at` the ledger's INIT or
    latest RESUBMIT: `observed_at` must fall between them. `dispatch_id` and `artifact_sha256` are
    the ledger's current submission. The attestation's `assertion_id` must be the one the contract
    declares this validation verifies, which is fully determined by the contract, so it is refused
    here at append time rather than only when a record is later re-verified.
    """
    domain = contract["domain"]
    level = domain["validation_levels"].get(attestation["validation_id"])
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
        raise ValueError(f"Source evidence was recorded for {values['validation_id']} but this "
                         f"attestation is for {attestation['validation_id']}")
    target = domain["validation_targets"].get(attestation["validation_id"])
    if values["assertion_id"] != target:
        raise ValueError(f"Source evidence was recorded for assertion {values['assertion_id']} but the "
                         f"contract declares {attestation['validation_id']} verifies {target}")
    if values["outcome"] not in ("supports", "contradicts", "inconclusive"):
        raise ValueError(f"Source evidence carries an unrecognized outcome {values['outcome']!r}")
    # A contradicting or inconclusive review is attested exactly like a supporting one, so the
    # finding is structurally bound to the ledger; `status` classifies it and never lets it verify.
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


# Attested lines compared exactly with the record; the operator is compared case-folded.
EXACT_LINES = ("source_type", "citation", "observed_at", "level", "outcome", "dispatch_id",
               "artifact_sha256", "validation_id", "assertion_id")


def record_problems(record, binding, validation_id, level, attestation, targets, assertions, sources) -> list[str]:
    """Why a digest-matched record does not verify the attestation; empty means it does.

    `targets` is the contract's validation_targets, `assertions` its assertions by id, `sources`
    its declared source ids. A digest proves which bytes were bound; this proves they are a source
    record for this task, revision, contract, submission, check and declared assertion, of a
    declared source, recorded by the attesting operator, saying what the attestation's lines say.
    Whether a verified record also covers its assertion is decided by `covers`."""
    try:
        validate_source_record(record)
    except ValueError as exc:
        return [f"record found by digest is not a valid source verification record ({exc})"]
    problems = []
    if record["task_id"] != binding["task_id"]:
        problems.append(f"record task_id {record['task_id']} is not {binding['task_id']}")
    if record["revision"] != binding["revision"]:
        problems.append(f"record revision {record['revision']} is not the ledger's {binding['revision']}")
    if record["contract_hash"] != binding["contract_hash"]:
        problems.append(f"record contract_hash {record['contract_hash']} is not the ledger's {binding['contract_hash']}")
    if record["dispatch_id"] != binding["dispatch_id"]:
        problems.append(f"record dispatch_id {record['dispatch_id']} is not the ledger's {binding['dispatch_id']}")
    if record["artifact_sha256"] != binding["artifact_sha256"]:
        problems.append(f"record artifact_sha256 {record['artifact_sha256']} is not the ledger's "
                        f"{binding['artifact_sha256']}")
    if record["validation_id"] != validation_id:
        problems.append(f"record validation_id {record['validation_id']} is not {validation_id}")
    if record["level"] != level:
        problems.append(f"record level {record['level']} is not the contract's {level}")
    target = targets.get(validation_id)
    if record["assertion_id"] != target:
        # By id, never by text: the record verifies exactly the assertion the contract says this
        # check verifies, or nothing.
        problems.append(f"record assertion_id {record['assertion_id']} is not {target}, the assertion the "
                        f"contract declares {validation_id} verifies")
    if record["source_id"] not in sources:
        problems.append(f"record source_id {record['source_id']} is not a source the contract declares")
    if (target in assertions and assertions[target]["fact_status"] == LP
            and record["source_type"] not in LEGAL_SOURCE_TYPES):
        problems.append(f"record source_type {record['source_type']} is not primary law; a {LP} is verified "
                        "only by reading the authority it characterizes")
    if record["operator"].strip().casefold() != attestation["operator"].strip().casefold():
        problems.append("record operator is not the attesting operator")
    attested = parsed_evidence(attestation["evidence"])[1]
    for key in EXACT_LINES:
        if attested.get(key) != str(record[key]):
            problems.append(f"attested {key} differs from the record's {key}")
    if attested.get("operator", "").strip().casefold() != record["operator"].strip().casefold():
        problems.append("attested operator differs from the record's operator")
    return problems


def covers(record, assertions) -> bool:
    """A verified record covers its assertion only when the source it reviewed is one the contract
    names as verifying that assertion. A record of another declared source still verifies as a
    record whose outcome counts, but it does not verify the assertion (ADR-068)."""
    item = assertions.get(record["assertion_id"])
    return item is not None and record["source_id"] in item["verified_by"]


def status(ledger, evidence_dir=None) -> dict:
    """Derive what each assertion and the packet's claim have earned; repetition never upgrades it."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import acceptance  # noqa: E402 — lazily, so the domain module never imports the controllers eagerly.
    state = acceptance.replay(ledger)[0]
    binding = state["binding"]
    submission = {**binding, "dispatch_id": state["result"]["dispatch_id"],
                  "artifact_sha256": acceptance.artifact_identity(state["artifact"])}
    if binding["domain_profile"] != PROFILE:
        raise ValueError(f"Ledger profile is {binding['domain_profile']}, not {PROFILE}")
    if state.get("domain_shortfall"):
        raise ValueError("Ledger contract predates the civil-rights-nc domain rules and yields no earned "
                         "status; it replays for audit and acceptance only: " + "; ".join(state["domain_shortfall"]))
    domain = state["contract"]["domain"]
    levels = domain["validation_levels"]
    targets = domain["validation_targets"]
    gate = acceptance.deterministic_status(state)
    assertions = {item["id"]: item for item in domain["assertions"]}
    defendants = {item["id"]: item for item in domain["defendants"]}
    declared_sources = {entry["id"] for entry in state["contract"]["sources"]}
    accepted = state["status"] == "ACCEPTED"
    synthetic = bool(domain.get("synthetic"))
    checks, problems = [], []
    contradicted: dict[str, list[str]] = {}  # assertion id -> checks whose bound source contradicts it
    inconclusive: dict[str, list[str]] = {}
    supported = set()  # assertions a re-verified, covering record found supported
    for check in state["contract"]["validation"]:
        identifier = check["id"]
        entry = {"validation_id": identifier, "level": levels[identifier], "gate": gate[identifier],
                 "machine_runnable": levels[identifier] in MACHINE_LEVELS, "assertion_id": targets.get(identifier),
                 "evidence_digest": None, "evidence_verified": None, "evidence_path": None,
                 "attested_outcome": None, "covers_assertion": None}
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
                # Reported for audit only: it earns nothing unless --evidence-dir re-derives it.
                entry["attested_outcome"] = values.get("outcome")
            if evidence_dir is not None and levels[identifier] in SOURCE_LEVELS:
                path, record, refused = _find_record(Path(evidence_dir), entry["evidence_digest"] or "")
                if record is None:
                    found = [f"{identifier}: no source verification record with the attested digest"
                             + (f" (refused: {'; '.join(refused)})" if refused else "")]
                else:
                    found = [f"{identifier}: {problem}" for problem in
                             record_problems(record, submission, identifier, levels[identifier], attestation,
                                             targets, assertions, declared_sources)]
                    if not found:
                        entry["attested_outcome"] = record["outcome"]
                        entry["covers_assertion"] = covers(record, assertions)
                        if record["outcome"] == "supports" and entry["covers_assertion"]:
                            supported.add(record["assertion_id"])
                entry["evidence_verified"] = not found
                entry["evidence_path"] = str(path) if path else None
                problems.extend(found)
            if levels[identifier] in SOURCE_LEVELS and entry["evidence_verified"] is not False:
                target = targets.get(identifier)
                if entry["attested_outcome"] == "contradicts":
                    contradicted.setdefault(target, []).append(identifier)
                elif entry["attested_outcome"] == "inconclusive":
                    inconclusive.setdefault(target, []).append(identifier)
        checks.append(entry)
    source_ids = [c["validation_id"] for c in checks if not c["machine_runnable"]]
    basis = "record" if evidence_dir is not None else "attestation"
    # A task-wide disqualifier keeps every assertion (and so the claim) from earning a verified
    # status; it never masks a contradiction, which is a finding in its own right (ADR-067).
    if problems:
        disqualifier = "; ".join(problems)
    elif not all(gate[v] == "ATTESTED" for v in source_ids):
        disqualifier = "A primary_source_verified validation lacks an attestation."
    elif synthetic:
        disqualifier = ("The contract declares synthetic: true; every input is fictional and establishes no "
                        "real case fact or legal conclusion, so this profile refuses to derive a verified status.")
    elif basis != "record":
        disqualifier = ("The attested digests were not re-verified against their records (supply "
                        "--evidence-dir); an attestation alone is reported for audit and never earns a verified status.")
    else:
        disqualifier = None

    # Assertion status. Precedence, first match wins: ledger not ACCEPTED -> UNVERIFIED; a check
    # targeting it whose record did not fail verification contradicts it -> CONTRADICTED_BY_SOURCE;
    # declared UNKNOWN -> UNKNOWN; a task-wide disqualifier -> UNVERIFIED; an inconclusive review ->
    # INCONCLUSIVE; a verified, covering, supporting record -> SOURCE_VERIFIED; otherwise UNVERIFIED.
    def assertion_status(identifier):
        item = assertions[identifier]
        if not accepted:
            return UNVERIFIED, f"Acceptance ledger is {state['status']}, not ACCEPTED."
        if identifier in contradicted:
            return CONTRADICTED, "bound primary source contradicts it (" + ", ".join(contradicted[identifier]) + ")"
        if item["fact_status"] == "UNKNOWN":
            return UNKNOWN, "declared UNKNOWN; no record can resolve it into a verified assertion"
        if disqualifier:
            return UNVERIFIED, disqualifier
        if identifier in inconclusive:
            return INCONCLUSIVE, "primary source review was inconclusive (" + ", ".join(inconclusive[identifier]) + ")"
        if identifier in supported:
            return SOURCE_VERIFIED, "a re-verified record from one of its verifying sources supports it"
        if identifier not in targets.values():
            return UNVERIFIED, "no primary_source_verified validation targets it"
        return UNVERIFIED, "no re-verified record from one of its verifying sources supports it"

    earned = {identifier: assertion_status(identifier) for identifier in assertions}
    claims = []
    for claim in domain["claims"]:
        roles = claim_roles(claim, defendants)

        def where(identifier):
            return f"{identifier} ({', '.join(roles[identifier])})"

        contra = [i for i in roles if earned[i][0] == CONTRADICTED]
        unclear = [i for i in roles if earned[i][0] == INCONCLUSIVE]
        unresolved = [i for i in roles if earned[i][0] == UNKNOWN]
        uncovered = [i for i in roles if earned[i][0] != SOURCE_VERIFIED]
        # Claim status. Precedence, first match wins: ledger not ACCEPTED; any assertion the claim
        # rests on contradicted (the matrix misstates a source; named with its role, ahead of every
        # other reason); a task-wide disqualifier; an inconclusive assertion; an UNKNOWN assertion;
        # declared missing evidence; any assertion not SOURCE_VERIFIED; otherwise SOURCE_VERIFIED_CLAIM.
        if not accepted:
            claim_status, reason = UNVERIFIED_CLAIM, f"Acceptance ledger is {state['status']}, not ACCEPTED."
        elif contra:
            claim_status = CONTRADICTED
            reason = "; ".join([f"{where(i)}: a bound primary source contradicts it, so the claim's matrix "
                                "misstates a source" for i in contra] + [f"also: {problem}" for problem in problems])
        elif disqualifier:
            claim_status, reason = UNVERIFIED_CLAIM, disqualifier
        elif unclear:
            claim_status, reason = UNVERIFIED_CLAIM, "; ".join(f"{where(i)}: primary source review was inconclusive"
                                                               for i in unclear)
        elif unresolved:
            claim_status, reason = UNVERIFIED_CLAIM, ("The claim rests on UNKNOWN assertion(s), which no record can "
                                                      "resolve: " + "; ".join(where(i) for i in unresolved))
        elif claim["missing_evidence"]:
            claim_status, reason = UNVERIFIED_CLAIM, ("The claim declares missing evidence: " + "; ".join(
                f"{gap['element_id']}: {gap['description']}" for gap in claim["missing_evidence"]))
        elif uncovered:
            claim_status, reason = UNVERIFIED_CLAIM, ("No re-verified supporting record covers: "
                                                      + "; ".join(where(i) for i in uncovered))
        else:
            claim_status = VERIFIED_CLAIM
            reason = ("Accepted, and every assertion the claim rests on (defendant identity, governing and "
                      "adverse authority, elements, threshold defenses, remedies, limitations, justiciability, "
                      "and any adequate-state-remedy or entity-liability analysis) is supported by a record from "
                      "one of its declared verifying sources, re-verified for this exact submission. This is not "
                      "a merits prediction and does not establish that the element list is complete.")
        claims.append({"claim_id": claim["id"], "defendant_id": claim["defendant_id"], "capacity": claim["capacity"],
                       "claim_type": claim["claim_type"], "claim_status": claim_status, "reason": reason,
                       "assertions": [{"assertion_id": i, "roles": roles[i], "status": earned[i][0]} for i in roles]})
    if claims:
        earned_basis, reason = claims[0]["claim_status"], claims[0]["reason"]
    else:
        earned_basis = NOT_ASSERTING
        reason = ("The contract asserts no claim; each assertion's earned status is reported under assertions."
                  if assertions else "The contract asserts no claim and no assertion.")
    # A primary-source rung counts as satisfied only when its record verified, covers the assertion
    # the check targets, and supports it; for a synthetic contract it never counts.
    satisfied = [c["level"] for c in checks
                 if c["gate"] == "PASSED"
                 or (c["gate"] == "ATTESTED" and c["evidence_verified"] is True and c["covers_assertion"] is True
                     and c["attested_outcome"] == "supports" and not synthetic)]
    highest = max(satisfied, key=LEVELS.index) if satisfied else None
    return {"task_id": binding["task_id"], "revision": binding["revision"], "ledger_status": state["status"],
            "declared_claim_basis": domain["claim_basis"], "earned_claim_basis": earned_basis,
            "evidence_basis": basis, "reason": reason, "workstream": domain["workstream"],
            "highest_level_satisfied": highest, "claims": claims,
            "assertions": [{"assertion_id": i, "fact_status": assertions[i]["fact_status"], "status": s, "reason": r}
                           for i, (s, r) in earned.items()],
            "validations": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate-contract", help="Apply the domain rules to a contract JSON")
    check.add_argument("contract", type=Path)
    evidence = commands.add_parser("source-record",
                                   help="Validate a source verification record and print the attestation lines it binds")
    evidence.add_argument("record", type=Path)
    evidence.add_argument("--validation-id", help="Refuse a record recorded for a different validation")
    derive = commands.add_parser("status", help="Derive the earned assertion and claim statuses from an acceptance ledger")
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
                      "declared_claim_basis": domain["claim_basis"],
                      "claims": [{"claim_id": c["id"], "defendant_id": c["defendant_id"], "capacity": c["capacity"],
                                  "claim_type": c["claim_type"]} for c in domain["claims"]],
                      "validation_levels": domain["validation_levels"],
                      "validation_targets": domain["validation_targets"],
                      "note": "Structure only; no check was executed and nothing is established."}
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
    raise SystemExit(cli_exit.run(main))
