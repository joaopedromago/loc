# Resource efficiency

State: not implemented

## Confirmed intent

Setup should configure local coding agents to use less unnecessary information and fewer tokens while aiming for high coding quality on machines with limited memory.

This extends setup beyond installing an agent and downloading a model. The specific techniques below are proposals for review, not approved dependencies or implemented features.

## Proposed success criteria

Optimize for successful coding tasks within the machine's memory and responsiveness limits. Track correctness, total task tokens, elapsed time, and peak memory together. A shorter prompt that causes missed requirements or repeated attempts is not a successful optimization.

Keep three quantities distinct: tokens actually sent to the model, the configured context capacity, and memory occupied by weights, caches, and runtime buffers. Reducing one does not establish a proportional reduction in the others. Larger configured context increases memory requirements in Ollama. [Ollama context documentation](https://docs.ollama.com/context-length)

## Proposed context behavior for review

### Relevant code on demand

- Prefer targeted searches, symbols, and relevant file sections before loading broad repository content.
- Exclude generated artifacts and downloaded dependencies from routine discovery while allowing deliberate inspection when a task requires them.
- Use a bounded repository map where the selected agent and model handle it well.
- Keep source locations available so the agent can expand context before making uncertain edits.
- Start with existing agent search capabilities; an embedding model or vector database is not a required dependency.

Aider already provides repository maps with an adjustable token budget. Its documentation also notes that maps can overwhelm weaker models, so enabling them universally would be inappropriate. [Aider repository maps](https://aider.chat/docs/repomap.html), [Aider FAQ](https://aider.chat/docs/faq.html)

### Compact tool output

- Consider RTK or an equivalent supported integration for repetitive shell, build, and test output.
- Preserve command failures, exit status, relevant diagnostics, and a way to retrieve omitted details.
- Allow raw output for exact-output tasks or unsupported commands.
- Avoid adding another model solely to summarize every command result by default.

RTK filters command output; it does not compress all prompts or model responses. Its reported token savings are estimates, not measurements of total session tokens or RAM savings. [RTK savings documentation](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/resources/savings-explained.md)

### Short instructions and manageable history

- Keep injected instructions concise and load task-specific reference material when needed.
- Preserve user requirements and repository rules instead of discarding them to meet a token target.
- Configure native history compaction and old tool-output pruning where the agent exposes those controls.
- Preserve the current objective, decisions, changed files, relevant failures, and unresolved work in compacted history.
- Request concise explanations while retaining complete code changes and necessary verification.
- Limit optional tool definitions and integrations to what the profile needs, where the agent supports this.

OpenCode documents automatic compaction, old tool-output pruning, and a reserved token buffer. These are examples of existing controls to evaluate; exact settings depend on the installed version. [OpenCode configuration](https://opencode.ai/docs/config/#compaction)

## Proposed memory behavior for review

- Choose model size, weight quantization, and usable context together for the selected coding workload.
- Reserve context capacity for agent instructions, tool definitions, responses, and compaction instead of allocating all capacity to repository content.
- Prefer one loaded model and limited concurrent inference on constrained machines when supported, without terminating unrelated sessions.
- Consider unloading idle models owned by the manager, with the startup-latency tradeoff made visible.
- Evaluate compatible attention and KV-cache settings through the selected runtime. Treat cache quantization separately from weight quantization.
- Preserve memory headroom for the operating system, editor, compiler, tests, and other applications.

Ollama exposes controls for concurrent requests, loaded models, and model retention. It also documents Flash Attention and KV-cache quantization; cache quantization can affect quality and is currently described as a server-wide setting. These controls require compatibility checks and must not be represented as isolated profile settings when they affect a shared server. [Ollama FAQ](https://docs.ollama.com/faq)

## Proposed validation

Compare configurations on representative coding tasks with the same model, agent, and task inputs where practical. Record successful edits, relevant checks, failed tool calls, retries, total input/output tokens, latency, and peak memory when observable.

Label estimates and unavailable measurements explicitly. Account for retrieval, compaction, and retry overhead when assessing savings. Do not claim a universal token-reduction percentage or guaranteed quality improvement.

## Limits and open decisions

- A launcher can configure only the capabilities exposed by its agent and runtime; it cannot guarantee control over all context construction.
- Repository maps, retrieval, compaction, and filtering can omit important information. Preserve access to original files and useful diagnostics.
- A smaller context window must still accommodate the selected agent's overhead and task. Reject combinations that cannot provide a useful working budget.
- Concise response instructions do not reliably control internal reasoning or runtime memory allocation.
- Runtime settings may be global or require restart. Conflict handling and ownership-detection mechanisms remain undecided. Installation ownership tracking is confirmed scope; see [Uninstallation and storage](uninstall-and-storage.md).
- Prompt caching may reduce repeated computation, but it is not equivalent to removing tokens or reducing resident memory.
- Profile controls, default budgets, optional tool integrations, supported agent versions, and evaluation methods remain undecided.
- Efficiency helpers themselves consume resources; their overhead must fit the same constrained environment.

## Delivery evidence

None. No efficiency settings, integrations, measurements, or runtime changes have been implemented. The references above inform proposals only.
