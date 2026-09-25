# Dependency detection and reuse

State: not implemented

## Confirmed requirement

The system must automatically identify existing installations and must never install a duplicate. If Ollama is already installed, setup must reuse that installation and must not run an installer again. This rule applies to every supported technology, including agents, runtimes, supporting tools, and model artifacts.

The rule applies regardless of whether loc or another tool originally installed the component. Creating another profile must not trigger another installation or another download of the same model artifact.

The loc installer and updater must follow this rule too. An existing loc installation must be updated through its installation owner rather than creating another copy through a different channel. See [Installing and updating loc](distribution-and-updates.md).

Installation ownership tracking is also confirmed scope. Distinguish components loc installed from those it reused, and preserve that distinction during profile removal, cleanup, and explicit uninstallation. See [Uninstallation and storage](uninstall-and-storage.md).

## Required observable behavior

- Check for existing installations before invoking an installer or opening a browser for manual installation.
- Treat an existing installation as present even when its service is stopped, its executable is missing from PATH, or a health check fails.
- Do not install another copy because the existing version is incompatible or because a different installation channel would be more convenient.
- Reuse the selected existing installation across profiles that depend on it.
- Reuse existing model artifacts when the runtime and format are compatible. Resolve identical artifacts by identity rather than assuming different profile names require different downloads.
- When several copies already exist, identify them and resolve which one to use. Do not add another copy or automatically remove the user's existing installations.
- If installation presence cannot be established confidently, leave installation pending and request the missing location or clarification. Unknown must not be treated as absent.
- Offer CLI or browser installation only after establishing that the component is absent.
- Recheck the installation state when retrying or resuming setup, including after a browser installation, before attempting any further installation.

## Detection boundaries

Checking PATH alone is insufficient. Supported detection needs to cover the applicable platform installation records, known application locations, package managers, managed tool environments, executable paths, and runtime/model inventories.

The exact detection mechanisms are deferred until planning. Every supported installation channel must have a defined detection boundary. Custom locations, inaccessible records, or installations in another environment may leave the result uncertain; setup must expose that uncertainty instead of claiming absence.

Native Windows, WSL, containers, and separate tool environments may expose different installations. Finding a component in another environment does not establish that the chosen profile can use it, and does not authorize automatically installing a second copy.

## Existing but unusable components

Diagnostics should identify whether the problem is availability, configuration, compatibility, or a damaged installation. Correcting a path, starting an existing service, or selecting another compatible profile is distinct from installing software.

Setup must not reinstall an existing component as a recovery shortcut. Any deliberate repair, upgrade, or migration belongs to a separate user-authorized action and must preserve the no-duplicate requirement. An update must target the chosen existing installation rather than silently adding another distribution.

## Models and shared files

Different versions or quantizations represent different model artifacts. Multiple profiles referencing the same artifact must share it where supported. A changed artifact in an intentional model update is distinct from downloading another copy of the same artifact.

If an existing artifact cannot be reused by the selected runtime without making a duplicate, explain the incompatibility and leave that step pending. Do not silently duplicate weights into another runtime's storage. Exact cross-runtime reuse and import support remains undecided.

Rollback proposals in [Maintenance](maintenance.md) must account for this rule: preserve references to existing artifacts where possible, and distinguish retained different versions from redundant copies of identical data.

## Proposed safeguards for review

- Record installation location, version, and channel when observable to support the confirmed ownership-tracking requirement, while checking actual machine state again on later runs.
- Coordinate simultaneous setup attempts so loc does not install or download the same component twice.
- Recheck immediately before installation, including after user interaction or an external installer completes.
- Inspect installer-managed prerequisites; a top-level installer must not bypass reuse of an existing dependency.
- Make detection results visible, such as an existing runtime's location and whether it is ready or needs attention.

The handling of external installers running concurrently with loc remains a design question. The product must not claim exhaustive detection of arbitrary hidden installations; uncertain cases must remain pending.

## Delivery evidence

None. Dependency discovery, reuse, duplicate prevention, and installation coordination are not implemented.
