# Repository instructions

State: implemented

These instructions govern work in this repository. Application intent, limits, and implementation states live in [Docs/README.md](Docs/README.md).

## Current phase

The current phase is static documentation for user review. The application is not implemented.

- Create and refine the requested documentation and repository hygiene files.
- Wait for the user's confirmation of this scope before starting application planning.
- Do not create application code, an implementation plan, package manifests, dependency installations, scaffolding, tests, or CI workflows during this phase.
- Documentation checks do not require separate confirmation.
- After the user authorizes a later phase, follow that authorization without asking for the same confirmation again.

## Read before working

1. Read [Docs/README.md](Docs/README.md) for the document index and state definitions.
2. Read [Docs/product-scope.md](Docs/product-scope.md) for the confirmed intent.
3. Read [Docs/review-and-decisions.md](Docs/review-and-decisions.md) for proposals and unresolved decisions.
4. Read the relevant capability documents before changing their scope or implementation state.

## Documentation discipline

- Keep product intent and limits in `Docs/`; link to them rather than maintaining competing specifications here.
- Every Markdown file in `Docs/` must declare exactly one `State:` using `implemented`, `partially implemented`, or `not implemented`.
- State describes delivery of the document's subject, not whether someone has written or approved the document.
- Writing requirements does not implement an application capability.
- Keep confirmed user requirements separate from proposals and unresolved decisions.
- Do not promote an assistant suggestion to an approved decision without user confirmation.
- When implementation is authorized, update affected documents with the delivered behavior, remaining limits, and verification evidence.
- Keep the document index synchronized with the files and their states.
- Treat illustrative CLI commands and model names as examples until explicitly resolved.

## Working conventions

- Use concise, grammatically correct communication in the user's language. Write repository documentation in clear English unless requested otherwise.
- Prefer `rg` for searches. Use RTK for supported shell commands when available; use original commands for unsupported operations or exact-output checks.
- Preserve unrelated work and existing local environments.
- Do not store credentials, machine-specific configuration, downloaded models, or runtime caches in the repository.
- Validate changes proportionately. Static documentation needs link, state, and formatting checks; it does not need application tests.
