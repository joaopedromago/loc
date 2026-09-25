# Diagnostics and recovery

State: partially implemented

## Delivered behavior

```sh
loc setup daily --dry-run
loc setup daily --resume
loc doctor daily
loc doctor daily --verify --timeout 240
loc doctor --report
loc status
```

Setup previews show reused/missing components, installation routes, model actions, catalog download estimates, available disk space, and estimated temporary space. Unknown sizes are labeled. Resume rechecks real state, keeps completed installations/downloads, and leaves interrupted profiles pending. Provider-supported layer continuation is used; otherwise the provider may restart a partial transfer.

Basic doctor checks inspect agent version, runtime reachability, exact model identity, local completion capability, and configured context. `--verify` loads the selected model and asks the selected agent to repair a tiny Python function in a disposable directory. It checks the actual resulting syntax without executing model-written code. Success requires an edit, a successful process exit, and observed local inference.

Verification restricts its editing task and isolates agent caches/configuration. It reports failure, timeout, skipped checks, and unknown measurements separately. Verification timeouts terminate only the process tree loc started. Normal agent sessions preserve interactive terminal behavior.

## Status and reporting

Status exposes requested and observed model identities, drift, local endpoints, loaded model information, runtime versions, hardware memory snapshots, and known loc sessions. Reading status never loads models just to fill missing values.

Reports allowlist diagnostic fields and remove sensitive values and home-directory identification. They do not include environment dumps, credentials, repository content, or unrestricted subprocess logs. A report is written locally, never uploaded. Existing report files are not overwritten; inspect one before sharing.

## Limits

A single editing task demonstrates basic integration, not general coding quality. Context capacity and artifact bytes are distinct from observed resident memory. Total task tokens and peak process-tree memory are currently unavailable and reported as unknown. Diagnostic text deliberately omits raw agent output; the opt-in development smoke script can retain local test logs.

Memory availability varies by platform. Download estimates exclude unknown installer sizes and may not match a custom runtime storage volume. Native Windows/Linux verification remains pending.

## Delivery evidence

Fixture tests cover interrupted setup and diagnostic failure paths. Live editing checks and environment preservation are recorded in [Implementation and verification](implementation-and-testing.md).
