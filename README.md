# loc

A CLI for setting up, launching, and maintaining local coding-agent environments.

State: not implemented

The project is in the documentation review phase. There is no installable application or working CLI yet. `loc` is the working project name; command syntax and technical choices remain open.

## Purpose

Local coding setups often spread across shell aliases, environment variables, model settings, and update scripts. loc aims to bring these into named profiles that are easy to configure and use on another computer.

The focus is coding agents. The intended experience covers installing the required tools, choosing models suited to the computer, launching agents inside repositories, and keeping their configurations usable as models change.

## Intended capabilities

- **Multiple profiles:** keep different agent and model combinations available on the same machine.
- **Automatic reuse:** detect existing tools and model artifacts across supported installation channels. Never reinstall an existing component during setup or create a duplicate; leave installation pending if detection is uncertain.
- **Guided installation:** install required agents, runtimes, and selected models through the CLI where supported. Otherwise, open the official installation page and wait for the user to complete installation and confirm.
- **Hardware-aware recommendations:** help select coding models and configurations that suit available hardware and the chosen agent.
- **Efficient local operation:** reduce unnecessary context and token use while aiming for high coding quality within limited memory.
- **Simple launching and maintenance:** start a selected profile and update its models through a small set of commands.
- **Easy loc installation and updates:** provide a straightforward installation route and keep the CLI updated through its original installation channel.
- **Recoverable setup and diagnostics:** preview changes, estimate downloads and disk space, resume interrupted setup, verify profiles, and inspect actual runtime status.
- **Portable daily workflows:** export/import profiles, select repository defaults, and complete profile names in the shell.
- **Explicit local and offline operation:** show inference destinations, prevent unexpected cloud fallback, and provide offline mode for verified combinations.
- **Storage and uninstallation:** show resource ownership and usage, clean selected unused artifacts, and uninstall supported components or loc while accounting for shared dependencies.
- **Cross-platform support:** target Windows, Linux, and macOS. Exact platform and hardware coverage is still undecided.

These are product intentions, not shipped features. [Product scope](Docs/product-scope.md) records the confirmed requirements and boundaries.

## Profiles

A profile combines a coding agent, model, and the settings needed to run them together. For example:

| Profile | Agent | Model family |
| --- | --- | --- |
| `claude-next` | Claude Code | Qwen3-Coder-Next |
| `opencode-qwen` | OpenCode | Qwen3.8 |
| `claude-glm` | Claude Code | GLM-4.7-Flash |

These combinations illustrate the requested experience. Exact model artifacts and compatibility are not yet validated.

Profiles must reuse existing tools and compatible model artifacts. Proposals include a default profile and profile-specific context and launch settings. Settings that affect a shared runtime need separate handling. See [Profiles](Docs/profiles.md).

## Illustrative usage

The following commands are proposals and are not executable in this repository:

```sh
# Create profiles interactively or specify an agent and model
loc setup
loc setup claude-next --agent claude --model qwen3-coder-next
loc setup opencode-qwen --agent opencode --model qwen3.8

# Inspect and launch profiles
loc profiles
loc run claude-next
loc run opencode-qwen

# Check for updates and diagnose the environment
loc update --check
loc update claude-next
loc doctor
```

The model strings are illustrative. Final commands, installation behavior, and update semantics are documented as proposals in [Setup and launch](Docs/setup-and-launch.md) and [Maintenance](Docs/maintenance.md).

## Efficiency and coding quality

The aim is successful coding work within the computer's limits. Candidate techniques include loading relevant code on demand, compacting noisy command output, managing conversation history, and selecting model and context settings together.

Token use, memory consumption, responsiveness, and correctness need to be evaluated together. Lower token counts alone do not demonstrate better results or proportionally lower RAM usage.

Optional RTK integration, repository maps, native agent compaction, and runtime tuning remain proposals. Their tradeoffs and supporting references are recorded in [Resource efficiency](Docs/resource-efficiency.md).

## Documentation and current status

The [documentation index](Docs/README.md) is the source of truth for detailed intent, limits, and implementation states. It links the profile, setup, recommendation, efficiency, maintenance, and platform documents.

Capability documents use `implemented`, `partially implemented`, or `not implemented`. All application capabilities currently remain `not implemented`.

Python is the preferred language candidate, and Ollama is an initial runtime candidate. The implementation language, dependencies, architecture, supported integrations, and delivery sequence have not been selected.

See [Technology candidates](Docs/technology-candidates.md) for the proposed support list and [Dependency detection and reuse](Docs/dependency-reuse.md) for the installation rules that apply to every supported technology.

[Installing and updating loc](Docs/distribution-and-updates.md) describes the proposed GitHub release services and installation/update experience. No installer or published package is available yet.

[Diagnostics and recovery](Docs/diagnostics-and-recovery.md), [Local inference and offline operation](Docs/local-and-offline.md), and [Uninstallation and storage](Docs/uninstall-and-storage.md) describe the newly approved usability and lifecycle scope.

Review the [pending decisions](Docs/review-and-decisions.md) before application planning begins. Repository contributors and coding agents should follow [AGENTS.md](AGENTS.md).
