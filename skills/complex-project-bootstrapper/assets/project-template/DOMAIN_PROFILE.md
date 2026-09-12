# Domain Profile — Software + Hardware Interfaces

This is the default/main specialization of the universal autonomous project template.

## Startup gate
Autonomy is OFF until the interactive intake is complete and the user approves the project charter, system architecture, component boundaries, dependency graph, hardware abstraction boundary, test strategy, model-routing policy, first milestone, and human-intervention triggers.

## Decomposition
Prefer components that can be validated independently of physical hardware. Separate protocol encoding/decoding, transport, device abstraction, hardware adapter, configuration, persistence, business logic, UI/API, simulation, telemetry, and deployment where applicable.

Every work packet defines objective, non-goals, allowed components, inputs, outputs, interface/version, dependencies, hardware assumptions and source references, acceptance criteria, deterministic tests, simulator tests, hardware-in-loop requirements, evidence required, model tier/effort, retry budget, escalation path, and architecture boundaries the worker may not alter.

## Validation
Static validation -> unit tests -> contract tests -> simulator/loopback -> integration -> hardware-in-loop -> representative field workflow when required. Never infer hardware success from compilation or simulation alone. Mark capability `UNVERIFIED_ON_HARDWARE` until representative evidence exists.

## GitHub ledger
Each milestone has one tracking issue containing a dependency-ordered wave plan. Each work packet has one issue. New findings become separate issues. PRs link the work packet and include test evidence. Issue comments record attempts, failures, escalation, hardware observations, and final evidence.

## Model routing
T0 LM Studio handles utility work. T1 LM Studio coder handles bounded functions/tests/adapters. T2 Mistral handles moderate reasoning after local failure. T3 Claude/Codex handles difficult implementation, debugging, and independent review. T4 strongest available Claude/OpenAI reasoning model handles architecture, decomposition, integration diagnosis, and architecture-change determination. Objective tests drive correction; loops are bounded.

## Human-intervention gate
Routine implementation, testing, issue/PR updates, model escalation, and bounded refactoring proceed autonomously inside the approved architecture. Stop for user approval before materially changing protocol assumptions, hardware support scope, public interfaces, persistence architecture, security/authentication model, deployment topology, core framework/language, or the hardware abstraction boundary.