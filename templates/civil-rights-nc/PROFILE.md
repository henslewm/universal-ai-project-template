# Domain Profile — North Carolina Civil Rights Litigation

This branch is the North Carolina civil-rights specialization of the universal autonomous project template, including federal civil-rights claims under 42 U.S.C. § 1983 and direct North Carolina constitutional theories associated with Corum and related authority.

## Startup gate
Autonomy is OFF until an interactive intake is completed and the user approves the project charter, defendant/capacity map, claim architecture, forum/jurisdiction posture, source/evidence map, limitations timeline, objective hierarchy, and human-intervention triggers.

## Operating model
Use the repository as durable state. Separate verified facts, allegations, inferences, disputed facts, legal propositions, and unknowns. Preserve original evidence and provenance. Primary legal authority controls over summaries.

## Claim architecture
Maintain separate but linked workstreams for:
- defendant-by-defendant identity and role;
- individual/official/entity capacity analysis;
- federal constitutional rights and §1983 claim elements;
- North Carolina constitutional/Corum theories;
- immunity and other threshold defenses;
- jurisdiction, standing, mootness, and prospective-relief issues;
- limitations/accrual and exhaustion or prerequisite questions where applicable;
- causation, damages, equitable relief, and remedies;
- municipal/entity policy or custom theories where applicable;
- evidence admissibility/authentication;
- procedural history and preservation;
- strongest adverse authority and dismissal risk.

Do not merge distinct defendants or theories into a single broad allegation. Each proposed claim gets an elements/requirements matrix and an evidence map.

## Mechanism (`scripts/civil_rights_nc.py`, issue #11)

The module adds structure to a `civil-rights-nc` contract's `domain` block through the same generic
hooks as the software-hardware and family-law modules; the acceptance controller is unchanged. It
requires each track to be addressed and sourced and never encodes the legal answer. Every worked
example under `examples/civil-rights-nc/` declares `synthetic: true`.

- **One bounded packet per claim, defendant and capacity.** The block holds a `workstream` (one of
  the twelve tracks above), `forum` and `procedural_posture`, `defendants` (identity, role, kind,
  capacities, sourced identity assertions), a flat list of id-bound `assertions`, at most one
  `claim`, and `validation_targets` naming the one assertion each primary-source check verifies.
- **Claim level versus case level.** Immunities and threshold defenses, justiciability, adequate
  state remedy and entity liability vary by defendant, capacity and claim type, so they live on the
  claim. Forum, evidence authentication and procedural history live in the orientation fields and
  their own workstream packets.
- **A claim carries** its governing authority, elements each tied to evidence, missing evidence,
  mandatory threshold defenses and adverse authority, remedies with causation, limitations and
  accrual, and justiciability. `adequate_state_remedy` is required for `NC_CORUM` claims and
  `entity_liability` (policy or custom) for entity capacity; otherwise both are optional.
- **Binding is by declared id, never by text.** A source verification record's `assertion_id` must
  equal the contract's target for its check, and a mismatch is refused when it is appended. A legal
  proposition is verified only by its own authority, read from a primary-law source type; an
  allegation is never verified by the filing that makes it; governing and adverse authority are
  distinct propositions, each read by its own primary-source check.

### Verification ladder

`structural` and `citation_linked` checks declare a command and are re-executed by the
deterministic gate. `primary_source_verified` declares no command: it is a non-implementer's
attestation binding a source verification record by digest, and it is an operator action, never
dispatched to a worker. `status` derives the earned statuses per assertion and per claim from the
ledger with a fixed precedence, and a contradiction names the assertion's role in the matrix.
`SOURCE_VERIFIED_CLAIM` means every assertion the claim rests on was read in a declared verifying
primary source for this exact submission. It is not a prediction on the merits. It is never earned
by a synthetic contract, or from attestations alone (`--evidence-dir` re-verifies each record).

### Known limits

- The material-change human gate above (forum, defendant set, capacity theory, controlling claim
  theory, requested relief, evidence architecture) cannot be mechanized inside a domain module
  without a controller hook. It stays with the bootstrap gates and the architect role.
- Reading a primary source, and every legal conclusion drawn from it, remains a human or
  strong-model act. The module records that the reading was bound and by whom, not that it was right.

## Legal work packet
Each issue states the precise legal question, forum/jurisdiction, defendant and capacity, procedural posture, governing elements/threshold rules, strongest adverse authority, supporting authority, facts/evidence supporting each element, missing evidence, likely defenses, rebuttal issues, requested relief, limitations implications, confidence, and next action.

## GitHub ledger
Use one tracking issue per major litigation objective and bounded issues for each claim/defendant combination, threshold defense, evidence gap, research question, drafting task, and procedural dependency. Issue comments hold source-backed findings and progress. Material changes to durable claim matrices, chronologies, or litigation architecture move through PRs. New factual or legal theories become separate issues.

## Model routing
T0/T1 LM Studio: evidence inventory, chronology, metadata normalization, scoped extraction, cite/index preparation, deterministic comparisons.
T2 Mistral: bounded synthesis and intermediate issue analysis.
T3 Claude/Codex: substantive claim/defense analysis, motion-risk review, contradiction analysis, high-stakes drafting, independent review.
T4 strongest available reasoning model: claim architecture, decomposition, adverse-authority analysis, integration across defendants/theories, and architecture-change determination.

High-stakes legal conclusions require verified primary authority and strong-model review.

## Human-intervention gate
Research, drafting, indexing, calculations, comparison, and preparation may proceed autonomously inside the approved litigation architecture. Stop before filing, serving, sending external communications, contacting a court/party/witness, issuing process, disclosing restricted records, deleting evidence, or another consequential external action. Also stop when the architect proposes a material change to forum, defendant set, capacity theory, controlling claim theory, requested relief, evidence architecture, or other approved litigation architecture.