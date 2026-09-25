# Technology candidates

State: not implemented

## Purpose

Record the recommended support scope for user review. This is a candidate list, not an approved support matrix, implementation plan, or commitment to install every listed technology.

Every candidate is subject to [Dependency detection and reuse](dependency-reuse.md). Setup should obtain only missing components required by the chosen profiles. Supporting a technology must include recognizing existing installations, not just providing an installation command.

## Recommended initial candidates

| Category | Candidates | Reason to evaluate |
| --- | --- | --- |
| Inference runtime | Ollama | Matches the existing workflow and provides model management and documented coding-agent integrations. |
| Coding agents | Claude Code, OpenCode, Aider | Covers the user's existing workflows and the requested agent/model combinations. |
| Model catalog | Selected Qwen coding and GLM configurations | Matches the requested examples while keeping compatibility validation bounded to exact artifacts and settings. |
| Optional output helper | RTK | Candidate for reducing noisy command output where agent integration is supported. |
| Optional hardware advisor | llmfit | Candidate for hardware inspection and model-fit recommendations. |
| Supporting dependencies | Git, plus Python/uv or Node.js when required by a chosen installation route | Obtain only dependencies needed for that profile and reuse any existing compatible installation. |

Ollama documents integrations for [Claude Code](https://docs.ollama.com/integrations/claude-code) and [OpenCode](https://docs.ollama.com/integrations/opencode). Aider documents its own [Ollama connection](https://aider.chat/docs/llms/ollama.html). These integrations are evidence to evaluate; they do not establish that every model works with every agent.

[RTK](https://github.com/rtk-ai/rtk) and [llmfit](https://github.com/AlexsJones/llmfit) remain optional candidates. Neither is required merely because a user creates a coding profile. Their compatibility, installation reuse, and overhead need evaluation before adoption.

Qwen and GLM are model families here. Support must identify exact runtime artifacts, versions or digests, quantizations, context settings, and agent compatibility. It must not imply support for every family member or a promise to download all variants.

## Additional candidates to evaluate later

| Technology | Potential role | Boundary |
| --- | --- | --- |
| LM Studio / llmster through `lms` | Reuse an existing local runtime or offer an alternative to Ollama | Recognize the existing installation and model inventory; do not install another runtime automatically. |
| llama.cpp | Direct control over local model serving | Requires its own installation, backend, lifecycle, and model-artifact compatibility checks. |
| MLX-LM | An Apple Silicon runtime option | Platform-specific support must remain explicit. |

LM Studio's [CLI documentation](https://lmstudio.ai/docs/cli) describes model downloads, model inventory, server controls, and headless-daemon management. [llama.cpp](https://github.com/ggml-org/llama.cpp) provides local inference and server tooling. [MLX-LM](https://github.com/ml-explore/mlx-lm) provides LLM execution on Apple Silicon. These are alternatives to evaluate, not dependencies to install alongside Ollama by default.

## Installation channels

Possible channels include official native installers and existing package managers such as Homebrew, WinGet, or the system's Linux package manager. These are installation mechanisms, not additional coding technologies every user must install.

Channel selection must follow detection. For example, finding a native application must prevent a second installation through a package manager. Python tool environments and Node package installations must likewise be inspected before choosing another route. Exact channel coverage remains undecided.

## Limits and open decisions

- The user has not yet approved this technology list or initial coverage.
- A runtime or agent is not supported until detection, reuse, installation fallback, configuration, launch, and relevant compatibility checks are defined and verified for the claimed platform. Update and uninstall coverage must also be explicit, including any manual routes or limitations.
- Model recommendations must remain a curated and maintainable subset of available artifacts.
- Browser fallback can cover missing installation automation; it cannot make incompatible software or model formats work together.
- User-selected profiles determine needed installations. The candidate list is not an install-all bundle.
- Ownership-detection mechanisms, update and uninstall routes, optional helper defaults, and exact agent/runtime versions remain undecided. Ownership tracking and uninstallation are confirmed capabilities; see [Uninstallation and storage](uninstall-and-storage.md).

## Delivery evidence

None. No listed integration or installation channel is implemented by this project.
