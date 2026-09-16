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
| `software-hardware` | `baseline`, `hardware_identity`, `interfaces`, `specifications`, `environment`, `known_paths`, `validation_resources`, `physical_access`, `architecture_boundaries` | Repository/software baseline with sources; exact hardware models, revisions and firmware; protocols and interfaces with versions; authoritative manuals and datasheets; host, toolchain and deployment environment; known-good and known-failing paths; fixtures, simulators, loopback and HIL resources; physical-access and safety limits; architecture boundaries whose change needs approval (the nine required by `scripts/validate_bootstrap.py`) |
| `family-law` | `case_identity`, `controlling_orders`, `objectives_and_deadlines`, `discovery`, `evidence`, `financial_support`, `parenting_custody`, `adverse_facts`, `appellate_preservation`, `reserved_actions` | Court/county, case number(s), parties and procedural posture; controlling orders/judgments in effect; ranked objectives, disputed issues and deadlines; discovery served/received/outstanding; evidence/exhibit sources and preservation; financial/support inputs; parenting/custody inputs; known adverse facts; appellate preservation posture; standing restrictions and reserved consequential actions |
| `civil-rights-nc` | `posture`, `defendants_and_theories`, `evidence_and_remedies` | Forum/procedural history with sources; defendants, roles/capacities and alleged rights; evidence, limitations/accrual posture and remedies |

These are the orientation requirements `validate_bootstrap.DOMAIN_FIELDS` enforces; a placeholder such as `TBD` is refused before review. The software-hardware set was completed in #9; the family-law set was completed in #10; civil-rights-nc remains assigned to #11.

Run new setup with `python scripts/bootstrap_project.py --interactive --answers verified-intake.json --profile software-hardware --destination ../my-project --no-git`, substituting the selected profile and destination. Omit `--answers` and its filename if absent. A destination must be new/empty or an uninitialized template repository; initialized projects require preservation-oriented retrofit/review instead of rebootstrap.

The generator normalizes common answers into `config/project.json` and creates `config/bootstrap.json` in inactive `INTAKE`. Common `source_locations` become `sources` in the bootstrap package. Optional proposal fields under the answers file's `bootstrap` object seed `architecture`, `risks`, `routing`, `workflow`, `human_gates`, `domain`, and `unresolved`; the architect must complete and verify the resulting package. The CLI collects facts and does not invent component architecture.

In `config/bootstrap.json`, `architecture` contains `summary`, `boundaries`, `milestones`, and `dependencies`. `routing` and `workflow` each require a `policy`; `human_gates`, `risks`, and `unresolved` are string lists. Resolve all architecture blockers so `unresolved` is empty before review. Disclose nonblocking defaults and assumptions in the package, including generated configuration defaults.

`scripts/bootstrap_gate.py review` revokes previous approval, refreshes `configuration` from `config/project.json`, and refreshes `documents` with SHA-256 hashes of `PROJECT_CHARTER.md`, `CONNECTOR_PLAN.md`, `SKILL_PLAN.md`, and `DOMAIN_PROFILE.md`. These fields, plus `domain`, `workflow`, and `unresolved`, are fingerprint-bound along with the common project/architecture fields. Do not handcraft approval metadata or reuse a previous fingerprint after revision.
