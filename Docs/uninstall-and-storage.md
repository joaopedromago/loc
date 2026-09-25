# Uninstallation and storage

State: not implemented

## Confirmed scope

The user approved installation ownership tracking, controlled cleanup, storage visibility, and preserving shared resources when removing profiles. The user also requested that loc be able to uninstall supported software and models.

Uninstallation covers supported coding agents, runtimes, optional helpers, model artifacts, and loc itself. Exact commands and supported uninstall routes remain to be defined.

## Ownership and references

- Record whether loc installed a component or reused an existing installation, along with its installation location and owning package manager or installer where known.
- Track which profiles reference each tool and model artifact, including retained artifacts needed for rollback.
- Inspect actual installation state before removal. Historical ownership records alone do not establish that a resource still belongs to loc or is unused.
- Distinguish resources unused by loc profiles from resources known to be unused everywhere. External consumers may be unknown.

## Separate removal operations

| Operation | Intended effect | Preserved by default |
| --- | --- | --- |
| Remove a profile | Remove the selected profile definition | Agents, runtimes, model weights, and other profiles |
| Uninstall a component | Remove an explicitly selected agent, runtime, helper, or model | Unrelated software, artifacts, configuration, and user projects |
| Clean storage | Remove explicitly selected eligible caches or unused artifacts | Reused third-party installations, referenced artifacts, and active workloads |
| Uninstall loc | Remove loc through its original installation method | Installed agents, runtimes, models, user projects, and profile data |

Deleting loc's saved profiles or other user data must be a separate explicit choice from uninstalling the application.

## Component uninstallation

- Identify the exact component and installation before removal. Ambiguous names or multiple installed copies require resolving the target.
- Show the removal scope, affected profiles, retained rollback references, known active usage, and the installation method that will perform the uninstall.
- Use the original package manager or supported official uninstall method. Do not delete guessed directories or switch installation channels.
- Removing a profile or running general cleanup must never implicitly uninstall an installation that loc originally reused.
- Allow an explicitly targeted uninstall of a reused installation when the user requests it and the impact is made clear. Reuse status must remain visible.
- If the component is still referenced by profiles, require an explicit resolution of those references before removal. Do not silently leave profiles presented as usable after removing their dependencies.
- Do not terminate active agents or unload models being used by another session as an implicit part of cleanup or uninstallation.
- Report missing permissions, unsupported removal routes, or unknown ownership without guessing that removal succeeded.
- Where only a manual uninstall route is supported, provide the official route, wait for completion confirmation, and recheck installation state.
- If the component is already absent, report that state without installing anything or performing unrelated cleanup.

Confirmation and noninteractive behavior remain design decisions. They must preserve the exact user-selected removal scope and account for shared resources; a broad cleanup request must not imply permission to remove everything discovered on the machine.

## Storage visibility and cleanup

- Show model storage, caches, partial downloads, and retained versions where observable.
- Identify which profiles reference an artifact and why an artifact is retained.
- Estimate reclaimable space without counting shared model layers or linked files repeatedly. Label estimates and unknowns.
- Provide a dry run that lists removal candidates and expected effects without deleting files or stopping processes.
- Recheck references and activity before removal, including paused downloads or concurrent setup work.
- Limit cleanup to known supported resources. Never remove a shared parent directory merely because it contains one managed artifact.
- Remove records only after the underlying result is verified, and report partial failures so users can retry safely.

## Illustrative commands

These commands are proposals, not executable interfaces:

```sh
loc storage
loc clean --dry-run
loc profile remove claude-next
loc uninstall agent opencode --dry-run
loc uninstall runtime ollama --dry-run
loc uninstall model glm-4.7-flash:q8_0 --dry-run
loc uninstall helper rtk --dry-run
loc self uninstall
```

## Limits and open decisions

- External applications may depend on reused or even loc-installed resources. Ownership does not prove exclusive use.
- Some upstream uninstallers remove configuration or model directories. Their effects must be understood before claiming the preservation behavior above; otherwise offer a supported alternative or leave removal pending.
- Shared model storage, file links, package-manager dependency cleanup, and running-file restrictions require platform-specific handling.
- loc self-uninstallation must account for the running process and preserve its installation-channel ownership.
- Exact target identifiers, data-removal options, cache retention, reference resolution, and confirmation behavior remain undecided.

## Delivery evidence

None. Ownership tracking, storage inspection, cleanup, component uninstallation, profile removal, and self-uninstallation are not implemented.
