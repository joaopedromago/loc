# Documentation index

State: implemented

This index and the documentation conventions are delivered. No application capability is implemented, and the scope is awaiting user review. Documentation completion does not imply approval to start planning or development.

## Current phase

Create `AGENTS.md`, `.gitignore`, and the static documents in `Docs/`. The user will review these files before application planning starts.

`loc` is a working project and command name. Examples describe possible behavior, not commands available in this repository.

## Documents

| Document | Subject | State |
| --- | --- | --- |
| [Product scope](product-scope.md) | Purpose, confirmed requirements, and product boundaries | not implemented |
| [Profiles](profiles.md) | Multiple agent and model combinations | not implemented |
| [Setup and launch](setup-and-launch.md) | CLI installation, browser fallback, model downloads, and starting coding agents | not implemented |
| [Model recommendations](model-recommendations.md) | Hardware-aware selection for coding agents | not implemented |
| [Resource efficiency](resource-efficiency.md) | Relevant context, fewer tokens, memory limits, and coding quality | not implemented |
| [Maintenance](maintenance.md) | Updates, compatibility checks, and proposed recovery behavior | not implemented |
| [Platforms and constraints](platforms-and-constraints.md) | Windows, Linux, macOS, and technical limits | not implemented |
| [Review and decisions](review-and-decisions.md) | Pending scope approval and unresolved decisions | not implemented |

The root [AGENTS.md](../AGENTS.md) defines repository working instructions. The root [.gitignore](../.gitignore) excludes local and generated artifacts.

## State definitions

Every document declares one of these exact states near its beginning:

- `implemented`: the subject is delivered, with evidence appropriate to that subject.
- `partially implemented`: some of the subject is delivered; the document must identify what works and what remains.
- `not implemented`: the subject has no delivered implementation. Intent, proposals, and examples can still be documented.

For product documents, state refers to application behavior. For this index, it refers only to the index and documentation conventions. For the review document, it refers to resolution of the review and decisions.

Implementation state and user approval are separate. An approved requirement can remain `not implemented`.

## Maintenance convention

When authorized work changes a capability, update its document and this index together. Record the resulting behavior, verification evidence, and remaining limits before advancing its state.
