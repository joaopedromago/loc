# Installing and updating loc

State: partially implemented

## Package and installation

loc is distributed as the Python package `loc-coding`, exposing the `loc` command. It requires an existing Python 3.11+ and has no runtime package dependencies. The source checkout is usable immediately:

```sh
python3 -m loc_cli --help
python3 scripts/install.py --source . --dry-run
python3 scripts/install.py --source .
```

The standalone installer detects existing loc commands and uv/pipx records before installation. Repeated installation reports the existing copy and does nothing. Failed record inspection blocks installation. It prefers existing uv, then pipx, otherwise a venv sharing the existing interpreter. It never downloads another Python or automatically installs another tool manager.

The POSIX and PowerShell wrappers invoke the same installer. Python must already be available; they provide the official Python installation destination when it is missing. Shell files and PATH are not rewritten; the installer shows the resulting command location.

For a published release, `install.py` resolves the latest stable GitHub wheel, checks the asset host and SHA-256 checksum, then installs through the selected owner. Model weights are never bundled. Release installers require no PyPI publication of loc; building from source may obtain setuptools as a build dependency.

## Self-management

```sh
loc self info
loc self update --check
loc self update --dry-run
loc self update
loc self uninstall --dry-run
loc self uninstall
```

Updates use the existing uv, pipx, or bootstrap-owned venv. Unknown/development installations receive an actionable refusal to create another copy. A wheel mismatch or failed owner update never triggers another installation channel. The new version is checked after replacement. Prereleases and automatic background updates are not enabled.

Self-uninstall removes loc's package through that owner, preserving profile data and all installed AI tools/models/projects. The bootstrap's existing interpreter environment can remain available for explicit reuse; removal does not purge user directories.

## GitHub delivery

The repository contains cross-platform test and release workflow definitions. A version tag matching package metadata builds a wheel/source archive, copies installer assets, creates `SHA256SUMS`, and publishes a GitHub Release when the workflow is intentionally triggered. No release has been published during development, so release-based install/update cannot succeed until the first release exists.

GitHub standard hosted Actions runners are free for public repositories; private quotas and larger-runner charges differ. Release assets must each stay below 2 GiB. Optional Pages documentation and PyPI Trusted Publishing remain future choices, not dependencies of installation. Repository visibility was not changed.

Sources: [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [GitHub release assets](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [uv tools](https://docs.astral.sh/uv/guides/tools/), [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/).

## Limits

Checksums verify consistency with a GitHub release, not an independent signing identity. Code signing, artifact attestations, native Homebrew/WinGet loc packages, PyPI name registration, public release deployment, cached update notifications, and package-version rollback remain incomplete. Configuration schema mismatches fail without rewriting state.

Unknown/custom hidden loc installations require resolution before installation; bounded detection is not an exhaustive filesystem search. Native Windows upgrade/file-lock behavior still needs testing.

## Delivery evidence

A wheel was built and installed into an isolated Mac environment. Repeating the installer made no changes. Self-uninstall removed that test package while preserving its saved profiles byte-for-byte. Checksums, failed metadata, unknown owners, and non-mutating previews are covered by tests. No production release was published.
