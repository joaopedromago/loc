# Uninstallation and storage

State: partially implemented

## Supported operations

| Operation | Effect | Preserved by default |
| --- | --- | --- |
| `loc profile remove NAME` | Remove a profile and its rollback references | Installed tools, model weights, other profiles |
| `loc uninstall KIND TARGET` | Remove an explicitly selected agent, runtime, helper, or model | Unrelated software, projects, configuration, and shared model layers |
| `loc clean` | Preview eligible unreferenced model artifacts created by loc | Reused models, all software, referenced/loaded artifacts, unknown partial downloads |
| `loc self uninstall` | Remove loc through its installation owner | Profile data, agents, runtimes, models, and projects |

```sh
loc storage
loc clean --dry-run
loc clean --apply
loc uninstall agent opencode --dry-run
loc uninstall runtime ollama --dry-run
loc uninstall model qwen3:4b --dry-run
loc uninstall helper rtk --dry-run
loc self uninstall --dry-run
```

## Ownership and removal rules

loc records installation location/owner and whether it installed or reused a resource. It checks real state again before removal. Ownership does not prove exclusive use: external consumers may be unknown.

Uninstall previews identify the exact target, route, affected profiles, rollback references, known loaded models, and ownership. Existing ambiguous copies require registration before removal. Component uninstallation uses the supported original package manager or native remover; it does not delete guessed directories or switch channels. OpenCode's native route preserves configuration and session data. Unsupported routes use official manual instructions, explicit completion confirmation, and a subsequent availability check.

Referenced resources cannot be removed by default. Explicit `--detach` disables affected profiles and discards affected rollback references before removal; partial failures remain visible. Loaded models and active loc sessions block destructive operations. Component processes are inspected without collecting their arguments. loc never implicitly terminates unrelated workloads.

Explicitly targeting a reused installation is allowed after its impact is shown. General cleanup and profile deletion never implicitly uninstall reused software. Already-absent model removals are idempotent. `--yes` applies only the selected operation; it does not expand its scope.

## Storage accounting

Storage shows model identities, logical sizes, profile/rollback references, and ownership. Logical sizes are not summed because layers may be shared. When local manifests match the runtime inventory, loc measures physical blob storage, counts hardlinks once, and reports partial-download bytes. Unknown/custom storage and external symlinks remain explicitly unverified.

Cleanup removes only selected, unreferenced, unloaded model references created by loc, using the runtime API. It rechecks state before removal and deletes ownership records only after verification. It never deletes shared parent directories. Runtime partial downloads and caches with unknown ownership are preserved.

## Limits

Actual reclaimable bytes depend on the runtime's remaining references. Native removers may have platform-specific effects; only routes preserving the documented data should be automated. Windows/Linux installer and process-inspection coverage still needs native validation. loc self-uninstall preserves saved user data; there is no implicit purge option.

## Delivery evidence

Fixture tests cover shared references, loaded models, explicit detach, cleanup eligibility, previews, and idempotence. A temporary loc installation was uninstalled on the Mac while its saved profiles remained byte-for-byte unchanged. The user's installed AI tools were not uninstalled for testing.
