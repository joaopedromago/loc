# Profiles

State: not implemented

## Confirmed intent

Multiple profiles are a core requirement. A user must be able to keep combinations such as Claude Code with Qwen3-Coder-Next and OpenCode with Qwen3.8 on the same computer.

A profile represents a selected coding agent and model, together with the configuration needed to run that combination.

The user also wants setup to configure efficient local operation. Proposed context and memory behavior is documented in [Resource efficiency](resource-efficiency.md).

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
- Share compatible model downloads and runtime installations across profiles.
- Apply environment variables and agent settings to the selected session without changing unrelated agent sessions.
- Treat profile deletion separately from deletion of shared models and dependencies.

## Limits and open decisions

- Multiple stored profiles do not imply that their models can run concurrently within available memory.
- A shared model update can affect multiple profiles; affected profiles must be visible to the user.
- Storage format, global versus repository-specific profiles, import/export, renaming, and deletion commands remain undecided.
- Profile portability must account for different hardware and runtime availability on the destination computer.
- Automatic import of arbitrary shell functions is not a confirmed requirement.

## Delivery evidence

None. Profile storage, selection, and execution are not implemented.
