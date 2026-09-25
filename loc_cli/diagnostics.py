"""Structured diagnostics without secrets, repository content, or subprocess logs."""

from __future__ import annotations

from dataclasses import asdict

from .agents import active_sessions, agent_version, run_profile
from .core import LocError, Profile, Store, redact
from .discovery import Discovery
from .hardware import inspect_hardware
from .ollama import Ollama, parameters


def status(store: Store, selected: str | None = None, base: str = "http://127.0.0.1:11434") -> dict:
    data = store.read()
    profiles = [asdict(store.profile(selected))] if selected else list(data["profiles"].values())
    endpoints = {row["endpoint"] for row in profiles} or {base}
    runtimes = {}
    for endpoint in sorted(endpoints):
        try:
            client = Ollama(endpoint)
            inventory = client.models()
            runtimes[endpoint] = {"status": "reachable", "version": client.version(), "loaded_models": client.loaded(), "models": inventory}
            for profile in profiles:
                if profile["endpoint"] == endpoint:
                    item = next((m for m in inventory if m["name"] == profile.get("resolved_model")), None)
                    profile["observed_digest"] = item["digest"] if item else None
                    profile["drift"] = item is None or item["digest"] != profile.get("digest")
        except LocError as exc:
            runtimes[endpoint] = {"status": "unavailable", "reason": str(exc)}
    return {"profiles": profiles, "runtimes": runtimes, "hardware": inspect_hardware(), "active_sessions": active_sessions(store)}


def doctor(store: Store, selected: str | None, *, verify: bool = False, timeout: int = 240, offline: bool = False) -> dict:
    data = store.read()
    profiles = [store.profile(selected)] if selected else [Profile.parse(x) for x in data["profiles"].values()]
    discovery = Discovery(store)
    checks = []
    if not profiles:
        return {"status": "pending", "checks": [], "next": "Create a profile with loc setup, or inspect loc scan."}
    for profile in profiles:
        row = {"profile": profile.name, "checks": []}
        try:
            install = discovery.detect(profile.agent).require()
            _, version = agent_version(install.path, profile.agent)
            row["checks"].append({"check": "agent", "status": "passed", "version": version})
            runtime = Ollama(profile.endpoint)
            row["checks"].append({"check": "runtime", "status": "passed", "endpoint": profile.endpoint, "version": runtime.version()})
            item, info = runtime.local_model(profile.resolved_model or profile.model)
            same = item["digest"] == profile.digest and profile.state == "ready"
            row["checks"].append({"check": "model identity", "status": "passed" if same else "failed",
                                  "expected": profile.digest, "observed": item["digest"], "model": item["name"]})
            params = parameters(info)
            row["checks"].append({"check": "configured context", "status": "passed" if params.get("num_ctx") == profile.context else "failed", "tokens": profile.context})
            if verify and same:
                row["checks"].append({"check": "agent file edit", **run_profile(store, profile, [], verify=True, timeout=timeout, offline=offline)})
            else:
                row["checks"].append({"check": "agent file edit", "status": "skipped", "reason": "Use --verify to load the model and exercise editing."})
        except LocError as exc:
            row["checks"].append({"check": "profile", "status": "failed", "reason": str(exc)})
        row["status"] = "failed" if any(x["status"] == "failed" for x in row["checks"]) else "passed"
        checks.append(row)
    return {"status": "failed" if any(x["status"] == "failed" for x in checks) else "passed", "profiles": checks}


def report(store: Store, result: dict) -> dict:
    # Deliberately allowlist report content. Do not include environment, commands, raw logs, or arbitrary state.
    hardware = inspect_hardware()
    hardware.pop("disk_location", None)
    hardware["gpus"] = [{k: v for k, v in gpu.items() if k in {"name", "memory_bytes", "shared_memory"}} for gpu in hardware["gpus"]]
    return redact({"schema": 1, "diagnostics": result, "hardware": hardware,
                   "sharing": "This report is stored locally. Inspect it before sharing; loc never uploads it."})
