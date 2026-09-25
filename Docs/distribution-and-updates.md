# Installing and updating loc

State: not implemented

## Confirmed intent

Users need an easy way to install loc and keep it updated on their machines. The [no-duplicate installation requirement](dependency-reuse.md) applies to loc itself and to any dependencies its installer obtains.

The user has also requested uninstallation support. loc must be removable through its original installation method while preserving installed agents, runtimes, models, and user data by default. See [Uninstallation and storage](uninstall-and-storage.md).

The user asked whether GitHub's free services can support this. The services and packaging approach below are recommendations for review, not selected infrastructure or implemented workflows.

## Recommended approach if Python is selected

Distribute loc as a versioned Python package, with uv as the preferred installation manager for new installations. Use GitHub Actions for validation and publishing, GitHub Releases for release notes and downloadable assets, and PyPI as the recommended Python package index. An optional GitHub Pages site can provide installation instructions.

Provide small POSIX-shell and PowerShell entry points that guide users through installation. They must first detect an existing loc installation and its owner, then reuse required tools and a compatible existing Python interpreter. They should install prerequisites only when those are established to be absent.

The goal is a simple user command with consistent dependency ownership, rather than requiring users to clone the repository or manage a development checkout. Installer URLs and the package name cannot be specified as usable commands until they exist.

uv supports isolated tool installation and upgrades. It also supports selecting an existing Python interpreter and disabling automatic Python downloads. The bootstrap policy must prevent an implicit interpreter download from bypassing the reuse requirement. An existing incompatible interpreter requires explicit resolution rather than silently installing another one. [uv tool guide](https://docs.astral.sh/uv/guides/tools/), [uv Python selection](https://docs.astral.sh/uv/concepts/python-versions/)

Publishing a Python package from GitHub Actions can use PyPI Trusted Publishing, avoiding a long-lived publishing token stored as a repository secret. [uv GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/), [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)

## GitHub services and cost boundaries

The following observations were checked against official documentation on 2026-09-25. Pricing and limits must be checked again before deployment.

| Service | Proposed use | Current boundary |
| --- | --- | --- |
| GitHub Actions | Validate and package releases for the supported platforms | Standard GitHub-hosted runners are free for public repositories. Private repositories have plan quotas; larger runners are billed. |
| GitHub Releases | Versioned packages, installer scripts, checksums, and release notes | Release assets must each be smaller than 2 GiB. GitHub documents no total release-size or bandwidth limit. |
| GitHub Pages | Optional documentation and installation instructions | Available for public repositories on GitHub Free; a `github.io` address avoids requiring a custom domain. |

Sources: [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [release assets](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [Pages availability](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

Actions artifacts and caches have separate allowances; release downloads should be published as release assets rather than relying on temporary CI artifacts. A public-repository approach can avoid paid build and download hosting for the initial CLI, subject to service limits. This does not imply that all optional distribution services, custom domains, or native signing arrangements are free.

Models should continue to come from their upstream runtime or model providers. loc's releases should contain the CLI and its distribution materials, not copies of Qwen or GLM weights.

## Proposed installation behavior

- Detect loc before installing loc, including known executable locations and supported package-manager records.
- If it already exists, report the installation and use its update route; do not install through another manager or directory.
- If installation ownership is uncertain or several copies already exist, resolve that state before making changes.
- Prefer installation for the current user and avoid elevated privileges when the selected route does not need them.
- Reuse existing uv and Python installations when usable. Do not bootstrap duplicate prerequisites.
- Keep user profiles and application state separate from application package files so upgrades preserve configuration.
- Identify the exact release and verify the expected artifact integrity before installing. Integrity and release-authenticity mechanisms remain to be selected.
- Re-running the installer must not create another loc installation or act as an implicit reinstall.

## Proposed update experience

These commands are illustrative and do not exist yet:

```sh
loc self update --check
loc self update
```

Updating loc is separate from `loc update`, which currently illustrates model/profile maintenance. Updating the CLI must not implicitly upgrade installed agents, runtimes, or model weights.

Recommended behavior:

- Check the current installation's channel for a newer compatible stable release.
- Cache update checks and let ordinary commands work without an internet connection. A check failure must not prevent launching an already working profile.
- Notify the user about available updates; automatic installation policy remains undecided and should not be assumed enabled.
- Update through the installation owner. For uv-managed installations, use the supported tool-update path. If Homebrew, WinGet, or another channel is later supported, use its corresponding route.
- Never fall back to another installation channel when an update fails.
- Preserve profiles and report the resulting version or actionable failure. Recovery, package replacement, and configuration migration must account for interruption and platform-specific file locking.
- Keep prereleases and downgrades explicit. Rollback depends on package availability and configuration compatibility; it must not be promised before those mechanisms exist.

For installations pinned to a version or a release-asset URL, the update process must deliberately resolve the new target. A generic upgrade must not be assumed to bypass existing source or version constraints. [uv upgrade behavior](https://docs.astral.sh/uv/guides/tools/#upgrading-tools)

## Alternatives and unresolved choices

- **GitHub-hosted packages without publishing loc to PyPI:** release assets can contain Python wheels. The installer/updater would need to select and verify the correct versioned artifact; Python dependencies may still use an external package index.
- **Standalone executables:** possible if Python is selected, but packaging tools such as PyInstaller bundle a Python interpreter and require platform-specific builds. Embedded runtime duplication needs an explicit decision under the current strict reuse requirement. [PyInstaller packaging model](https://pyinstaller.org/en/stable/operating-mode.html)
- **Native package managers:** Homebrew and WinGet may be useful additional channels. Initial channel support, publishing requirements, and maintenance ownership remain undecided.
- **Repository visibility:** public hosting is the recommended basis for the free-service approach; no repository visibility change is authorized here.
- **Still open:** package name availability, minimum Python version, supported platform builds, installer URLs, update metadata, release authentication, signing, update notification frequency, migration behavior, and release policy.

## Delivery evidence

None. No package, installer, release workflow, hosted documentation, publishing configuration, or self-update command has been implemented or deployed.
