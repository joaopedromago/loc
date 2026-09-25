# Review and decisions

State: not implemented

The documentation is prepared for review. Individual requirements and later clarifications are recorded below. Approval of the complete scope and resolution of technical decisions remain pending, so this review subject remains not implemented.

## Current authorization

The user requested `AGENTS.md`, `.gitignore`, and static documents describing all product intent and limits. Every document must carry an implementation state.

The user will confirm this documentation before application planning starts. This document is a review record, not an implementation plan or a development backlog.

## Confirmed direction

- Local coding-agent environments are the entire product focus.
- Multiple agent/model profiles are essential.
- Setup should reduce unnecessary information and token use while aiming for high coding quality within limited local memory.
- The CLI should detect hardware, help select models, set up agents, launch profiles, and update models.
- Setup should install required tools and download selected models through the CLI where supported.
- If CLI installation is unavailable, setup should open the relevant installation page in a browser and wait for the user to finish installation and confirm before proceeding.
- Windows, Linux, and macOS are target platforms.
- Python is preferred but not mandatory.

## Proposals awaiting review

- The `loc` command name and illustrated command syntax.
- Named defaults, profile storage semantics, and shared dependency behavior.
- Session-scoped settings and non-destructive setup behavior.
- Installation verification after automated or manual installation, retry/cancellation behavior, and instructions when a browser cannot be opened.
- Recommendation criteria, catalog freshness, and optional local validation.
- Context selection, compact tool output, native compaction, and memory tuning described in [Resource efficiency](resource-efficiency.md), including optional RTK integration.
- Update previews, retention of previous artifacts, and rollback.
- Initial integrations and the additional scope boundaries in the capability documents.

## Decisions deferred until planning is authorized

| Topic | Unresolved decision |
| --- | --- |
| Language | Python or another language |
| Initial coverage | Which agents, runtimes, operating system versions, and accelerators ship first |
| CLI | Final commands, flags, defaults, and interactive behavior |
| Profiles | Storage format, location, repository overrides, and portability |
| Recommendations | Data sources, dependency choices, ranking, maintenance, and verification |
| Resource efficiency | Supported controls, context budgets, optional integrations, shared-runtime effects, and quality/resource measurements |
| Installation | Packaging, dependency ownership, platform-specific CLI routes and browser destinations, completion verification, runtime lifecycle, and privilege handling |
| Updates | Version tracking, shared dependencies, validation, retention, and rollback |
| Delivery | Architecture, sequencing, milestones, and test strategy |

These questions are intentionally unresolved. Their presence does not authorize planning or select an approach.

## Approval record

- Static-file creation: requested by the user.
- Installation scope clarification: the user requested CLI installation and model downloads, with a browser fallback that waits for installation and confirmation.
- Efficiency scope clarification: the user requested reduced information load and token use with high coding quality on machines with limited memory; individual techniques remain proposals.
- Documentation and proposed scope: awaiting user confirmation.
- Application planning: not yet authorized.
- Application implementation: not yet authorized.

After confirmation, record what the user approved and any corrections before beginning the newly authorized work. Existing authorization should not be requested again.
