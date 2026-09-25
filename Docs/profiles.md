# Profiles

State: implemented

## Intent and delivered behavior

Profiles store an agent, Ollama source model, context/output/map budgets, temperature, supported sampling parameters, local endpoint, resolved model reference, and model digests. Several profiles may reuse the same agents and model layers.

The source `model` is the name shown to agents. The `resolved_model` is the internal configuration alias used for inference and retained in diagnostic output. Displaying the source name does not change which pinned weights or profile settings serve the request.

Supported agents are `claude`, `opencode`, and `aider`. The recommended pairing is Claude Code with a local Qwen Coder model, selected to fit the machine. New profiles default to `claude`; existing profiles keep their agent/model. OpenCode + Qwen3.8 and Claude Code + GLM remain supported alternatives; use exact installed or upstream model tags. Qwen3-Coder-Next below is an example for sufficient memory, not a fixed default on every machine.

```sh
loc setup claude-next --agent claude --model qwen3-coder-next:latest --context 32768
loc profiles
loc profile show claude-next
loc use claude-next
loc use claude-next --project
loc run
loc run claude-next --continue
```

Explicit profile selection takes precedence over the nearest repository `.loc.json`, then the user-wide default. Repository discovery stops at a Git boundary. `.loc.json` accepts only a schema version and an existing profile name; it cannot contain executable instructions. Changing one repository default does not change others.

## Portability

```sh
loc profile export claude-next --file claude-next.json
loc profile import claude-next.json --name imported-next
loc setup imported-next --resume
```

Exports contain declarative settings and source identity, without credentials, machine paths, repository content, model weights, or temporary model aliases. Imports enter `pending` state. Setup rechecks dependencies, model identity, and context on the destination. Conflicting profile names and unavailable artifacts produce actionable errors. A changed source digest requires explicit `--accept-model-change`.

Custom upstream aliases must already exist on the destination or be made available through their original recipe; exporting a profile does not publish or copy that model. Portability does not promise equal performance on different hardware.

## Removal and completion

`loc profile remove NAME --dry-run` previews removal. Applying it removes the definition and rollback references while keeping software and models. Repository defaults pointing at a removed profile fail visibly; loc does not rewrite unrelated repositories.

`loc completion bash|zsh|fish|powershell` prints a completion script. Completion candidates include commands, profiles, and common flags, and do not start inference or modify state. Source the generated script using the selected shell's normal mechanism; loc does not modify shell files.

## Limits

Existing profiles cannot be overwritten with different settings during setup; create another named profile. Renaming and an interactive profile editor are not included. Stored profiles do not imply that their models fit concurrently in RAM. Shared source updates and rollback references remain visible through [Maintenance](maintenance.md) and [Uninstallation and storage](uninstall-and-storage.md).

## Delivery evidence

Profile validation, import/export, conflict handling, defaults, and completion are covered by automated tests. Multiple live Mac profiles reused installed tools and model layers.
