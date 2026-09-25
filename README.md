# loc

Set up, run, and maintain local coding-agent environments from one CLI.

State: partially implemented

loc pairs **Claude Code, OpenCode, or Aider with Ollama** in named profiles. It detects existing tools, reuses model weights, configures local inference, and manages updates and removal. Python 3.11+ is required; loc has no runtime package dependencies.

The recommended setup is **Claude Code pointing to a local Qwen Coder model through Ollama**. Model size and context depend on the machine's memory. Other agents and models remain available through explicit selection.

The CLI is implemented and tested on an Apple Silicon Mac. Windows/Linux adapters and CI definitions are present; native validation on those systems is pending. There is no published release yet.

## Start from this checkout

```sh
python3 -m loc_cli --help
python3 -m loc_cli scan
python3 -m loc_cli models recommend
```

To install the `loc` command using your existing Python and tool manager:

```sh
python3 scripts/install.py --source . --dry-run
python3 scripts/install.py --source .
```

The installer reuses existing uv/pipx when available, otherwise creates a venv sharing the existing interpreter. It does nothing if loc is already installed. It prints the command location and does not modify shell files.

## Daily workflow

Use an exact model tag available through Ollama, or a model already installed on your machine:

```sh
loc models recommend
loc setup daily --model qwen3-coder:30b --dry-run
loc setup daily --model qwen3-coder:30b
loc doctor daily --verify
loc run daily
loc run daily -- --continue

loc setup open-coder --agent opencode --model qwen3-coder:30b
loc profiles
loc use open-coder --project
loc run
```

New profiles default to Claude Code; existing profiles keep their selected agent. Interactive `loc setup` offers a fitting Qwen Coder model as the suggested choice. The 30B tag above is an example: check `loc models recommend` for your machine before setup. If no compatible Qwen Coder model fits the estimate, loc asks for an explicit alternative. Noninteractive setup requires an exact `--model`.

The preferred pairing follows the project's chosen default, not a comparative benchmark. Recommendations label estimated fit and unmeasured performance. Qwen3 4B is used for small integration tests and remains an optional alternative.

Profiles use shared-layer Ollama configuration aliases, with session-scoped agent settings and a local model-restricted gateway. Existing shell aliases, global agent configuration, and original model references are preserved.

## Setup, maintenance, and removal

```sh
loc setup daily --resume
loc status
loc doctor --report
loc update daily --check
loc update daily
loc rollback daily
loc update --component opencode --dry-run

loc profile export daily --file daily.json
loc profile import daily.json --name imported-daily
loc setup imported-daily --resume
loc completion zsh

loc storage
loc clean --dry-run
loc uninstall agent opencode --dry-run
loc uninstall model qwen3:4b --dry-run
loc profile remove daily --dry-run
loc self update --check
loc self uninstall --dry-run
```

Setup never reinstalls an existing component as a repair shortcut. Missing PATH entries, broken installs, multiple copies, and inaccessible records remain explicit detection states. `loc register COMPONENT PATH` selects an existing custom installation. Removing a profile keeps its software and model weights; destructive operations show shared references and preserve unrelated data.

Commands support `--json`. `LOC_HOME` or global `--home PATH` selects isolated state. Use `--yes` only when applying the chosen operation noninteractively. `loc clean` previews by default; `--apply` performs cleanup.

## Local and offline behavior

Normal launches keep model inference local, while agent tools may still use the network. `loc run NAME --offline` adds OS enforcement for Claude Code/Aider on macOS. OpenCode and Windows/Linux offline combinations currently fail as unsupported. Offline mode uses a private runtime reading existing weights; it may need extra RAM alongside other sessions.

## Testing and limits

```sh
python3 -m unittest discover -v
python3 scripts/check_docs.py
```

The 112-test suite passed on the Mac with Python 3.12 and 3.14. It covers duplicate prevention, state/locking, setup recovery, gateway restrictions, agent settings, portable profiles, updates/rollback, shared-resource cleanup, and distribution integrity. Live checks exercised all three agents, the existing Qwen3.8 64K profile, and offline Claude Code/Aider. Original model digests and `.zshrc` were preserved. No existing AI tools were uninstalled for testing.

The first runtime adapter is Ollama. LM Studio, llama.cpp, and MLX-LM are future candidates. Model recommendations are estimates; total task tokens, peak memory, and comparative coding quality are not yet measured. Fresh-machine installers and native Windows/Linux behavior need further verification. Release-based self-update requires the first GitHub release to be published.

The [Docs index](Docs/README.md) contains the full scope, implementation states, and limits. Start with [Implementation and verification](Docs/implementation-and-testing.md) for evidence, and [Installing and updating loc](Docs/distribution-and-updates.md) for release preparation. Contributors should follow [AGENTS.md](AGENTS.md).
