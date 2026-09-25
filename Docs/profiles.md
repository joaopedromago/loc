# Profiles

State: not implemented

## Confirmed intent

Multiple profiles are a core requirement. A user must be able to keep combinations such as Claude Code with Qwen3-Coder-Next and OpenCode with Qwen3.8 on the same computer.

A profile represents a selected coding agent and model, together with the configuration needed to run that combination.

The user also wants setup to configure efficient local operation. Proposed context and memory behavior is documented in [Resource efficiency](resource-efficiency.md).

Creating additional profiles must reuse existing tools and compatible model artifacts without duplicate installations or downloads. This is a confirmed requirement; see [Dependency detection and reuse](dependency-reuse.md).

The user also approved portable profile export/import, repository-specific default profiles, and shell completion.

## Portability

- Export enough profile information to reproduce the intended agent/model configuration, including resolved model identity and relevant settings where available.
- Exclude credentials, machine-specific paths, repository content, and model weights from portable exports.
- On import, detect existing dependencies and artifacts before obtaining anything, and recheck the destination computer's compatibility and memory constraints.
- Report unavailable artifacts, incompatible settings, or conflicting profile names rather than silently replacing the requested model or an existing profile.
- Keep imported profile data declarative. Importing a profile must not execute bundled scripts or treat arbitrary supplied commands as setup instructions.

The export format, versioning, and conflict-resolution interface remain undecided. Portability does not guarantee identical performance on different hardware.

## Project defaults and shell completion

Allow a repository to select its default profile so that launching loc from that project can use the appropriate coding environment. Selecting a project default must not replace the defaults for unrelated repositories.

Provide shell completion for supported commands, profile names, and relevant options. Completion should not download models, start inference, or modify profiles.

Proposed default precedence is an explicit CLI profile, then the repository default, then a user-wide default. Exact configuration locations, trust handling for repository-provided settings, supported shells, and completion installation behavior remain undecided. Reading a repository default must not execute arbitrary repository content.

## Illustrative profiles

| Profile name | Coding agent | Model family |
| --- | --- | --- |
| `claude-next` | Claude Code | Qwen3-Coder-Next |
| `opencode-qwen` | OpenCode | Qwen3.8 |
| `claude-glm` | Claude Code | GLM-4.7-Flash |

These names illustrate the requested combinations. They do not establish exact downloadable model identifiers, availability, or verified compatibility.

## Proposed behavior for review

- Give each profile a unique user-chosen name.
- Allow the same agent in several profiles and the same model with several compatible agents.
- Record the runtime, exact model reference, context size, model parameters, and agent launch settings.
- Associate supported context, tool-output, and memory preferences with each profile. Expose settings that affect a shared runtime separately from settings isolated to one agent session.
- Create another profile without replacing existing profiles.
- Allow an explicit default profile and launching by name.
- Apply environment variables and agent settings to the selected session without changing unrelated agent sessions.
- Treat profile deletion separately from deletion of shared models and dependencies.

Profile removal preserves installed components and model weights. Explicit uninstallation and shared-reference handling are defined in [Uninstallation and storage](uninstall-and-storage.md).

## Limits and open decisions

- Multiple stored profiles do not imply that their models can run concurrently within available memory.
- A shared model update can affect multiple profiles; affected profiles must be visible to the user.
- Storage format, repository-default locations, export format, renaming, conflict resolution, and deletion commands remain undecided. Export/import and repository-specific defaults are confirmed capabilities.
- Profile portability must account for different hardware and runtime availability on the destination computer.
- Automatic import of arbitrary shell functions is not a confirmed requirement.

## Delivery evidence

None. Profile storage, selection, execution, export/import, repository defaults, and shell completion are not implemented.
