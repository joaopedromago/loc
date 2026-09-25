# Diagnostics and recovery

State: not implemented

## Confirmed scope

The user approved resumable setup, download and disk-space estimates, an optional change preview, complete profile verification, runtime status, and diagnostic reports. These extend the setup and diagnostic capabilities already in scope.

Exact command syntax, implementation mechanisms, and platform coverage remain undecided.

## Setup visibility and recovery

- Show the components already available, the ones still needed, and the changes setup would make.
- Estimate download size and required free disk space, including temporary files and retained versions during updates. Label unavailable or approximate values.
- Provide an optional dry run that reports intended changes without installing software, changing configuration, starting services, or downloading models.
- Preserve completed setup steps when installation is interrupted. Recheck actual installation state before continuing so resumed setup obeys [Dependency detection and reuse](dependency-reuse.md).
- Resume partial downloads where the provider supports it. Where it does not, explain the restart and reuse already completed artifacts.
- Report progress and cancellation clearly. Interrupted work must not be marked complete or leave a profile presented as ready.
- Preserve the existing working configuration when a replacement fails and report any partial changes that still require attention.

## Profile verification

Diagnostics must cover the selected agent, runtime connection, exact model, usable context, and relevant editing capabilities. Checking that executables exist is not sufficient to demonstrate a working profile.

Provide a verification action that exercises a small coding task in a disposable directory. It should check the selected agent's tool or edit protocol and confirm that the requested edit occurred. The check must not modify the user's repository.

Distinguish basic inspection from verification that loads a model and performs inference. Show whether each check passed, failed, was skipped, or could not be measured. A successful small task demonstrates basic compatibility, not general coding quality.

## Status

Expose the selected profile, requested and observed model identities, runtime endpoint, loaded models, and available memory information. Include agent and runtime versions where detectable.

Distinguish observed values, estimates, and unknowns. Report differences between a profile's expected configuration and the actual environment, including changed model references or missing dependencies. Reading status should not load a model or change the environment merely to fill in missing values.

## Diagnostic reports

Allow users to produce a report suitable for troubleshooting or filing an issue. Remove credentials, authentication headers, sensitive environment values, repository content, and unnecessary identifying paths.

Users must be able to inspect the report before choosing to share it. Generating a report does not upload it. Diagnostics should report the useful failure and affected component without embedding unrestricted command output or configuration files.

## Illustrative commands

These commands are proposals, not implemented interfaces:

```sh
loc setup --dry-run
loc setup --resume
loc doctor claude-next --verify
loc doctor --report
loc status
```

## Limits and open decisions

- Download continuation depends on the provider; resuming setup must still work when a particular download must restart.
- Verification tasks, timeouts, report format, and redaction rules remain undecided.
- Hardware and runtime statistics may be unavailable on some platforms; missing data must not be replaced with invented measurements.
- Offline behavior is governed by [Local inference and offline operation](local-and-offline.md).
- Recovery must not reinstall an existing component or silently switch installation channels.

## Delivery evidence

None. Setup previews, recovery, profile verification, status inspection, and diagnostic reports are not implemented.
