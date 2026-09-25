# Implementation and verification

State: partially implemented

## Authorization and architecture

On 2026-09-25 the user authorized implementation of the documented scope and testing on their Mac. Windows and Linux testing will also be performed by the user. Implementation choices below follow that authorization; they do not imply a published release.

loc is a Python 3.11+ package with no runtime dependencies. Its console command is `loc`; the distribution name is `loc-coding`. The package uses the standard library for argument parsing, HTTP, subprocess management, atomic JSON state, and platform locks.

The first supported runtime is Ollama. Agent adapters cover Claude Code 2.x, OpenCode 1.x/2.x, and Aider. Optional helpers are RTK and llmfit. Other runtimes in [Technology candidates](technology-candidates.md) remain future integrations.

## Components

| Module | Responsibility |
| --- | --- |
| `core.py` | Validated profiles, state, locks, project defaults, and redaction |
| `discovery.py` | Existing executables, installer records, ownership, and explicit registration |
| `install.py` | Reuse, installer routes, manual completion, component update/uninstall, runtime startup |
| `ollama.py` | Local runtime API, model inventory, shared-layer configuration aliases |
| `gateway.py` | Session inference restricted to the selected local model and context |
| `agents.py` | Agent configuration, argument forwarding, sessions, and disposable editing verification |
| `lifecycle.py` | Setup recovery, model updates, rollback, references, removal, and cleanup |
| `hardware.py` | Hardware inspection and clearly labeled model-fit estimates |
| `offline.py` | macOS runtime/agent network sandboxes; unsupported combinations fail closed |
| `distribution.py` | Release checksum validation and updates/uninstall through the original owner |

No command edits the user's shell aliases. Generated agent configuration is temporary. Persistent user state lives outside the repository, with `LOC_HOME` or `--home` available for isolated testing.

## Automated checks

Run from the checkout:

```sh
python3 -m unittest discover -v
python3 scripts/check_docs.py
python3 -m loc_cli --help
```

The tests cover actual local HTTP fixtures, duplicate prevention, ambiguous/broken installations, state corruption, competing processes, dry runs, interrupted downloads, profile portability, model identity drift, network restrictions, shared-resource cleanup, failed updates, rollback, and release checksums. Installer and destructive component actions use fixtures. They do not uninstall the developer's existing AI environment.

The complete suite passed 123 tests on both installed Python 3.14 and Python 3.12. Documentation state/link checks and `git diff --check` also passed.

After adding direct agent-argument forwarding to `loc run`, the full suite passed 132 tests on Python 3.14. The nine new forwarding tests also passed on Python 3.12. They cover default/explicit profiles, agent option values and ordering, loc options, explicit separators, help, strict parsing for other commands, model/provider restrictions, and forwarding an explicitly requested Claude permission flag without changing persistent settings.

CLI help was checked with both `-h` and `--help` across 43 command/action forms (86 calls) on Python 3.12 and 3.14. Every command has a short purpose, described arguments/options, and an example. Both flags produce matching output and exit successfully before accessing state or dispatching an operation. The regression suite also passed after the help update.

Names-only model listing passed 23 CLI checks for `--name`/`-n`, implicit/explicit `list`, exact output, empty inventories, JSON, custom endpoints, runtime errors, and rejection of other actions without dispatch or state creation. All 123 regression tests passed on Python 3.14 after this change. The existing pipx installation was updated and both flags were checked against all 10 models in the Mac's live Ollama inventory; saved profiles and inventory remained unchanged.

Recommendation regressions cover the user-selected Claude Code + local Qwen Coder default, memory limits, installed custom aliases, unreadable/hosted metadata, interactive selection, and preservation of existing agent/model choices. A read-only CLI check on the Mac selected an existing Qwen Coder alias for Claude and left the model inventory and profile state unchanged.

Model-identity regressions verify that agents and API metadata use the original model name while inference remains pinned to the internal configuration alias. They cover all agent adapters, JSON responses, Anthropic/OpenAI event streams, native Ollama streaming, unchanged generated text/tool arguments, and digest/selection restrictions.

