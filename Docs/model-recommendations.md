# Model recommendations

State: not implemented

## Confirmed intent

Inspect the computer's configuration and help select suitable available models for local coding agents.

Recommendations must remain within the coding-agent scope and support profiles pairing different agents and models.

## Proposed selection criteria for review

- Hardware and runtime compatibility, including usable accelerator memory and system memory.
- Storage requirements and existing model downloads.
- Coding quality and the selected agent's requirements for tool calls, structured output, or edit formats.
- Model quantization, context requirements, runtime overhead, and memory reserved for other applications.
- Responsiveness for the user's intended coding workload.
- The user's preference for speed, quality, or longer context.
- The useful task context remaining after agent overhead, and total task efficiency including retries and compaction. See [Resource efficiency](resource-efficiency.md).

A recommendation should identify a model configuration for a particular agent and computer. A model name alone does not describe the full configuration.

## Proposed evidence and freshness behavior

- Maintain a bounded catalog of supported model configurations with sources and freshness information.
- Distinguish estimated fit or speed from locally measured results.
- Explain why candidates are recommended and identify uncertainty.
- Consider local compatibility checks and benchmarks after download.
- Allow manual selection when the user prefers another supported configuration.
- Refresh recommendation data independently of changing an existing working profile.

## Limits and open decisions

- “Best” is workload-dependent and is not a promise to identify a universal market winner.
- Model weight size alone is insufficient to establish runtime memory requirements.
- Hardware fit alone does not demonstrate reliable behavior with a coding agent.
- Performance or compatibility must not be presented as measured when only estimated.
- Catalog sources, maintenance ownership, ranking method, benchmark design, and cached-catalog freshness rules remain undecided. Recommendations in offline mode must use available local metadata without network refreshes; see [Local inference and offline operation](local-and-offline.md).
- Using an existing hardware recommendation tool is a candidate approach, not an approved dependency.

## Delivery evidence

None. Hardware detection, catalog ingestion, scoring, and validation are not implemented.
