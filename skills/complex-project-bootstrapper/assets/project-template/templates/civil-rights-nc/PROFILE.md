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