The fix was applied to the existing pipx-managed loc installation and checked against the tested source. A fresh Claude Code session using the existing daily profile answered the model-identity question with `qwen3.8-coder-q8-64k:latest`; its model-usage metadata used the same original tag. This exercised one inference request with zero gateway errors. Saved profiles, `.zshrc`, and the complete model-name/digest inventory were unchanged. Existing sessions require restart to receive the new configuration.

GitHub Actions passed the six Python 3.11/3.14 jobs across macOS, Windows, and Linux for commit `37118bc`: [observed test run](https://github.com/joaopedromago/loc/actions/runs/36179465444). These jobs exercise the automated suite, package installation, command version, and documentation checks. Live agent setup and OS-specific dependency installers remain separate validation work.

## v0.1.0 release preparation

The user authorized the first public release and chose the MIT license. Both package version declarations are `0.1.0`. The wheel includes SPDX license metadata, the MIT license text, the `loc` entry point, and no runtime dependencies. The source archive includes the license, changelog, release notes, tests, and documentation; local state, caches, and model weights are excluded.

Release preparation passed all 132 tests on Python 3.12 and 3.14 on the Mac. `scripts/smoke_install.py --dist PATH` passed against the built wheel and distributed installer, using fixture download responses and a real temporary Python environment. It checked checksums, command help/version, installation ownership, duplicate prevention without another download, and self-uninstall preserving saved profile state byte-for-byte. The developer's existing installations were not changed.

The tag workflow repeats the hosted test matrix and runs this installation check before creating a draft with six download assets. Public-download verification will be recorded after the draft is published.

## Live Mac verification

The inspected machine has Apple Silicon and 64 GiB of unified memory. Existing Ollama 0.34.3, Claude Code 2.1.278, OpenCode 2.0.11, and Aider 0.86.2 were reused.

Verified with disposable file edits:

- Claude Code with installed Qwen3 4B.
- Claude Code with Qwen3 4B Instruct: a disposable file edit passed in 4.71 seconds, with three inference requests and zero gateway errors.
- OpenCode 2 with installed Qwen3 4B.
- Aider with installed Qwen3 4B.
- OpenCode 2 with the user's existing Qwen3.8 Q8 64K configuration.
- Aider with Qwen3 4B inside the macOS offline sandbox.
- Claude Code with Qwen3 4B inside the macOS offline sandbox.

The network test checks the agent and a child process: the gateway port is reachable; external addresses and unrelated local ports are blocked. Original model digests and `.zshrc` were checked before and after live tests and preserved. Test configuration aliases share existing weight blobs and are tracked in ignored `.tmp/` test state.

For the requested response-time improvement, setup created a separate `fast-instruct` profile and downloaded the missing `qwen3:4b-instruct` weights, reusing the existing Claude and Ollama installations. Existing profiles, the global default, and prior model digests were preserved. [Resource efficiency](resource-efficiency.md#delivery-evidence) records the controlled latency comparison: the non-thinking model with six core coding tools answered the test question in about 5.5 seconds. These isolated results do not guarantee the same timing in an existing repository session.

The package was built and installed into an isolated environment using the existing interpreter. Repeating installation made no changes. Self-uninstallation removed the test package and preserved saved profiles byte-for-byte. Release downloads and installer failures are exercised with fixtures.

Repeat a live integration check only when you intend to load the selected installed model:

```sh
python3 scripts/smoke_local.py --model qwen3:4b
python3 scripts/smoke_local.py --model qwen3:4b --agents aider --offline
```

The script creates configuration aliases and retains its test state for inspection. It never downloads model weights or removes original models. A successful small edit is evidence of basic integration, not a coding benchmark or a guarantee against every failure.

## Remaining verification

- Live Windows/Linux agent setup, OS-specific dependency installer/uninstaller behavior, and additional hardware.
- OpenCode 1 live integration; its adapter has configuration tests.
- Production release publishing and first installation from real release assets.
- Fresh-machine installation routes: existing software was deliberately preserved on this Mac.
- Representative coding-quality, token-efficiency, latency, and peak-memory comparisons. Unmeasured values remain unknown.

## Delivery evidence

Source, tests, packaging, installer scripts, and workflow definitions are in the repository. Local test outcomes above were observed on 2026-09-25. Detailed capability limits remain in the linked documents.
