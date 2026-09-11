# Software and Hardware Interface Project Profile

## Mission
Build, debug, validate, and productize software that interacts with physical hardware while minimizing paid-model usage and preventing agent drift, regressions, and unsupported claims of hardware success.

Read `AUTONOMY_CONTROL_PLANE.md` as the controlling workflow policy.

## Interactive setup
Autonomy remains off until setup is approved. Establish the objective and definition of done; repository and known-good baseline; exact hardware models and firmware; interfaces and authoritative manuals; software stack and deployment target; known working and failing paths; test resources; cost/time targets; available model pool; and architecture boundaries requiring user approval.

The architect then presents an architecture diagram, component boundaries, dependency graph, hardware abstraction boundary, test strategy, model-routing policy, first milestone, and stop conditions. Autonomy begins only after approval.

## Decomposition
Prefer components that can be validated independently of physical hardware. Separate protocol encoding/decoding, transport, device abstraction, hardware adapter, configuration, persistence, business logic, UI/API, simulation, telemetry, and deployment where applicable. Hardware-facing components should expose contracts that permit simulation or fixture testing when technically possible.

## Work packet
Every issue states objective, non-goals, allowed components, inputs, outputs, interface/version, dependencies, hardware assumptions and source references, acceptance criteria, deterministic tests, simulator tests, hardware-in-loop requirements, evidence required, model tier/effort, retry budget, escalation path, and architecture boundaries the worker may not alter.

## Validation hierarchy
Static validation -> unit tests -> contract tests -> simulator/loopback -> integration -> hardware-in-loop -> representative field workflow when required. Never infer hardware success from compilation or simulation alone; use `UNVERIFIED_ON_HARDWARE` until representative evidence exists.

## GitHub ledger
Each milestone has one tracking issue containing the dependency-ordered wave plan. Each work packet has one issue. New findings become separate issues. PRs link the work packet and include test evidence. Issue comments record attempts, failures, escalation, hardware observations, and final evidence.

## Architecture-change gate
Stop for user approval before materially changing protocol assumptions, hardware support scope, public interfaces, persistence architecture, security/authentication model, deployment topology, core framework/language, or hardware abstraction boundary. Routine implementation changes remain autonomous.

## Model routing
T0 LM Studio handles utility work. T1 LM Studio coder handles bounded functions/tests/adapters. T2 Mistral handles moderate reasoning after local failure. T3 Claude/Codex handles difficult implementation, debugging, and independent review. T4 strongest available Claude/OpenAI model handles architecture, decomposition, integration diagnosis, and architecture-change determination. Objective tests drive correction; loops are bounded.