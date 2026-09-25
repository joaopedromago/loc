<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/loc-logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/loc-logo-light.svg">
    <img src="assets/loc-logo-light.svg" alt="loc" width="200" height="100">
  </picture>
</h1>

<p align="center"><strong>Local coding agents. One CLI.</strong></p>

loc sets up, runs, and maintains local coding-agent environments. Choose a profile, reuse the tools and models already on your machine, and start coding.

The recommended pairing is **Claude Code + a local Qwen Coder model through Ollama**, with model selection based on your hardware. OpenCode, Aider, and other compatible local models are also supported.

> **Early development:** automated CLI tests run on macOS, Windows, and Linux. Live coding-agent checks cover Apple Silicon macOS; Windows/Linux agent setup still needs validation.

## Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Updates](#updates)
- [Configuration](#configuration)
- [Local inference and offline mode](#local-inference-and-offline-mode)
- [Uninstallation](#uninstallation)
- [Troubleshooting](#troubleshooting)
- [Platform support](#platform-support)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

## Installation

### Requirements

- An existing **Python 3.11+** installation.
- Enough memory and disk space for the model you select. `loc models recommend` estimates memory fit.
- Internet access when downloading missing software or model weights.

loc has no runtime Python package dependencies. Agents and Ollama can already be installed; setup detects and reuses them. Missing components use supported installers or a guided manual installation flow.

### Install the latest release

Download [install.py](https://github.com/joaopedromago/loc/releases/latest/download/install.py) from the [latest release](https://github.com/joaopedromago/loc/releases/latest), then run it from the download directory:

**macOS / Linux**

```sh
python3 install.py
```

**Windows PowerShell**

```powershell
python install.py
```

The installer checks the release wheel against `SHA256SUMS` before installation. It uses an existing uv or pipx, otherwise an isolated environment sharing your Python interpreter. Repeating installation detects the existing loc copy and leaves it in place. Add `--dry-run` to preview.

The optional `install.sh` and `install.ps1` release assets are wrappers; keep `install.py` in the same directory. Python must already be installed.

### Install from source

Run from the root of a checkout containing this README and `scripts/install.py`.

**macOS / Linux**

```sh
python3 scripts/install.py --source .
```

**Windows PowerShell**

```powershell
python scripts/install.py --source .
```

This route is intended for development or an unreleased checkout. It uses the same existing-installation detection as the release installer.

The installer prints the command location. It does not edit your shell files or PATH. If your shell cannot find `loc`, follow [Command not found](#command-not-found).

### Verify installation

```sh
loc --version
loc --help
```

You can also use the checkout without installing a command:

```sh
python3 -m loc_cli --help
python3 -m loc_cli scan
```

See [Installing and updating loc](Docs/distribution-and-updates.md) for the distribution details.

## Quickstart

Inspect your machine, create a profile, and launch it:

```sh
loc scan
loc models recommend
loc setup daily
loc run daily
```

Interactive setup defaults to Claude Code and suggests a compatible Qwen Coder model that fits the memory estimate. It reuses installed components and model weights, then asks before obtaining anything missing. If no preferred model fits, choose an alternative explicitly.

The first profile becomes your global default. After setup, launch it with:

```sh
loc run
```

To verify the full agent/model connection with a disposable coding edit:

```sh
loc doctor daily --verify
```

## Usage

### Get help

Every command accepts `--help` or `-h`. Help lists the command's purpose, arguments, options, useful defaults, and an example.

```sh
loc --help
loc run -h
loc setup --help
loc models recommend -h
loc profile export --help
```

Commands with actions, such as `profile` and `self`, also explain each available action. Use `loc run daily -- --help` to ask the selected agent for its own help.

### Select an exact model

Choose a model from the recommendations or your installed inventory:

```sh
loc models list
loc models --name
loc models recommend --context 32768
loc setup coder --model qwen3-coder:30b --dry-run
loc setup coder --model qwen3-coder:30b
```

Use `loc models --name` or `loc models -n` to print only installed model names, one per line. Add `--json` for an array of names.

The 30B tag is an example, not a requirement for every machine. Check its memory estimate before setup. New profiles default to Claude; use `--agent opencode` or `--agent aider` to choose another agent. Noninteractive setup requires a profile name, `--model`, and `--yes` to apply the operation.

Create a new profile name when changing an existing profile's settings. Setup preserves an existing profile instead of silently replacing it.

### Prefer quick responses

For a small model that answers without a separate thinking phase, use the explicit Instruct tag:

```sh
loc setup fast-instruct --agent claude --model qwen3:4b-instruct
loc run fast-instruct
```

The `qwen3:4b` tag inspected during local testing contained Qwen3-4B-Thinking-2507, which can spend many tokens reasoning even about simple prompts. Claude's `/effort low` does not turn a thinking-only model into a non-thinking one. The Instruct variant uses different weights and may need a download. See [response-time limits](Docs/resource-efficiency.md#quick-responses-and-thinking-models).

To reduce Claude's tool definitions to file reading, editing, writing, shell commands, and file/text search:

```sh
loc run fast-instruct --tools "Read,Edit,Write,Bash,Glob,Grep"
```

This limits the tools available in that session; Claude's normal permission checks still apply. Omit `--tools` when you need its full tool set.

### Switch profiles

```sh
loc setup alternate --agent opencode --model qwen3-coder:30b
loc profiles
loc profile show daily
loc use daily
loc run alternate
```

Set a default for the current repository:

```sh
loc use alternate --project
loc run
```

Selection order is **explicit profile → repository `.loc.json` → global default**. Multiple profiles can share agents and model weights.

### Pass arguments to an agent

Pass agent options directly, with or without a profile name:

```sh
loc run --dangerously-skip-permissions
loc run daily --continue
loc run fast-instruct --tools "Read,Edit,Write,Bash,Glob,Grep"
```

Put the profile name and loc options (`--dry-run`, `--offline`, `--json`, `-h`, `--help`) before agent options. The first option loc does not recognize starts the agent arguments; it and everything following it are forwarded unchanged, including option values. For example, `loc run --effort low` uses your default profile.

The explicit separator still works: `loc run daily -- --help` asks the agent for help, while `loc run --help` shows loc's help. Use `--` when an agent option has the same name as a loc option.

Agent options that override the configured model or inference destination are rejected. Permission options are forwarded only when supplied; for Claude, `--dangerously-skip-permissions` disables its normal permission prompts for that launch.

### Move a profile between machines

```sh
loc profile export daily --file daily.json
loc profile import daily.json --name imported-daily
loc setup imported-daily --resume
```

Exports contain profile settings and model identity. Credentials, machine paths, and model weights stay on the original machine. Imported profiles remain pending until setup verifies the destination. Custom model aliases must already exist there or be recreated from their original recipe.

## Updates

### Update loc

```sh
loc self info
loc self update --check
loc self update
```

Self-update checks the latest stable GitHub release, verifies its checksum, and updates through the original installation manager, preserving your profiles. See the [changelog](CHANGELOG.md) for version history and the versioning policy.

### Update models and tools

```sh
loc update daily --check
loc update daily
loc rollback daily
loc update --component claude --dry-run
```

A model update verifies a real coding edit before activating the new configuration. Retained configurations allow rollback. Component updates use their existing installation channel. See [Maintenance](Docs/maintenance.md) for shared-model effects and rollback limits.

## Configuration

### Profile settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `--agent` | `claude` | Coding agent for a new profile |
| `--context` | `32768` | Model context capacity |
| `--output-tokens` | `4096` | Response budget |
| `--map-tokens` | `1024` | Repository-map budget where supported |
| `--temperature` | `0.2` | Model sampling temperature |
| `--endpoint` | `http://127.0.0.1:11434` | Local Ollama endpoint |

Settings apply to the selected profile. Agent configuration is scoped to each session; existing shell aliases and global agent settings are preserved. Ollama configuration aliases share weight layers instead of copying model files.

Agents see your selected model's original name. Internal `loc-*` aliases hold profile settings and appear separately as `resolved_model` in diagnostics. Use `loc profile show NAME` to inspect both identifiers.

Use `loc setup --help` for all setup options. Memory estimates and context tradeoffs are described in [Model recommendations](Docs/model-recommendations.md) and [Resource efficiency](Docs/resource-efficiency.md).

### State location

| Platform | Default directory |
| --- | --- |
| macOS | `~/Library/Application Support/loc` |
| Linux | `$XDG_STATE_HOME/loc`, or `~/.local/state/loc` |
| Windows | `%LOCALAPPDATA%\loc` |

Set `LOC_HOME` or use global `--home PATH` to select another state directory. Model weights remain in Ollama's storage.

### JSON output and completion

```sh
loc profiles --json
loc status --json
loc completion zsh
```

`loc completion` prints a script for `bash`, `zsh`, `fish`, or `powershell`. Load it through your shell's usual completion configuration. loc does not modify shell startup files automatically.

## Local inference and offline mode

Normal launches send model inference to the selected local model. Agent tools may still access the network.

For enforced offline operation:

```sh
loc run daily --offline
```

Offline enforcement currently supports **Claude Code and Aider on macOS**. Other combinations report that they are unsupported. Offline launches use existing weights and a private runtime, which may need extra memory alongside other sessions. See [Local inference and offline operation](Docs/local-and-offline.md).

## Uninstallation

Removing a profile keeps its software and model weights:

```sh
loc profile remove daily --dry-run
```

Inspect storage or preview removal of a specific resource:

```sh
loc storage
loc clean
loc uninstall model qwen3-coder:30b --dry-run
loc uninstall agent opencode --dry-run
```

`loc clean` previews by default; `--apply` removes eligible unused model references created by loc. Explicit removals show affected profiles and refuse to remove resources still in use. See [Uninstallation and storage](Docs/uninstall-and-storage.md) before applying removals.

To remove loc itself:

```sh
loc self uninstall --dry-run
loc self uninstall
```

Self-uninstall preserves profiles, coding agents, model runtimes, and model weights.

## Troubleshooting

### Command not found

First, check the command location printed by the installer. If it exists, add its directory to your user PATH instead of installing another copy.

For the common macOS/Linux user command directory, in bash or zsh:

```sh
export PATH="$HOME/.local/bin:$PATH"
command -v loc
loc --version
```

Use the actual directory printed by the installer. The fallback environment uses `~/.local/share/loc/venv/bin`. To persist the change, add the corresponding PATH entry to your shell configuration. In zsh, `rehash` refreshes command lookup after installation.

On Windows, add the printed command directory to your **user Path** in Environment Variables, then open a new terminal. You can also invoke the installed executable by its full path.

### No profile selected

Installing loc does not create a coding profile. Run `loc setup daily`, or choose an existing default with `loc use NAME`.

### Runtime unavailable or setup interrupted

```sh
loc runtime status
loc runtime start
loc setup daily --resume
loc doctor daily
```

Starting the runtime reuses the existing Ollama installation. Resume checks what is already present and continues setup without reinstalling completed dependencies.

### Existing installation is ambiguous

Use `loc scan` to inspect detected paths. Select a custom installation with `loc register COMPONENT PATH`. Unknown or broken installations block automatic installation until resolved; loc does not treat them as missing.

### Collect a diagnostic report

```sh
loc doctor daily --report
```

The report is written locally and is never uploaded automatically. Review it before sharing. Include the loc version, operating system, failing command, and relevant error when reporting a problem.

## Platform support

State: partially implemented

| Platform | Current verification |
| --- | --- |
| macOS, Apple Silicon | Live setup and coding edits with Claude Code, OpenCode 2, and Aider; offline checks with Claude/Aider |
| Linux | Python 3.11/3.14 automated CLI tests passed; live agents and dependency installers pending |
| Windows | Python 3.11/3.14 automated CLI tests passed; live agents and dependency installers pending |

The current runtime is Ollama. LM Studio, llama.cpp, and MLX-LM remain future integrations. OpenCode 1 has configuration tests; its live integration is pending. Recommendations estimate fit and do not claim measured comparative coding quality.

See [Implementation and verification](Docs/implementation-and-testing.md) for observed checks, fresh-machine installation gaps, and other limits.

## Contributing

Read [AGENTS.md](AGENTS.md) and the [documentation index](Docs/README.md) before making changes. Keep implementation claims aligned with delivered behavior and preserve existing user environments during tests.

From the repository root:

```sh
python3 -m unittest discover -v
python3 scripts/check_docs.py
```

Application tests use isolated fixtures for installers and destructive operations. Live model tests are opt-in; instructions are in [Implementation and verification](Docs/implementation-and-testing.md).

## Documentation

- [Product scope](Docs/product-scope.md)
- [Setup and launch](Docs/setup-and-launch.md)
- [Profiles and project defaults](Docs/profiles.md)
- [Supported technologies](Docs/technology-candidates.md)
- [Dependency detection and reuse](Docs/dependency-reuse.md)
- [Full documentation index](Docs/README.md)

Wordmark assets: [SVG](assets/loc-logo.svg) · [PNG](assets/loc-logo.png) · [Light theme](assets/loc-logo-light.svg) · [Dark theme](assets/loc-logo-dark.svg).

## License

loc is released under the [MIT License](LICENSE). Integrated agents, runtimes, and model weights retain their own licenses.
