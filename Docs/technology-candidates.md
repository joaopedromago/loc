# Supported technologies and candidates

State: partially implemented

## Initial integrations

| Technology | Delivered role | Installation/update/removal boundary |
| --- | --- | --- |
| Ollama | Local model inventory, pull, shared-layer configuration, serving, update/rollback, removal | Reuse native installs; Homebrew cask on macOS, WinGet on Windows, official Linux installer, manual fallback |
| Claude Code 2.x | Local Anthropic-compatible launch and editing verification | Reuse native/npm/manager installs; supported native or manager routes; manual uninstall when no verified owner route exists |
| OpenCode 1.x / 2.x | Version-specific local configuration, compaction, launch, verification | Native installer or WinGet; original owner updates; native uninstall keeps configuration/data |
| Aider | Local Ollama chat, repository-map/context budgets, verification | Reuse or install with existing uv/pipx and compatible existing Python; owner-specific update/uninstall |
| RTK | Optional installation/reuse and concise command-output guidance | Homebrew where supported, otherwise official manual route; no global hook rewrite |
| llmfit | Optional installation/reuse | Homebrew where supported, otherwise official manual route; recommendation engine does not require it |
| Git, Python, uv, pipx, Node.js | Discover supporting tools and reuse them where needed | No install-all bundle, no implicit extra Python downloads, no substitute-channel recovery |

Discovery must precede every route; a technology is never reinstalled just because its preferred installer differs from its current owner. Read [Dependency detection and reuse](dependency-reuse.md) for the strict rule and detection boundaries.

Qwen and GLM are model families, not additional agent installers. Model support identifies exact Ollama artifacts and their capabilities. The catalog is a maintainable subset, not a promise to download every model or support every family member.

## Future runtime candidates

LM Studio/llmster through `lms`, llama.cpp, and MLX-LM are not implemented adapters. They remain candidates for later coverage, with their own discovery, model-format, context, serving, lifecycle, and platform requirements. Supporting one must not silently copy existing weights into another runtime store.

## Evidence and limits

The Mac reused Ollama, Claude Code, OpenCode 2, and Aider and completed live coding checks. OpenCode 1 has configuration tests. Fresh installation/removal routes are tested through fixtures; native Windows/Linux checks remain pending. No support claim extends to arbitrary future major versions.

Official references: [Ollama Claude integration](https://docs.ollama.com/integrations/claude-code), [OpenCode 2 providers](https://opencode.ai/v2/docs/providers), [Aider Ollama](https://aider.chat/docs/llms/ollama.html), [OpenCode installer](https://opencode.ai/install), [RTK](https://github.com/rtk-ai/rtk), [llmfit](https://github.com/AlexsJones/llmfit).

## Delivery evidence

Integration adapters, discovery/installer routes, fixture tests, and live Mac checks are recorded in [Implementation and verification](implementation-and-testing.md).
