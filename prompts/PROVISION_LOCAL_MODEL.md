# Local Model Provisioning Prompt

Runs once, during project creation. Not a per-session step.

## Purpose

A project that declares a local resource tier must select that model against the host's measured hardware and the current state of published open-weight models, not against a name copied from an example configuration. This prompt selects a candidate, proves it fits, compares it honestly to the cheapest authorized cloud tier, and proposes it into the architecture package for approval. It downloads nothing before that approval.

## When this runs

Execute during `ARCHITECTING`, after intake has established whether the project declares a local tier at all, and only when every condition holds:

- the approved domain profile authorizes a tier-0 or tier-1 local resource;
- `evidence/processed/local-model-provisioning.json` does not already exist;
- the host exposes a local inference runtime (LM Studio, Ollama, llama.cpp) the eventual executor can reach.

If `evidence/processed/local-model-provisioning.json` exists, stop and report the recorded selection. Re-provisioning is a deliberate operator action, never an automatic refresh, and never a session-start step. If the project declares no local tier, skip this prompt entirely and record nothing.

## Stage 1 — Measure the host

Do not infer hardware. Read it. Record total VRAM, total system RAM, GPU model, and the free space and media type of the volume holding the model directory. Treat VRAM as the binding constraint: the usable budget is total VRAM less approximately 1 GB for display, and weights plus KV cache must fit inside it for a resource to qualify as GPU-resident. A candidate that does not fit is not disqualified, but it must be scored at its real offloaded speed, not its nominal parameter count.

## Stage 2 — Enumerate current candidates

Query the Hugging Face API for the twenty most recently published abliterated models, newest first:

```
https://huggingface.co/api/models?search=abliterated&sort=createdAt&direction=-1&limit=20
https://huggingface.co/api/models?search=abliterated&filter=gguf&sort=createdAt&direction=-1&limit=20
```

Record each candidate's repository ID, creation date, base model, parameter count, dense or mixture-of-experts architecture, active parameter count where applicable, and available quantizations with their file sizes. Recency is a search key, not a merit: a model published yesterday has no track record and no independent evaluation.

## Stage 3 — Eliminate on fit

Discard any candidate whose smallest acceptable quantization exceeds the measured system RAM, and any base model that is not instruction-tuned — a base model cannot follow a work-packet contract or emit conformant structured output, whatever its benchmark scores. Prefer a mixture-of-experts candidate whose active parameter count is small over a dense candidate of the same total size: partial offload costs far less on sparse activation, and the dense-model speed rules do not apply to it.

## Stage 4 — Verify the abliteration, not just the model

Abliteration methods are not equivalent and the most prolific publishers are not the most reliable. For each surviving candidate, establish which method was applied and what independent evaluation exists for that method at that parameter scale. Reject any candidate whose method is reported to retain a substantial share of refusals at its size — a download that still refuses is a wasted download — and any candidate whose method shows KL divergence outside the normal range against its base. Treat capability figures published by the abliterating party as claims to be tested, not results. Expect measurable capability loss in every case, and expect it to grow with model size.

## Stage 5 — Compare against the cheap cloud tier before concluding

A local resource earns its place on total cost per accepted result, which is the master objective, not on token price. Run one identical bounded packet through the selected candidate and through the cheapest authorized cloud tier. Record wall-clock time, iteration count, operator attention required, and whether the result was objectively accepted. If the cloud tier wins, say so plainly in the proposal and recommend against the local tier for that class of packet. A finding that the local tier loses is a finding about the plan, not a failure of provisioning.

## Stage 6 — Propose, do not install

Add the selection to the reviewable architecture package as a proposed resource: repository ID, exact quantization filename, upstream revision SHA, measured fit, abliteration method and its provenance, the Stage 5 comparison, and the download size. The proposal must state which tier the resource serves and must not place an abliterated model in a tier whose contract requires schema-conformant output; structured-output tiers take the official instruction-tuned build of the same base. Approval of the architecture package is the authority to download. There is no separate approval, and no download occurs in `AWAITING_APPROVAL`.

## Stage 7 — Install and pin

After the package reaches `ACTIVE`, download the exact quantization at the exact recorded revision. Verify the downloaded file's checksum against the upstream file record and confirm the runtime loads it. Write the resource into the routing configuration under an ID that encodes the model and the quantization, so that a later change of either produces a new ID rather than silently inheriting the prior ID's recorded observations. Never edit an existing resource ID in place to point at different weights.

## Stage 8 — Record

Write `evidence/processed/local-model-provisioning.json` containing the measured hardware, the full candidate list as retrieved with its retrieval timestamp, every elimination and its reason, the Stage 5 comparison, the approved selection with revision SHA and checksum, and the resulting resource ID. This record is the reason this prompt does not run again. Record it in `SOURCE_INDEX.md` with its location, date and checksum as `evidence/README.md` requires, and reference it from the architecture package and from the issue comment that closes provisioning.

## Prohibitions

Do not download before package approval. Do not substitute a different quantization or revision than the one approved. Do not replace or repoint an existing enabled resource. Do not treat a model card's self-reported benchmarks as verification. Do not run this prompt at session start, on branch switch, or as part of routine validation. Do not write model files into the repository working tree, and do not commit weights or quantization artifacts. Neither credentials nor tokens belong in this record.
