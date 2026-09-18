# Domain Profile — North Carolina Family Law

This is the family-law specialization of the universal autonomous project template: evidence-first
case research and preparation, built so that repetition never converts an allegation into a fact.
`AUTONOMY_CONTROL_PLANE.md` is the controlling workflow policy; the controllers named below are
the mechanism.

## Startup gate

Autonomy is OFF until interactive intake is complete and the user approves the exact package.
`scripts/validate_bootstrap.py` requires, for this profile, a meaningful answer to every domain
orientation field before review or activation: court/county, case number(s), parties and
procedural posture; controlling orders and judgments in effect; ranked objectives, disputed
issues and deadlines; discovery served, received and outstanding; evidence/exhibit sources and
preservation; financial/support inputs; parenting/custody inputs; known adverse facts;
appellate-preservation posture; and standing restrictions/reserved consequential actions. The
architect then presents the case architecture, source map, objective hierarchy, deadlines, and
human-intervention triggers. A placeholder answer is refused, not deferred.

## Case decomposition

Maintain distinct but linked workstreams for docket/procedure, custody/parenting, support/
financial calculations, discovery, enforcement/contempt, evidentiary issues, communications,
conduct issues when legally relevant, appellate preservation, deadlines, and requested relief.
Every packet names exactly one workstream from this list. A packet that spans several is not
independently testable and is decomposed further. `examples/family-law/` is a worked
decomposition.

## Work packet

The common contract is unchanged. For this profile the `domain` block is structural, validated by
`config/domains/family-law.schema.json` and `scripts/family_law.py` wherever a contract is
validated:

- `workstream`: the one linked workstream.
- `fact_assertions`: every material factual claim the packet's output rests on, each declared
  with its category (`ALLEGATION`, `DISPUTED_FACT`, `INFERENCE`, `LEGAL_PROPOSITION`, or
  `UNKNOWN`) and citing a contract source. Empty means the packet asserts no material fact and is
  `NOT_FACT_ASSERTING`.
- `source_references`: contract sources the packet's claims rely on; required when any fact
  assertion exists.
- `adverse_authority`: the strongest authority against the packet's own position, each citing a
  contract source. Required non-empty whenever any assertion is declared `LEGAL_PROPOSITION`.
- `validation_levels`: every validation id mapped to exactly one rung of the ladder.
- `fact_basis`: `UNVERIFIED_FACT` or `NOT_FACT_ASSERTING`. A contract cannot declare
  `VERIFIED_FACT`; it is earned, never authored. The block is closed — no undeclared key and no
  free text can carry that literal anywhere in it.

## Verification ladder

structural → citation_linked → primary_source_verified.

The first two rungs are machine-runnable: each such validation must declare a `command`, and the
acceptance controller's deterministic gate re-executes it in the reviewed workspace (completeness,
cross-reference and citation-linkage checks — the kind of thing a script can verify). The rung
above them must not declare a command: it fails closed to an attestation by a non-implementer
operator who actually read the primary source, and that attestation must bind a structured source
verification record by digest. A primary-source rung with a command is refused as a script
masquerading as a human review; a citation check without one is refused as attestation
substituting for a runnable check. `scripts/family_law.py status` derives the earned fact basis
from the ledger: `VERIFIED_FACT` only for an accepted task whose primary-source rungs were all
attested, every bound record re-verified against the ledger (`--evidence-dir`), every record
supporting the claim, every declared fact assertion covered by a supporting record, and whose
contract does not declare `domain.synthetic: true` — every worked example in this template declares
it, so none of them can earn `VERIFIED_FACT`. A record verifies a claim only if its
`claim_verified` is exactly one of the contract's `fact_assertions`; a record for an unrelated
statement verifies nothing, and one checked claim never verifies a packet's other assertions. A
primary source can also actively contradict the claim it was consulted to check, or be
inconclusive: `status` reports `CONTRADICTED_BY_SOURCE` as its own outcome, ahead of every other
reason, and an inconclusive review is reported unverified with that reason stated — neither is
masked as a generic failure, and neither ever earns `VERIFIED_FACT`. The output names its
`evidence_basis`: without `--evidence-dir` the status rests on the ledger's attestations alone,
which are reported for audit and never earn `VERIFIED_FACT` or a satisfied primary-source rung,
because nothing has compared the bound record's revision, contract hash, submission identity or
claim with the ledger; with `--evidence-dir` every bound record is found by digest, validated, and
re-verified for task, revision, contract hash, submission identity, validation, rung, claim, and
the attesting operator. A ledger stored before these rules existed replays marked with its shortfall
for audit and acceptance status; only new events are refused, and the fact-basis derivation is the
one that refuses.

## Cost posture

Indexing, chronology, deadline arithmetic, citation linkage, and other bounded, deterministic work
route to the local tiers first; objective failures and stakes, never preference, drive escalation.
A packet asserting a disputed allegation or a legal proposition carries elevated risk so the
acceptance floor adds independent model review and, at high stakes, the cross-family gate.
Primary-source reviews are operator actions and are never dispatched to a worker.

## GitHub ledger

Use one tracking issue per major objective and bounded issues for research questions, evidence
gaps, discovery analysis, hearing preparation, and draft work. Issue comments are the
progress/evidence ledger. Material changes to durable project documents move through PRs. New
factual findings become separate issues rather than silently expanding another theory. Primary-
source observations are recorded as bound source verification records and their attestations, not
as prose in a comment.

## Model routing
T0/T1 LM Studio: document organization, metadata normalization, scoped extraction, deterministic calculations, comparison of known fields, chronology support.
T2 Mistral: bounded synthesis and intermediate analysis.
T3 Claude/Codex: substantive legal analysis, contradiction analysis, high-stakes drafting, independent review.
T4 strongest available reasoning model: case architecture, decomposition, adverse-authority review, integration, and strategy-change determination.

High-stakes legal conclusions require primary-source verification and strong-model review.

## Human-intervention gate
Research, drafting, indexing, calculations, comparison, and preparation may proceed autonomously inside the approved case architecture. Stop before filing, serving, sending external communications, contacting a court/party/witness, issuing process, disclosing restricted records, deleting evidence, or taking another consequential external action. Also stop when the architect proposes a material change to case strategy, requested relief, controlling legal theory, forum/jurisdiction posture, or evidence architecture.