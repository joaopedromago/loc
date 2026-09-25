# Documentation index

State: implemented

The user authorized application implementation on 2026-09-25. The repository now contains a working Python CLI, tests, installers, and release workflow definitions. Native Mac checks have run; Windows/Linux and production release deployment still have explicit gaps.

## Documents

| Document | Subject | State |
| --- | --- | --- |
| [Product scope](product-scope.md) | Confirmed requirements and product boundaries | partially implemented |
| [Profiles](profiles.md) | Agent/model profiles, portability, project defaults, completion | implemented |
| [Setup and launch](setup-and-launch.md) | Detection, installation, recovery, local agent sessions | partially implemented |
| [Dependency detection and reuse](dependency-reuse.md) | Discovery, ownership, and strict duplicate prevention | partially implemented |
| [Diagnostics and recovery](diagnostics-and-recovery.md) | Previews, verification, status, and reports | partially implemented |
| [Local inference and offline operation](local-and-offline.md) | Model restrictions and OS-enforced offline behavior | partially implemented |
| [Uninstallation and storage](uninstall-and-storage.md) | Ownership, references, storage, cleanup, and removal | partially implemented |
| [Supported technologies and candidates](technology-candidates.md) | Initial integrations and future runtime candidates | partially implemented |
| [Installing and updating loc](distribution-and-updates.md) | Package, installers, self-management, GitHub delivery | partially implemented |
| [Model recommendations](model-recommendations.md) | Hardware inspection, catalog, estimated fit | partially implemented |
| [Resource efficiency](resource-efficiency.md) | Context, compaction, output, and memory tradeoffs | partially implemented |
| [Maintenance](maintenance.md) | Model/component updates and retained rollback | partially implemented |
| [Platforms and constraints](platforms-and-constraints.md) | macOS, Windows, Linux, and verified coverage | partially implemented |
| [Review and decisions](review-and-decisions.md) | Resolved implementation authorization and choices | implemented |
| [Implementation and verification](implementation-and-testing.md) | Architecture, checks, and observed results | partially implemented |

The root [README.md](../README.md) introduces the CLI. [AGENTS.md](../AGENTS.md) governs repository work. [.gitignore](../.gitignore) excludes generated/local artifacts.

## State definitions

Every Markdown document in this directory declares exactly one state near its beginning:

- `implemented`: its subject is delivered, with appropriate evidence.
- `partially implemented`: delivered behavior and remaining work are identified.
- `not implemented`: there is no delivered implementation of its subject.

State describes delivery, not whether requirements were written or approved. A capability can be approved yet only partially implemented. The index's state refers to this index; the review document's state refers to the resolved authorization and decision record.

Update affected capability documents, their evidence, and this index together when behavior changes. Do not turn fixture tests or workflow definitions into claims of native platform verification.
