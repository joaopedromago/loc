# Maintenance

State: partially implemented

## Model updates and rollback

```sh
loc update daily --check
loc update daily --dry-run
loc update daily
loc rollback daily
```

Update checks compare an upstream Ollama manifest with the installed source, showing affected profiles and download estimates. A custom derived model's declared parent is used when available; unavailable upstream metadata leaves the operation pending.

Updates pull the selected source, retain the old resolved configuration alias, build a new alias with the profile's context/sampling settings, and verify a disposable edit before activating the replacement. Other profiles keep their resolved model references. Failed verification leaves the current profile active and downloaded artifacts available for inspection. Rollback checks that its retained artifact still exists with the expected digest before restoring it.

Old/new versions can occupy additional disk space, although identical layers remain shared. There is no automatic model deletion after an update. Removing a profile or explicitly detaching a model can discard its rollback references.

## Separate component and manager updates

```sh
loc update --component opencode --dry-run
loc update --component opencode
loc self update --check
loc self update
loc models refresh
```

Component updates use the detected installation owner, with no alternate-channel fallback. Active use blocks replacement. Some component owners do not provide a non-mutating version check; the preview reports availability as unknown and shows the route. Unsupported owners receive instructions rather than an invented updater.

Catalog refresh changes recommendation metadata, not installed models or profiles. loc's own distribution lifecycle is covered in [Installing and updating loc](distribution-and-updates.md).

## Limits

Complex custom model recipes, changed templates, adapters, and cross-runtime migrations are not reconstructed automatically. Supported numeric sampling overrides survive profile updates; custom source artifacts may still require their original recipe. Source-tag updates are visible to external users of that tag, while loc profiles continue using retained resolved aliases.

No background update scheduler or automatic installation is enabled. Check failures do not prevent running a working local profile. Native package replacement and recovery across Windows/Linux still require testing.

## Delivery evidence

Automated tests cover failed-update preservation, successful activation, retained references, rollback, and missing rollback artifacts. Real upstream model or agent updates were not applied to the user's existing environment during testing.
