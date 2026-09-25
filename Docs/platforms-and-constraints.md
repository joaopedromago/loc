# Platforms and constraints

State: not implemented

## Confirmed intent

Support Windows, Linux, and macOS. Python is the user's preferred language candidate, with alternatives explicitly allowed.

Setup should install required tools and download selected models through the CLI where supported. When CLI installation is unavailable for an otherwise supported component, setup must open a browser for manual installation and wait for the user's completion confirmation.

## Proposed compatibility boundaries for review

- Keep user-facing profile and launch behavior consistent across supported platforms.
- Account for platform-specific paths, terminal behavior, dependency installation, and runtime startup.
- Record installation coverage separately from runtime compatibility: a supported component may require manual installation on one platform and allow CLI installation on another.
- Identify supported operating system, architecture, runtime, and accelerator combinations explicitly.
- Detect unsupported combinations and explain the limitation instead of claiming successful setup.
- Account for shared memory on relevant systems and separate system memory and accelerator memory where applicable.
- Avoid embedding the original developer's home directory, shell, or hardware into product behavior.
- Preserve existing installations and unrelated user configuration.
- Keep credentials, local state, model weights, and caches outside tracked source files.

## Candidate technologies, not decisions

- Python for the CLI and environment coordination.
- Ollama as an initial inference runtime.
- Claude Code, OpenCode, and Aider as agent integration candidates.
- Existing hardware inspection and model recommendation tools as possible dependencies.

These candidates come from the user's existing workflow and earlier discussion. No dependency, architecture, package manager, configuration format, or distribution method is selected in this phase.

## Limits and open decisions

- Cross-platform intent does not mean that every GPU or agent is supported on every operating system.
- Minimum OS versions, CPU architectures, supported accelerators, CPU-only behavior, and initial support coverage remain undecided.
- Native Windows versus WSL support requires an explicit decision.
- Packaging, dependency versions, offline operation, and installation privilege handling remain undecided.
- Browser availability, terminal environment refresh after installation, and installation verification need platform-specific handling; the exact mechanisms remain undecided.
- Support claims must eventually be backed by checks on the relevant platform; documentation alone is not evidence of support.

## Delivery evidence

None. No language toolchain, platform adapters, dependencies, packaging, or support matrix has been implemented.
