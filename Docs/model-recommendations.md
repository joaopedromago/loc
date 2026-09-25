# Model recommendations

State: partially implemented

## Delivered behavior

```sh
loc models list
loc models --name
loc models -n
loc models recommend
loc models recommend --agent opencode --preference balanced
loc models recommend --agent aider --preference speed --context 16384
loc models catalog
loc models refresh
```

`loc models --name` and `loc models -n` list only installed model names, one per line, with their exact tags. Both also work with the explicit `list` action. They preserve inventory order and include runtime aliases. An empty inventory prints nothing; adding `--json` returns an array of names. These flags apply only to `list`; other actions reject them before performing work.

Hardware inspection reports OS/architecture, CPU count, memory capacity/availability, disk space, Apple Silicon shared memory, and NVIDIA information when `nvidia-smi` is already available. It does not install a hardware helper merely to inspect the machine.

The preferred setup is Claude Code with a local Qwen Coder model through Ollama, as selected by the user. `loc models recommend` defaults to Claude. It prefers Qwen Coder candidates within the same estimated-fit category, then applies the selected quality/speed heuristic and installed-model reuse preference. A fitting alternative ranks above an oversized Qwen Coder model. Other agents retain their own explicit selection and general model ranking.

Recommendations combine a bounded catalog with the existing Ollama inventory. Entries identify exact tags, estimated artifact size, context, source, tool support, and catalog date. loc reads installed model metadata without loading models or downloading weights. Tool-driven agents exclude entries without demonstrated tool metadata. Existing custom models can be recommended from their runtime metadata; Qwen Coder naming, including versioned custom aliases, identifies the preferred family rather than proving its quality. Installed models with unreadable metadata or hosted-inference redirects are excluded instead of borrowing catalog capability claims.

The ranking reserves OS/application memory headroom and considers weights, a conservative runtime/cache estimate, selected context, coding-oriented catalog priority, and reuse of installed models. Installed tags and named custom variants retain their matching catalog family's priority; capability checks still use the exact installed model. Speed preference favors smaller weights within the fit and preferred-pairing categories. Discrete accelerator fit is reported separately from system RAM; CPU offload may be required.

Interactive setup offers a default model only when a compatible Qwen Coder candidate has a positive memory-fit estimate. Unknown memory or insufficient capacity leaves the model choice explicit. Noninteractive setup requires `--model`; recommendations do not trigger downloads, alter profiles, or switch an existing agent/model.

The bundled catalog is deliberately small. `loc models refresh` explicitly obtains maintained project metadata from GitHub and validates it before replacing the cached catalog. Offline use keeps locally available metadata. A failed refresh does not change working profiles.

## Limits

This is an explainable estimate, not a universal market ranking or a coding benchmark. Weight size alone does not establish runtime memory use. KV caches, architecture, attention implementation, parallelism, and workload can change fit substantially. No inference is run solely to manufacture measured values.

AMD/Intel accelerator capacity, detailed CPU throughput, freshness policy beyond the visible catalog date, and benchmark-driven ranking remain incomplete. Catalog priority is a heuristic and needs ongoing review as models change. Unknown memory or tool information is not represented as measured support.

## Delivery evidence

Ranking/budget behavior is tested with fixtures, including Qwen Coder preference, installed alternatives, low/unknown memory, custom model metadata, explicit overrides, and preservation of existing profiles. Recommendations are also inspected on the Mac's actual inventory. Source model identities used by live integration checks were present locally. [Implementation and verification](implementation-and-testing.md) records their coverage.
