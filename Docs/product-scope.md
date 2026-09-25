# Product scope

State: not implemented

This document records confirmed intent and proposed boundaries. The user has not yet approved the complete documentation set.

## Purpose

Provide a CLI that makes local coding-agent environments easy to set up, launch, and maintain across computers.

The intended user currently manages agent launchers through shell aliases and functions, with separate scripts for model updates. The product should replace that recurring manual configuration with simple commands and reusable profiles.

## Confirmed requirements

- Focus exclusively on coding-agent environments.
- Support multiple named profiles, including different agents paired with different models.
- Detect the computer's configuration and recommend suitable models for coding work.
- Configure local coding agents to reduce unnecessary context and token use while aiming for high coding quality on machines with limited memory. See [Resource efficiency](resource-efficiency.md).
- Set up the dependencies and configuration needed to use the selected coding agent locally.
- Automatically identify and reuse existing installations of every supported technology. Never install a duplicate or reinstall an existing component during setup. See [Dependency detection and reuse](dependency-reuse.md).
- Install required tools and download the selected models through the CLI where supported, including setups such as Ollama with a Qwen model.
- When CLI installation is unavailable, open the relevant installation page in a browser and wait for the user to complete installation and confirm before continuing setup.
- Launch coding agents with convenience comparable to existing aliases.
- Update models when needed.
- Provide an easy way to install loc itself and keep it updated on users' machines. See [Installing and updating loc](distribution-and-updates.md).
- Support resumable setup, download and disk-space estimates, and an optional preview of intended changes.
- Verify complete coding profiles, show actual runtime status, and generate diagnostic reports with sensitive information removed. See [Diagnostics and recovery](diagnostics-and-recovery.md).
- Support profile export/import, repository-specific default profiles, and shell completion. See [Profiles](profiles.md).
- Make local inference destinations explicit, prevent unexpected cloud fallback, and support verified offline operation for compatible environments. See [Local inference and offline operation](local-and-offline.md).
- Track installation ownership and storage usage, provide controlled cleanup, and allow users to uninstall supported components and loc itself while accounting for shared dependencies. See [Uninstallation and storage](uninstall-and-storage.md).
- Target Windows, Linux, and macOS.
- Consider Python as the preferred starting language while leaving alternatives open.
- Complete and review these static files before planning the application.

## Existing workflow as context

The inspected local setup uses Ollama with Claude Code, OpenCode, and Aider. Launchers select Qwen or GLM models and sometimes define context limits or agent-specific settings. A shell script pulls a fixed model list and recreates a custom model configuration.

This is background for the problem, not a requirement to reproduce every existing flag or support every tool in the first release. The existing machine's paths and hardware must not become product assumptions.

## Scope boundaries

The coding-agent focus excludes general chat products, image or audio generation, and unrelated AI workloads.

The following additional boundaries are proposed for review:

- Integrate existing coding agents and inference runtimes.
- Leave the agent's reasoning loop, repository edits, and execution permissions to the selected agent.
- Keep training, fine-tuning, runtime development, and multi-machine orchestration outside the initial scope.
- Keep a graphical interface and hosted inference outside the initial local CLI scope.
- Do not promise support for every model, accelerator, or agent on every platform.

## Intended outcome

A user can obtain the required tools and models, configure several local coding profiles on a supported computer, launch any profile inside a repository, and maintain those profiles through simple commands. Setup should guide the user through both automated installation and any required manual installation steps.

## Delivery evidence

None. This repository currently contains static documentation and repository hygiene files only.
