# Architected task issue view

Generate this view from the canonical work-packet JSON; do not maintain a second handwritten contract here.

1. Follow `WORK_PACKET_PROTOCOL.md` and prepare a complete contract using a relevant example under `examples/work-packets/`.
2. Record it with `python scripts/work_packet.py create`.
3. Validate the packet and its complete dependency graph.
4. Generate the GitHub issue body with `python scripts/work_packet.py render <packet.json> --output <new-issue.md>`.
5. Retain the packet JSON as the authority. GitHub publication and execution require their applicable project permissions and gates.

The generated view includes the task identity, profile, version/hash, current contract fields, revision provenance and latest recorded event. See the protocol for commands, state transitions and the distinction between recorded metadata and independently verified outcomes.
