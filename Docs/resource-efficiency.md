# Resource efficiency

State: partially implemented

## Intent

Reduce unnecessary information and token use while preserving useful coding quality on computers with limited memory. Actual prompt tokens, configured context capacity, and resident memory remain distinct measurements.

## Implemented controls

Profiles configure context, output budget, repository-map budget, temperature, and supported sampling overrides. Validation requires working context beyond output/map/agent overhead. Ollama aliases set context without duplicating weight blobs. The inference gateway enforces model identity and native request context/output settings.

Claude Code receives concise additional coding guidance and local model/context settings. OpenCode 1 uses native compaction/pruning; OpenCode 2 uses its own compaction buffer/retained-token schema and bounded tool output. Aider gets a bounded repository map, chat-history limit, local weak/editor models, and explicit model metadata. No extra embedding or summarization model is required.

Instructions favor targeted searches and file sections, preserve repository rules and useful failure information, and retain task state during summaries. Optional `--rtk` reuses or obtains RTK and adds guidance for supported noisy commands. It does not rewrite arbitrary shell commands or install global hooks.

A loc-started runtime limits loaded models and parallel requests. Existing shared runtimes keep their settings; loc does not silently restart them, change global KV-cache quantization, or unload another workload.

## Quick responses and thinking models

Parameter count alone does not predict response latency. A small model can generate a long reasoning trace before answering. On the inspected Mac, `qwen3:4b` resolved to Qwen3-4B-Thinking-2507: its model metadata identified the Thinking finetune and its advertised thinking values were `[true]`. Its entire loaded allocation was on the GPU. Reducing Claude's effort was not a reliable way to disable this model's reasoning. An explicit disabled-thinking API request still produced reasoning as ordinary text during a local check.

For direct responses, create a separate profile with the explicit `qwen3:4b-instruct` tag:

```sh
loc setup fast-instruct --agent claude --model qwen3:4b-instruct
loc run fast-instruct
```

The [Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) describes a model supporting only non-thinking mode. [Ollama's corresponding tag](https://ollama.com/library/qwen3:4b-instruct) uses different weights from the thinking model, so obtaining it can require a download; setup still reuses existing tools and shared layers. Existing profiles remain available. This is a latency-oriented alternative, not a guarantee of better coding quality.

Model loading, prompt processing, repository instructions, tool definitions, and generated answer length also affect latency. Claude's initial prompt can be much larger than a plain Ollama chat request. Keep relevant project instructions; do not replace the agent's system prompt or remove permission controls solely to improve a timing result. Native runtime timing and end-to-end agent timing are different measurements.

For basic coding work, `loc run fast-instruct --tools "Read,Edit,Write,Bash,Glob,Grep"` passes Claude a smaller tool selection. It retains file operations, shell commands, and searches while omitting other built-in tools for that session. It does not grant tool permissions or remove repository instructions. Omit the forwarded option when the complete tool set is needed; configured external integrations can add their own overhead.

## Tradeoffs and limits

A launcher controls only settings exposed by an agent/runtime. Guidance is not a guarantee that an agent always selects minimal context. Repository maps, compaction, and output filtering can omit information; original files remain available.

Larger context increases runtime memory, but fewer visible tokens do not imply proportional RAM savings. KV-cache quantization, Flash Attention tuning, representative quality comparisons, total task token measurement, and peak process-tree memory measurement remain incomplete. No universal efficiency percentage or best-quality claim is made.

References informing the integrations: [Ollama context](https://docs.ollama.com/context-length), [Ollama memory controls](https://docs.ollama.com/faq), [Aider repository maps](https://aider.chat/docs/repomap.html), [OpenCode 2 compaction](https://opencode.ai/v2/docs/compaction), [RTK](https://github.com/rtk-ai/rtk).

## Delivery evidence

Adapter tests check schema-specific settings and budgets. Live agent file edits passed under configured local contexts, including OpenCode with Qwen3.8 at 64K. Those tests establish integration, not comparative efficiency or general coding quality.

On 2026-09-25, isolated Claude Code 2.1.278 sessions on the Apple Silicon Mac compared the same model-identity question at 32K context and low effort:

| Model and tools | Elapsed time in two runs | Input tokens, including cached tokens | Reasoning trace |
| --- | --- | --- | --- |
| Qwen3 4B Thinking, default tools | 25.22 / 36.40 seconds | About 13,500 | Present |
| Qwen3 4B Instruct, default tools | 22.85 / 21.77 seconds | About 14,400 | None |
| Qwen3 4B Instruct, six core tools | 5.49 / 5.54 seconds | About 4,300 | None |

These are end-to-end observations for a simple question in fresh isolated sessions, not a representative coding benchmark. Model residency and partial prompt caching varied; existing interactive conversations, repository instructions, external tools, and longer outputs can take more time. The earlier reported 89-second session was not reproduced under the isolated conditions. All measured sessions completed with one inference request and zero gateway errors. The comparison kept the original profiles and shell settings intact.
