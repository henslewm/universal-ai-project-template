## Canonical task and contract

<!-- Link the canonical task issue and controlling master issue. Avoid automatic issue-closing keywords until the required acceptance evidence and decision exist. -->

- Canonical task issue:
- Master issue:
- Canonical JSON packet at a specific commit or durable version:
- Packet task_id / current revision / complete contract SHA-256:

<!-- This PR is a review view. The latest validated packet revision is the sole current contract; revise through the architect process and regenerate views when it changes. -->

## Objective

<!-- What outcome does this change achieve? -->

## Scope

<!-- Link the packet's allowed scope, exclusions, interfaces, and architecture boundaries. Describe changed files and behavior; identify any discrepancy requiring an architect revision. -->

## Dependencies and routing

<!-- Link prerequisite task issues/packets, their required revisions and verified completion evidence, plus the applicable routing/feedback records. State none where applicable. -->

## Evidence / sources

<!-- Source IDs, issues, records, or authoritative references relied upon. -->

## Validation

<!-- For each acceptance criterion, link the exact result for the reviewed commit and packet revision: check, expected/actual outcome, evidence location, and remaining gaps. Running a check or claiming PASS is not independent acceptance. -->

- [ ] `python scripts/validate_project.py`
- [ ] Task-specific checks completed
- [ ] Canonical packet and dependency bindings validated for this revision
- [ ] No secrets or unintended sensitive files added
- [ ] Project state / open loops / handoff updated when material

## Independent review and acceptance

<!-- Name the independent reviewer and link the review of the exact commit and packet revision, verified validation results, findings, and their resolution. A worker cannot accept their own work by changing role labels. If review is pending, say so. -->

- Independent reviewer and review evidence:
- Unresolved findings or evidence gaps:
- Verified result and acceptance decision reference, or pending:

<!-- Record ACCEPTED only after the required results have been verified and independent review has passed. A checked box, open PR, green self-reported result, or merge does not itself establish acceptance. Record later merge and verification evidence separately under the applicable lifecycle. This template grants no execution or external-write authority. -->

## Risks and adverse facts

<!-- Known limitations, unresolved contradictions, or rollback concerns. -->

## Next action and owner

<!-- Name the next action, responsible owner, any dependency or required human decision, and the handoff location. Link material architecture-change requests and the controlling approval before work governed by that change proceeds. -->
