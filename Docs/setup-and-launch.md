# Setup and launch

State: partially implemented

## Implemented commands

```sh
loc scan
loc models recommend --agent claude
loc setup daily --model qwen3-coder:30b --dry-run
loc setup daily --model qwen3-coder:30b
loc setup daily --resume
loc runtime start
loc run daily
loc run daily --continue
```

New profiles default to Claude Code with local Ollama. Interactive setup asks for a profile and agent, then offers a fitting Qwen Coder model as the recommended choice. Model recommendations use the requested context and verified installed-model metadata. If no compatible Qwen Coder candidate has a positive memory-fit estimate, the model choice remains explicit. The example tag above is not suitable for every machine.

Noninteractive setup requires a profile name and exact `--model`; `--agent` overrides the Claude default. Existing profiles retain their selected agent/model when resumed. Dry runs inspect without installing, downloading, starting services, or writing profiles.

Setup first discovers existing installations. It reuses working components, leaves ambiguous or damaged installations pending, and obtains only missing components. Official automated routes and manual browser fallback are listed in [Technology candidates](technology-candidates.md). Opening a browser is not success: the user must confirm completion and loc must find the executable.

Setup preserves completed steps, rechecks actual state on every attempt, resumes through the runtime's download mechanism, and marks a profile ready only after model/context configuration succeeds. It does not overwrite a differently configured profile with the same name.

## Command help

Every command supports `--help` and `-h`, including grouped forms such as `loc models recommend -h`, `loc profile export --help`, and `loc self update -h`. Help gives a short purpose, descriptions for all arguments/options, useful defaults, and an example. Group help also explains its available actions. Asking for help exits before reading profile state or running an operation; it does not need installed agents or a running model service.

`loc run -h` describes loc's profile launcher. Arguments after `--` belong to the agent, so `loc run daily -- --help` launches the selected agent to show its help instead.

## Model and runtime behavior

Only local Ollama endpoints are accepted. Missing models are pulled explicitly; existing names are reused. Ollama shares existing content-addressed blobs during pulls and configuration creation. A deterministic configuration alias sets context and sampling without copying weights. Source and resolved digests are recorded.

loc can start the existing Ollama executable when its service is unavailable. It never reinstalls a stopped service or restarts an unrelated running runtime. A loc-started service disables cloud features and limits concurrent/loaded models; these environment settings do not alter an existing shared service.

## Launch behavior

Each launch builds temporary agent configuration and a loopback inference gateway for the selected model. It rejects model/provider overrides in forwarded flags, strips conflicting inherited provider settings, preserves interactive I/O and exit status, and keeps persistent user configuration unchanged.

Agents receive the profile's original model tag, such as `qwen3-coder:30b`, in their model settings and concise identity guidance. The gateway maps that public name to the pinned `loc-*` configuration alias internally. Model discovery and response metadata, including streamed events, expose the original name. Generated text and tool arguments are not rewritten. This preserves context/sampling settings and digest checks without presenting an internal hash as the model's identity.

Launch previews and verification results show the original name as `model` and retain the internal alias as `resolved_model` for diagnostics. Existing profiles need no migration or new model download. A running agent session must be restarted to receive updated configuration; old conversation messages may still contain the former alias.

Agent options can follow `loc run` directly, with or without a profile name: `loc run --dangerously-skip-permissions`, `loc run daily --continue`, and `loc run --effort low` all forward their agent options. The optional positional argument remains a profile name, not a raw model tag. Put it and loc's `--dry-run`, `--offline`, `--json`, `-h`, or `--help` before agent options. Once the first unknown option is encountered, it and every subsequent argument pass through unchanged, so agent option values cannot be mistaken for profiles or loc settings. A positional argument after the profile also starts forwarding.

The explicit `--` separator remains supported and resolves option-name collisions: `loc run daily -- --help` asks the agent for help. Forwarding is specific to `run`; other commands still reject unknown options. Existing model/provider override checks apply to both forms. User-supplied permission options reach the agent, but loc does not enable permission bypasses by default or write them into persistent settings. The verification command allows the narrow disposable editing task described in [Diagnostics and recovery](diagnostics-and-recovery.md).

A profile that is pending, disabled, missing a dependency, or pointing to a changed model cannot launch as ready. Optional `--rtk` requests helper reuse/installation and concise guidance; it does not globally install hooks.

## Limits

Windows/Linux native execution and fresh-machine installation routes still need validation. Unsupported major agent versions fail rather than guessing a schema. Native Windows dependencies such as Git Bash remain agent-specific. Existing personal aliases and scripts are not imported automatically. Full offline support has narrower boundaries than local inference; see [Local inference and offline operation](local-and-offline.md).

## Delivery evidence

Live Claude Code, OpenCode 2, and Aider edits passed on the Mac. Setup idempotence, failure recovery, and previews are tested with isolated runtime and installer fixtures.

Model-name mapping is covered across native Ollama, OpenAI-compatible, and Anthropic-compatible routes, including alias drift, model restrictions, streaming, and preservation of tool payloads. Protocol references: [Ollama streaming](https://docs.ollama.com/api/streaming) and [Anthropic streaming messages](https://platform.claude.com/docs/en/build-with-claude/streaming).
