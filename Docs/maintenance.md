# Maintenance

State: not implemented

## Confirmed intent

Maintain local coding-agent setups and update models when needed through simple commands.

## Proposed behavior for review

- Report available changes before changing a working profile.
- Distinguish an update to an existing model artifact from replacement with a different recommended model.
- Allow an update to target a named profile and identify other affected profiles sharing dependencies.
- Keep catalog refreshes, model updates, agent updates, and runtime updates distinguishable.
- Preserve the prior configuration and required model artifacts until the replacement has been validated.
- Rebuild derived model configurations when their base artifact changes.
- Validate that an updated profile can load and work with its selected agent before activating it.
- Provide rollback to a retained working profile configuration.
- Report interrupted or failed updates without describing the profile as successfully updated.

## Illustrative CLI

These commands express proposed behavior only:

```sh
loc update --check
loc update claude-next
loc rollback claude-next
```

## Limits and open decisions

- An update may require additional disk space for both old and new model artifacts.
- Recording an old artifact identifier does not guarantee rollback unless the artifact remains available.
- Shared model and runtime changes must account for dependent profiles and active sessions.
- Automatic deletion of models or replacement of active configurations is not an approved default.
- Scheduled updates, agent/runtime installation ownership, retention policy, update checks, and cleanup behavior remain undecided.
- Exact version-pinning and rollback mechanisms depend on the selected runtime and remain undecided.

## Delivery evidence

None. Update detection, replacement validation, and rollback are not implemented.
