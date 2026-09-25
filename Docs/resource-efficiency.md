# Resource efficiency

State: partially implemented

## Intent

Reduce unnecessary information and token use while preserving useful coding quality on computers with limited memory. Actual prompt tokens, configured context capacity, and resident memory remain distinct measurements.

## Implemented controls

Profiles configure context, output budget, repository-map budget, temperature, and supported sampling overrides. Validation requires working context beyond output/map/agent overhead. Ollama aliases set context without duplicating weight blobs. The inference gateway enforces model identity and native request context/output settings.

Claude Code receives concise additional coding guidance and local model/context settings. OpenCode 1 uses native compaction/pruning; OpenCode 2 uses its own compaction buffer/retained-token schema and bounded tool output. Aider gets a bounded repository map, chat-history limit, local weak/editor models, and explicit model metadata. No extra embedding or summarization model is required.

Instructions favor targeted searches and file sections, preserve repository rules and useful failure information, and retain task state during summaries. Optional `--rtk` reuses or obtains RTK and adds guidance for supported noisy commands. It does not rewrite arbitrary shell commands or install global hooks.

A loc-started runtime limits loaded models and parallel requests. Existing shared runtimes keep their settings; loc does not silently restart them, change global KV-cache quantization, or unload another workload.

## Tradeoffs and limits

A launcher controls only settings exposed by an agent/runtime. Guidance is not a guarantee that an agent always selects minimal context. Repository maps, compaction, and output filtering can omit information; original files remain available.

Larger context increases runtime memory, but fewer visible tokens do not imply proportional RAM savings. KV-cache quantization, Flash Attention tuning, representative quality comparisons, total task token measurement, and peak process-tree memory measurement remain incomplete. No universal efficiency percentage or best-quality claim is made.

References informing the integrations: [Ollama context](https://docs.ollama.com/context-length), [Ollama memory controls](https://docs.ollama.com/faq), [Aider repository maps](https://aider.chat/docs/repomap.html), [OpenCode 2 compaction](https://opencode.ai/v2/docs/compaction), [RTK](https://github.com/rtk-ai/rtk).

## Delivery evidence

Adapter tests check schema-specific settings and budgets. Live agent file edits passed under configured local contexts, including OpenCode with Qwen3.8 at 64K. Those tests establish integration, not comparative efficiency or general coding quality.
