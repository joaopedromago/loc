# Local inference and offline operation

State: not implemented

## Confirmed scope

The user approved explicit local inference and offline behavior, visible request destinations, and prevention of unexpected cloud fallback.

Local inference means that model execution happens on the selected local runtime. Full offline operation also restricts network use by loc, the selected agent, the runtime, and their tools. Local process communication remains necessary and is distinct from external network access.

## Local inference behavior

- Show the configured runtime destination and model identity so the user can inspect where inference requests are directed.
- Configure supported agent and runtime controls to use the selected local model.
- Never substitute a cloud model when the local model is unavailable, too slow, or unable to fit in memory.
- Report conflicting provider configuration or an unverifiable destination before claiming that a profile uses local inference.
- Keep intentional downloads, update checks, and agent network tools distinguishable from model inference traffic.

## Offline behavior

- Provide an explicit offline mode for supported combinations of agents, runtimes, and operating systems.
- Reuse installed dependencies, downloaded models, and locally available metadata.
- Do not perform external update checks, downloads, catalog refreshes, telemetry, or automatic browser installation steps while offline mode is active.
- Configure or restrict the selected agent's and runtime's external network capabilities, including tools and child processes, to the extent required for the promised offline behavior.
- If a required dependency or artifact is unavailable locally, identify it and leave that operation pending rather than silently going online.
- If the combination cannot provide verified offline behavior, report it as unsupported. Do not label a profile fully offline solely because its model endpoint is local.

## Integration constraints

Some provider controls affect an entire shared runtime. Applying an offline profile must account for other sessions and must not silently restart or reconfigure unrelated workloads.

Ollama documents a setting to disable its cloud models and web search. That control is useful evidence for a runtime integration, but does not establish that the selected coding agent or its subprocesses cannot access the network. [Ollama cloud controls](https://docs.ollama.com/faq)

## Illustrative command

The syntax is proposed and not implemented:

```sh
loc run claude-next --offline
```

## Limits and open decisions

- Supported enforcement and verification mechanisms depend on the platform and agent. No mechanism has been selected.
- Provider redirects, external endpoints, inherited settings, and agent startup behavior need to be included in compatibility checks.
- Network-dependent coding tasks may be unavailable offline; the limitation must be explicit rather than hidden by an online fallback.
- This scope does not introduce hosted inference or multi-machine inference as product features.

## Delivery evidence

None. Local-destination verification, cloud-fallback prevention, and offline enforcement are not implemented.
