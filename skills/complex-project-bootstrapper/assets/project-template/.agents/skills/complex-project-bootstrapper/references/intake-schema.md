# Intake Schema

Recover verified facts from the repository and authorized sources first. Classify values as verified, proposed default, unresolved, or conflicting. Ask only missing, decision-relevant fields in small related stages. Supplied values are reused; an instruction to skip questions does not supply missing material facts or approve the architecture.

1. Project name and one-sentence outcome.
2. Definition of done, deliverables, and target date/urgency.
3. Canonical profile (`software-hardware`, `family-law`, or `civil-rights-nc`), jurisdiction/version, risk tier, and sensitivity.
4. Authoritative source locations and source-conflict authority.
5. AI clients to support.
6. Connectors and read/write boundary for each.
7. Repeated workflows and output formats.
8. Constraints, exclusions, approval gates, and owner.

Common answer keys include `project_name`, `objective`, `success_criteria`, `deliverables`, `target_date`, `owner`, `risk_tier`, `sensitivity`, `source_locations`, `ai_clients`, `connectors`, `connector_permissions`, `repeatable_workflows`, `output_formats`, `constraints`, and `out_of_scope`. Record source authority and provenance in the durable source records. Avoid secrets and restricted source contents in intake files.

Choose `--profile` explicitly or recover `domain_profile` from supplied intake/the canonical template. For an optional `verified-intake.json`, place orientation under `bootstrap.domain`. The interactive collector prompts only when these common or profile values are missing:

| Profile | Orientation fields under `bootstrap.domain` | Content |
|---|---|---|
| `software-hardware` | `baseline`, `interfaces`, `validation_resources` | Hardware/firmware/software baseline with sources; protocols/interfaces and specifications; simulator/HIL resources, known paths, physical-access limits |
| `family-law` | `posture`, `objectives_and_deadlines`, `evidence` | Court/case posture and orders with sources; ranked objectives, disputed issues and deadlines; evidence/discovery and preservation |
| `civil-rights-nc` | `posture`, `defendants_and_theories`, `evidence_and_remedies` | Forum/procedural history with sources; defendants, roles/capacities and alleged rights; evidence, limitations/accrual posture and remedies |

These are initial orientation requirements. Detailed domain schemas and workflows remain assigned to #9/#10/#11; templates carry snapshots of the existing domain documents.

Run new setup with `python scripts/bootstrap_project.py --interactive --answers verified-intake.json --profile software-hardware --destination ../my-project --no-git`, substituting the selected profile and destination. Omit `--answers` and its filename if absent. A destination must be new/empty or an uninitialized template repository; initialized projects require preservation-oriented retrofit/review instead of rebootstrap.

The generator normalizes common answers into `config/project.json` and creates `config/bootstrap.json` in inactive `INTAKE`. Common `source_locations` become `sources` in the bootstrap package. Optional proposal fields under the answers file's `bootstrap` object seed `architecture`, `risks`, `routing`, `workflow`, `human_gates`, `domain`, and `unresolved`; the architect must complete and verify the resulting package. The CLI collects facts and does not invent component architecture.

In `config/bootstrap.json`, `architecture` contains `summary`, `boundaries`, `milestones`, and `dependencies`. `routing` and `workflow` each require a `policy`; `human_gates`, `risks`, and `unresolved` are string lists. Resolve all architecture blockers so `unresolved` is empty before review. Disclose nonblocking defaults and assumptions in the package, including generated configuration defaults.

`scripts/bootstrap_gate.py review` revokes previous approval, refreshes `configuration` from `config/project.json`, and refreshes `documents` with SHA-256 hashes of `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md`. These fields, plus `domain`, `workflow`, and `unresolved`, are fingerprint-bound along with the common project/architecture fields. Do not handcraft approval metadata or reuse a previous fingerprint after revision.
