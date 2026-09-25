# Local inference and offline operation

State: partially implemented

## Local inference

loc accepts loopback HTTP runtime endpoints only. It verifies local weights and completion capability, rejects cloud-marked or remotely hosted models, and pins the resolved model digest. A per-session gateway exposes only the selected model and inference/metadata routes. It blocks management, web-search, alternate models, and runtime redirects; it does not inherit HTTP proxies.

Agent configuration points model roles at that gateway. Unexpected cloud fallback is not configured. Provider/model overrides in launch arguments are rejected. Normal local inference still permits the coding agent's tools to use the network; local model execution is not a promise that every tool is offline.

## Enforced offline mode

```sh
loc run daily --offline
loc doctor daily --verify --offline
```

The current enforced implementation supports Claude Code and Aider on macOS using `sandbox-exec`. It starts a private Ollama process reading the existing weight store, with external networking denied and model-file writes denied. The agent and its children may connect only to the session gateway. No existing runtime is restarted or reconfigured. The private runtime is stopped when the session finishes.

Missing local models or an unknown storage directory fail without downloading. Set `OLLAMA_MODELS` to an existing nonstandard store when necessary. Offline setup, catalog refresh, and updates never silently go online; network-dependent operations remain pending or fail explicitly.

OpenCode offline execution and Windows/Linux offline enforcement are unsupported in this release and fail closed. `sandbox-exec` availability is checked; failure to establish the sandbox is not treated as success.

## Limits

A private runtime can require additional resident memory if another runtime already has the model loaded, even though disk weights are shared. loc does not unload another session's models to free memory. Agent network tools are unavailable in offline mode. Loopback runtime control and internal worker communication remain necessary.

The gateway and OS controls address supported local inference paths. This is not a general adversarial containment system for arbitrary third-party extensions. macOS's sandbox interface is platform-specific and must be revalidated as operating systems change.

Ollama's cloud-disable setting alone does not prove an agent is offline; loc combines runtime configuration with OS restrictions. [Ollama cloud controls](https://docs.ollama.com/faq)

## Delivery evidence

A macOS test verifies that the agent and a child process reach the gateway but cannot connect externally or to unrelated local ports. Both Aider and Claude Code completed live file edits inside the offline environment. Additional agent/platform coverage remains open.
