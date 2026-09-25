# Review and decisions

State: implemented

## Authorization

The user first requested static documentation for review, then approved the additional usability/lifecycle scope and uninstallation. On 2026-09-25 the user explicitly requested implementation of everything documented and testing on their Mac. Planning, application code, packaging, tests, and workflow definitions are now authorized; the documentation-only restriction is superseded.

The user will also run Windows/Linux tests. The implementation must preserve the existing local AI environment during development. The user subsequently authorized preparing, testing, committing, pushing, and publishing the first release, `v0.1.0`, using external Chrome for publication. The user selected the MIT license. Repository visibility changes remain outside the request.

## Selected implementation decisions

- Python 3.11+ with standard-library runtime dependencies only; package `loc-coding`, command `loc`.
- Ollama first, with Claude Code 2, OpenCode 1/2, and Aider adapters. RTK and llmfit remain optional helpers.
- User-selected recommendation: Claude Code with a local Qwen Coder model through Ollama. Prefer compatible Qwen Coder candidates within the memory estimate; retain explicit alternatives and existing profile choices.
- Versioned JSON profiles/state, atomic writes, process locks, and explicit custom-installation registration.
- Session-scoped agent configuration and a model-restricted local gateway. Shared-layer aliases hold profile context/sampling settings.
- Explicit profile selection, then repository default, then global default.
- Imported profiles remain pending until destination verification. No secrets, model weights, or executable scripts in exports.
- Explicit updates/removals; owner-specific routes and retained model configurations for rollback. No automatic update scheduler.
- GitHub release wheels/checksums and installer scripts; reuse existing uv/pipx or an existing-interpreter venv. No bundled Python or model weights.
- macOS offline enforcement for supported adapters; unsupported combinations fail closed.

## Confirmed product rules

Local coding agents only. Multiple profiles. Hardware-aware recommendations. Efficient context on limited RAM. Installation detection and no duplicates. CLI installation where supported and browser/manual completion otherwise. Recovery, diagnostics, reports, portability, completion, project defaults, local inference, offline behavior, storage visibility, cleanup, and uninstall are all in scope.

The detailed limits and implementation states live in their capability documents rather than competing specifications here.

## Remaining decisions and delivery limits

Future runtime adapters, expanded native platform coverage, richer model benchmarks, additional completion behavior, advanced runtime memory tuning, and signed release provenance remain future work. The first public release, v0.1.0, was published as authorized; [publication and installation evidence](implementation-and-testing.md#v010-release-verification) is recorded separately from workflow definitions. No further scope approval is required to fix or test the implementation already authorized.

## Delivery evidence

The prior approval gate is resolved, implementation choices are recorded, and [Implementation and verification](implementation-and-testing.md) links the resulting code/tests and observed limits.
