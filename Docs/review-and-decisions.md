# Review and decisions

State: not implemented

The documentation is prepared for review. Individual requirements and later clarifications are recorded below. Approval of the complete scope and resolution of technical decisions remain pending, so this review subject remains not implemented.

## Current authorization

The user requested `AGENTS.md`, `.gitignore`, and static documents describing all product intent and limits, followed by a root `README.md` introducing the project. Every document must carry an implementation state.

The user will confirm this documentation before application planning starts. This document is a review record, not an implementation plan or a development backlog.

The user has explicitly approved adding all suggested usability and recovery features below, plus uninstallation support, to the scope documents. This approves those capabilities for documentation; command syntax, architecture, and application implementation remain unresolved.

## Confirmed direction

- Local coding-agent environments are the entire product focus.
- Multiple agent/model profiles are essential.
- Setup should reduce unnecessary information and token use while aiming for high coding quality within limited local memory.
- The CLI should detect hardware, help select models, set up agents, launch profiles, and update models.
- Users must have an easy way to install loc itself and keep it updated.
- Resumable setup, download/disk estimates, and optional dry runs are in scope.
- Complete profile verification, actual runtime status, and diagnostic reports with sensitive information removed are in scope.
- Installation ownership, storage visibility, and controlled cleanup must preserve shared and reused resources unless the user explicitly targets them for removal.
- Users must be able to uninstall supported agents, runtimes, helpers, models, and loc itself through appropriate installation-owner routes.
- Portable profile export/import, repository-specific defaults, and shell completion are in scope.
- Explicit local inference, no unexpected cloud fallback, and verified offline behavior for supported combinations are in scope.
- Setup should install required tools and download selected models through the CLI where supported.
- Setup must automatically identify existing installations across all supported technologies and must never reinstall them or create duplicates. Detection uncertainty must be resolved before installing anything.
- If CLI installation is unavailable, setup should open the relevant installation page in a browser and wait for the user to finish installation and confirm before proceeding.
- Windows, Linux, and macOS are target platforms.
- Python is preferred but not mandatory.

## Proposals awaiting review

- The `loc` command name and illustrated command syntax.
- Default-selection precedence, profile storage/export formats, and shared dependency mechanisms. Repository defaults, export/import, and the no-duplicate requirement are confirmed.
- Session-scoped settings and non-destructive setup behavior.
- Exact installation-verification checks, retry/cancellation interfaces, and instructions when a browser cannot be opened. Profile verification and resumable setup are confirmed capabilities.
- Recommendation criteria, catalog freshness, and optional local validation.
- Context selection, compact tool output, native compaction, and memory tuning described in [Resource efficiency](resource-efficiency.md), including optional RTK integration.
- Update previews, retention of previous artifacts, and rollback.
- Initial integrations and the additional scope boundaries in the capability documents.
- The recommended integration scope in [Technology candidates](technology-candidates.md), with optional helpers and additional runtimes kept separate from required profile dependencies.
- GitHub-based distribution, a possible Python/uv package route, installer entry points, and self-update behavior in [Installing and updating loc](distribution-and-updates.md).
- Detailed diagnostic checks, recovery mechanisms, offline enforcement, supported completion shells, uninstall confirmation behavior, and the new illustrative command names.

## Decisions deferred until planning is authorized

| Topic | Unresolved decision |
| --- | --- |
| Language | Python or another language |
| Initial coverage | Which agents, runtimes, operating system versions, and accelerators ship first |
| CLI | Final commands, flags, defaults, and interactive behavior |
| Profiles | Storage/export formats, default precedence, repository trust handling, portability checks, and completion shells |
| Recommendations | Data sources, dependency choices, ranking, maintenance, and verification |
| Resource efficiency | Supported controls, context budgets, optional integrations, shared-runtime effects, and quality/resource measurements |
| Installation | Detection coverage, reuse mechanisms, ambiguous or incompatible installations, packaging, dependency ownership, CLI/browser routes, completion verification, runtime lifecycle, and privilege handling |
| Updates | Version tracking, shared dependencies, validation, retention, and rollback |
| loc distribution | Repository visibility, package identity, installation channels, GitHub services, release policy, and self-update behavior |
| Diagnostics and recovery | Verification tasks, resume mechanisms, status measurements, and report redaction |
| Offline operation | Supported agent/platform combinations and network restriction/verification mechanisms |
| Uninstallation and storage | Ownership detection, reference resolution, shared storage accounting, uninstall routes, and data-retention options |
| Delivery | Architecture, sequencing, milestones, and test strategy |

These questions are intentionally unresolved. Their presence does not authorize planning or select an approach.

## Approval record

- Static-file creation: requested by the user.
- Installation scope clarification: the user requested CLI installation and model downloads, with a browser fallback that waits for installation and confirmation.
- Efficiency scope clarification: the user requested reduced information load and token use with high coding quality on machines with limited memory; individual techniques remain proposals.
- Dependency reuse clarification: the user requires automatic detection and no duplicate installation for every supported technology, including installations made outside loc.
- Distribution scope clarification: the user requested easy installation and updates for loc itself and asked about GitHub's free services; the proposed hosting and packaging choices remain unapproved.
- Usability and lifecycle additions: the user approved all suggested recovery, verification, status/reporting, ownership/cleanup, portability, local/offline, completion, and repository-default features, and explicitly requested uninstallation support.
- Complete documentation review and remaining proposals: awaiting user confirmation; confirmed requirements above do not require approval again.
- Application planning: not yet authorized.
- Application implementation: not yet authorized.

After confirmation, record what the user approved and any corrections before beginning the newly authorized work. Existing authorization should not be requested again.
