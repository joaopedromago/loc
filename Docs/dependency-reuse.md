# Dependency detection and reuse

State: partially implemented

## Non-negotiable requirement

Setup must never reinstall an existing component or add another copy because PATH, health, version, or installation channel is inconvenient. This applies to agents, runtimes, supporting technologies, loc itself, and identical model artifacts. An intentional version update is a separate operation through the existing owner.

## Implemented detection

Discovery checks PATH, known native locations, application bundles, common NVM/Python tool environments, recorded custom locations, Homebrew records, pipx/uv records, applicable Linux package records, Windows uninstall records, and relevant npm directories. Symlinks resolving to one executable count as one installation.

Results distinguish `present`, `absent`, `unknown`, `unusable`, and `multiple`. A package record or broken executable prevents installation. Inaccessible records and unresolved application files do not prove absence. Multiple installations require explicit selection:

```sh
loc scan
loc register ollama /path/to/existing/ollama
```

Registration selects an existing executable; it does not install, copy, or repair it. Ownership records distinguish installed-by-loc from reused components and are checked against current machine state before changes.

## Coordination and model reuse

Mutating loc operations use a platform file lock, and installers recheck presence immediately before running. Failed installation never falls back to another channel. Existing incompatible Python is not an excuse to download another interpreter. Aider installation requires a compatible existing interpreter.

Profiles reference shared Ollama artifacts. Configuration aliases create metadata over shared weight blobs. Existing tags are not pulled by setup, and missing tags use Ollama's content-addressed layer reuse. Rollback retains references to different versions, not separate identical weight copies per profile.

## Honest detection boundary

Arbitrary hidden installations, other users' inaccessible state, stopped containers, and separate WSL environments cannot be exhaustively discovered by these probes. Use registration for custom locations. A supported detection failure remains pending; loc must not claim universal machine inventory or interpret uncertainty as permission to install.

Cross-runtime model imports are not automated. If a future adapter cannot reuse an artifact without duplicating weights, that operation must remain pending. Windows/Linux records and uncommon installers still need native validation.

## Delivery evidence

Automated tests cover missing-PATH installations, symlinks, broken executables, installer records, ambiguity, uncertain discovery, concurrent operations, and prevention of repeated setup downloads. The Mac's existing agents/runtime were found and reused without running their installers.
