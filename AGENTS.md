# Repository instructions

State: implemented

These instructions govern work in this repository. Application intent, limits, and implementation states live in [Docs/README.md](Docs/README.md).

## Current phase

The user authorized application planning and implementation on 2026-09-25, including testing on their Mac. Windows and Linux need additional testing on those systems.

- Implement the approved scope, with explicit support boundaries and delivery evidence.
- Exercise destructive operations in isolated fixtures; preserve the user's existing installations, configuration, and model artifacts during development.
- Run meaningful automated tests and appropriate local integration checks.
- Do not publish releases or change repository visibility unless requested.

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
