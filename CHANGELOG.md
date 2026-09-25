# Changelog

Versions use `MAJOR.MINOR.PATCH`. During `0.x` development, patch releases contain fixes and minor releases introduce capabilities or compatibility changes. Released versions are never replaced; subsequent changes receive a new version. Version `1.0.0` will establish a stable CLI and configuration contract.

## 0.1.0 — 2026-09-25

Initial public release of loc, licensed under MIT.

- Set up Claude Code, OpenCode, or Aider with local Ollama models through named profiles.
- Detect and reuse existing tools and model layers; install only supported missing components.
- Inspect hardware and recommend models using explicit memory-fit estimates.
- Configure local model identity, context, sampling, and output budgets through session-scoped agent settings.
- Launch default or named profiles and forward agent options directly, including options with values.
- List installed model names with `loc models --name` or `loc models -n`.
- Inspect setup health, verify a disposable coding edit, export/import profiles, and choose repository defaults.
- Update models and tools, retain model rollback references, inspect storage, and remove selected resources.
- Install and update loc from GitHub release assets with SHA-256 verification and existing-manager reuse.
- Provide command help, JSON output, and shell completion scripts.

Python 3.11+ is required. Automated CLI tests run on macOS, Windows, and Linux. Live coding-agent checks cover Apple Silicon macOS; Windows/Linux agent and native installer validation remains pending. Enforced offline execution currently supports Claude Code and Aider on macOS only. Model rankings are estimates, not coding benchmarks.

See the [release notes](releases/v0.1.0.md) and [verification record](Docs/implementation-and-testing.md).
