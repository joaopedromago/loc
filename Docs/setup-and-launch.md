# Setup and launch

State: not implemented

## Confirmed intent

Use simple CLI commands to set up local coding-agent environments and start the chosen agent/model profile. Setup must accommodate multiple profiles.

Setup should also configure efficient local operation, reducing unnecessary context and tokens while preserving coding quality on machines with limited memory. Specific proposals and their limits live in [Resource efficiency](resource-efficiency.md).

Resumable setup, download and disk estimates, optional dry runs, complete profile verification, runtime status, and diagnostic reports are now confirmed scope. See [Diagnostics and recovery](diagnostics-and-recovery.md). Launch behavior must also respect [Local inference and offline operation](local-and-offline.md) and repository defaults described in [Profiles](profiles.md).

## Confirmed installation requirements

- Automatically identify existing installations for every supported technology and reuse them. Never reinstall an existing component during setup or create a duplicate. See [Dependency detection and reuse](dependency-reuse.md).
- Setup should obtain the required tools and selected models, rather than assume the user has already installed everything.
- Install only components established to be absent, using the CLI where supported. Uncertain detection must leave installation pending rather than treating the component as missing.
- Obtain the selected model through the supported runtime or model download mechanism, reusing an existing compatible artifact without downloading another copy. For example, an Ollama and Qwen profile needs access to both the runtime installation and the chosen Qwen model artifact.
- When an absent component supports manual installation but has no supported CLI installation route, open its official installation or download page in the user's browser.
- Keep setup pending while the user follows the installation instructions. Wait for explicit confirmation that the installation is complete before continuing with dependent setup steps.

The browser fallback is part of the setup experience, not a separate task the user must discover independently. It does not imply support for a component that cannot run on the user's platform.

## Proposed installation completion behavior for review

- Show which component needs installation and what the user should do before returning to the CLI.
- After a CLI installation or the user's confirmation of a manual installation, check that the component is available and usable before marking the step complete.
- Treat browser opening, installer startup, and elapsed time as insufficient evidence of installation success.
- If verification fails, explain what is still missing and allow retry or cancellation without marking the profile ready.
- Continue profile setup after successful verification, reusing components that are already installed.
- If a browser cannot be opened, display the official URL and instructions. Do not silently assume the manual step is complete.

## Proposed setup behavior for review

- Inspect the operating system, hardware, existing dependencies, and available model installations.
- Let the user create one or more profiles and choose an agent and model.
- Offer suitable model recommendations while allowing an explicit compatible selection.
- Offer compatible context and memory settings, explaining their tradeoffs and any shared-runtime effects.
- Explain required installations, configuration changes, and model downloads.
- Preserve unrelated configuration while applying the required installation and model reuse rules.
- Provide a clear explanation when an installation or hardware combination is unsupported.

## Proposed launch behavior for review

- Launch a named profile or the configured default from the current working directory.
- Check that required dependencies, runtime access, and model artifacts are available.
- Preserve the agent's interactive terminal behavior, cancellation, and exit status.
- Forward arguments after `--` to the selected coding agent.
- Keep profile settings scoped to the launched session where the integration supports this.
- Offer diagnostics for missing dependencies, incompatible configuration, and runtime failures.

## Illustrative CLI

Command names and flags are proposals, not an approved interface or an implementation:

```sh
loc setup
loc setup claude-next --agent claude --model qwen3-coder-next
loc setup opencode-qwen --agent opencode --model qwen3.8
loc profiles
loc use claude-next
loc run
loc run opencode-qwen
loc run claude-next -- --continue
loc doctor
```

The model strings above are illustrative. Exact artifacts and agent compatibility must be resolved later.

## Limits and open decisions

- Installation methods, runtime startup behavior, and privilege handling vary across operating systems.
- Supported CLI installation routes and official browser destinations must be established for each component and platform; no installer commands or URLs are selected in this documentation phase.
- Browser fallback covers missing installation automation, not unsupported hardware or operating systems.
- Shell aliases may be optional conveniences; their generation and existing alias migration remain undecided.
- Agent-specific flags cannot be assumed interchangeable.
- The first supported agent set and noninteractive setup behavior remain undecided. A manual installation step requires user action; how noninteractive runs report that requirement remains undecided.
- The manager should preserve the selected agent's permission model; existing personal flags do not establish product defaults.

## Delivery evidence

None. No commands, installers, launchers, or diagnostic checks exist yet.
