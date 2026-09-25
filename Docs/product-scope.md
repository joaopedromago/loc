# Product scope

State: partially implemented

## Confirmed intent

loc manages local coding-agent environments through named profiles. The user authorized implementation on 2026-09-25 after the documentation phase. Windows, Linux, and macOS remain target platforms; Python 3.11+ is the selected implementation language.

The CLI covers hardware inspection, model recommendations, installation, setup, launch, updates, diagnostics, portability, and removal. It must reuse existing installations and model weights, preserve unrelated configuration, and reduce unnecessary context while retaining useful coding quality.

The user selected Claude Code pointing to a locally served Qwen Coder model as the recommended setup. Model size and context must remain hardware-aware. This preference does not remove other supported agents/models or establish a universal quality ranking.

## Delivered behavior

The package implements profiles pairing Claude Code, OpenCode, or Aider with Ollama. Commands cover setup/resume and previews, launch, model recommendations, verification, status, profile import/export, repository defaults, shell completion, model update/rollback, component installation/update/uninstall, storage cleanup, and loc self-management.

Ollama configuration aliases reuse content-addressed weight layers. Agent settings are scoped to each launch. A local gateway restricts inference to the selected installed model. Supported macOS offline launches add operating-system network enforcement.

See [Implementation and verification](implementation-and-testing.md) for architecture and observed evidence; each capability document defines its remaining limits.

## Boundaries

- Coding agents are the entire product focus. General chat, image/audio generation, training, and fine-tuning are outside this scope.
- loc integrates existing agents and runtimes; it does not implement their reasoning loops or replace their permissions.
- No GUI, hosted inference, or multi-machine orchestration is included.
- Exact model artifacts and compatibility matter; a model-family name is not a guarantee of availability or quality.
- Setup installs only components established to be absent within supported detection coverage. Unknown or conflicting installations remain pending.
- When an eligible component needs manual installation, loc opens its official page and waits for explicit completion confirmation, then rechecks availability.
- Installation, model updates, component updates, and loc self-updates remain distinct operations.

## Remaining work

Live Windows/Linux agent and dependency-installer validation, future runtime adapters, and broader quality/performance measurements remain incomplete. The first public release, v0.1.0, is published and its release installer has been verified. Existing installations and model artifacts were preserved during local development.

## Delivery evidence

Python package, CLI, automated tests, and live Mac coding checks. See [Implementation and verification](implementation-and-testing.md).
