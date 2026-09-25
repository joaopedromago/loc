"""Recoverable setup, explicit updates, rollback, and reference-aware removal."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .agents import active_sessions, agent_version, run_profile
from .core import LocError, Profile, Store, confirm, model_name
from .discovery import Discovery, TECHNOLOGIES
from .hardware import GIB, catalog, inspect_hardware
from .install import Installer, start_runtime
from .network import remote_manifest
from .ollama import Ollama, parameters
from .storage import physical_storage


def progress(event: dict):
    if sys.stderr.isatty():
        status = event.get("status", "working")
        if event.get("total"):
            status += f" {event.get('completed', 0) * 100 / event['total']:.0f}%"
        print("\r" + str(status)[:120].ljust(120), end="", file=sys.stderr, flush=True)


def references(data: dict, model: str, endpoint: str | None = None) -> list[str]:
    found = []
    for key, row in data["profiles"].items():
        if (endpoint is None or row["endpoint"] == endpoint) and model in {row["model"], row.get("resolved_model")}:
            found.append(key)
    for key, records in data["history"].items():
        if any((endpoint is None or row["endpoint"] == endpoint) and model in {row["model"], row.get("resolved_model")} for row in records):
            found.append(key + " (rollback)")
    return found


def no_active(store: Store, *, profile: str | None = None, component: str | None = None, model: str | None = None):
    for item in active_sessions(store):
        if (profile and item.get("profile") == profile) or (component and (item.get("agent") == component or component == "ollama")) or (model and item.get("model") == model):
            raise LocError("The target is used by an active loc session. Finish that session before changing it.")


def model_key(base: str, model: str) -> str:
    return base + "|" + model_name(model)


class Lifecycle:
    def __init__(self, store: Store):
        self.store = store
        self.discovery = Discovery(store)
        self.installer = Installer(store, self.discovery)

    def setup_plan(self, profile: Profile) -> dict:
        profile.validate()
        tools = [self.installer.plan("ollama"), self.installer.plan(profile.agent)]
        if profile.rtk:
            tools.append(self.installer.plan("rtk"))
        runtime = Ollama(profile.endpoint)
        existing, runtime_error = None, None
        try:
            existing = runtime.find(profile.model)
            if tools[0]["action"] not in {"reuse", "reuse service"}:
                tools[0] = {"component": "ollama", "action": "reuse service", "endpoint": profile.endpoint}
        except LocError as exc:
            runtime_error = str(exc)
        estimate = next((x["bytes"] for x in catalog(self.store)["models"] if model_name(x["model"]) == profile.model), None)
        download = 0 if existing else estimate
        hardware = inspect_hardware()
        return {"profile": asdict(profile), "components": tools, "model_action": "reuse" if existing else "inspect after runtime startup" if runtime_error else "pull missing model",
                "runtime_error": runtime_error, "estimated_download_bytes": download,
                "estimated_required_disk_bytes": int(download * 1.1 + 256 * 1024 ** 2) if download else 0 if existing else None,
                "disk_free_bytes": hardware["disk_free_bytes"], "estimate_note": "Conservative catalog estimate; Ollama reuses existing content-addressed layers. Unknown installer sizes are excluded.",
                "context": profile.context, "configuration": "Per-session agent settings and a shared-layer Ollama configuration alias."}

    def setup(self, profile: Profile, *, yes: bool = False, offline: bool = False, accept_model_change: bool = False) -> dict:
        profile.validate()
        data = self.store.read()
        existing = data["profiles"].get(profile.name)
        if existing:
            old = Profile.parse(existing)
            fields = ("agent", "model", "context", "output_tokens", "map_tokens", "temperature", "endpoint", "rtk")
            if any(getattr(old, k) != getattr(profile, k) for k in fields):
                raise LocError("This profile already exists with different settings. Create a new named profile instead of overwriting it.")
        no_active(self.store, profile=profile.name)
        plan = self.setup_plan(profile)
        if plan["estimated_required_disk_bytes"] and plan["disk_free_bytes"] is not None and plan["estimated_required_disk_bytes"] > plan["disk_free_bytes"]:
            raise LocError("Estimated disk space is insufficient for the download and temporary files.")
        confirm(f"Set up {profile.name}, reusing existing components and obtaining only missing ones?", yes)
        if not existing:
            data["profiles"][profile.name] = asdict(profile)
            self.store.save(data)
        try:
            Ollama(profile.endpoint).version()
            service_available = True
        except LocError:
            service_available = False
        if service_available and not any(i.executable for i in self.discovery.detect("ollama").installations):
            data = self.store.read()
            data["components"]["ollama"] = {"path": None, "owner": "unknown", "endpoint": profile.endpoint, "installed_by_loc": False}
            self.store.save(data)
        else:
            self.installer.ensure("ollama", yes=yes, offline=offline)
        self.installer.ensure(profile.agent, yes=yes, offline=offline)
        if profile.rtk:
            self.installer.ensure("rtk", yes=yes, offline=offline)
        agent_version(self.discovery.detect(profile.agent, refresh=True).require().path, profile.agent)
        runtime = Ollama(profile.endpoint)
        try:
            runtime.version()
        except LocError:
            if offline:
                raise LocError("Start the existing runtime before an offline setup.")
            start_runtime(self.store, profile.endpoint)
        item = runtime.find(profile.model)
        pulled = item is None
        if pulled:
            if offline:
                raise LocError("The selected model is not installed; offline setup remains pending.")
            confirm(f"Download missing {profile.model}? Existing layers will be reused.", yes)
            runtime.pull(profile.model, progress)
            data = self.store.read()
            pulled_item = runtime.find(profile.model)
            data["models"][model_key(profile.endpoint, profile.model)] = {"model": profile.model, "endpoint": profile.endpoint,
                                                                        "installed_by_loc": True, "size": pulled_item.get("size")}
            self.store.save(data)
        item, info = runtime.local_model(profile.model)
        if profile.source_digest and profile.source_digest != item["digest"] and not accept_model_change:
            raise LocError("The imported profile's source digest differs. Review the model, then use --accept-model-change if intended.")
        if profile.agent != "aider" and "tools" not in info.get("capabilities", item.get("capabilities", [])):
            raise LocError("This agent requires a model with tool support. Choose a compatible model or use Aider.")
        maximum = [v for k, v in info.get("model_info", {}).items() if k.endswith(".context_length") and isinstance(v, int)]
        if maximum and profile.context > max(maximum):
            raise LocError("The profile context exceeds the model's declared context capacity.")
        inherited = {k: v for k, v in parameters(info).items() if k in {"top_k", "top_p", "min_p", "repeat_penalty", "repeat_last_n", "seed"}}
        profile.parameters = {**inherited, **profile.parameters}
        profile.validate()
        resolved, digest, created = runtime.configured(profile.model, profile.context, profile.temperature, progress, sampling=profile.parameters)
        profile.resolved_model, profile.digest, profile.source_digest, profile.state = resolved, digest, item["digest"], "ready"
        data = self.store.read()
        data["profiles"][profile.name] = asdict(profile)
        if not data.get("default"):
            data["default"] = profile.name
        for name, owned, size in [(profile.model, pulled, item.get("size")), (resolved, created, item.get("size"))]:
            key = model_key(profile.endpoint, name)
            prior = data["models"].get(key, {})
            data["models"][key] = {"model": name, "endpoint": profile.endpoint, "installed_by_loc": owned or prior.get("installed_by_loc", False), "size": size}
        self.store.save(data)
        return {"profile": asdict(profile), "status": "ready", "verification": "Run loc doctor NAME --verify to exercise the agent's editing protocol."}

    def update_check(self, profile: Profile) -> dict:
        runtime = Ollama(profile.endpoint)
        item, info = runtime.local_model(profile.model)
        source = profile.model
        parent = item.get("details", {}).get("parent_model") or info.get("details", {}).get("parent_model")
        if parent:
            source = model_name(parent)
        remote = remote_manifest(source)
        installed = runtime.find(source)
        installed_digest = installed["digest"] if installed else (profile.source_digest if source == profile.model else None)
        return {"profile": profile.name, "source": source, "derived_from": parent,
                "current_digest": installed_digest, "latest_digest": remote["digest"],
                "update_available": installed_digest != remote["digest"] if installed_digest else None,
                "estimated_download_bytes": remote["download_bytes"], "affected_profiles": references(self.store.read(), profile.model, profile.endpoint),
                "note": "Actual download excludes shared layers. Old configurations remain available for rollback."}

    def update(self, profile: Profile, *, yes: bool = False) -> dict:
        no_active(self.store, profile=profile.name)
        check = self.update_check(profile)
        if check["update_available"] is False:
            return {**check, "status": "up to date"}
        confirm(f"Update {profile.name}, retaining its current configuration until verification passes?", yes)
        hardware = inspect_hardware()
        if hardware["disk_free_bytes"] is not None and check["estimated_download_bytes"] * 1.1 > hardware["disk_free_bytes"]:
            raise LocError("Insufficient estimated space to retain the old artifact during the update.")
        runtime = Ollama(profile.endpoint)
        # The managed resolved model keeps the old blobs reachable; only this profile changes after verification.
        runtime.pull(check["source"], progress)
        source_item, _ = runtime.local_model(check["source"])
        replacement = copy.deepcopy(profile)
        replacement.model = check["source"]
        replacement.source_digest = source_item["digest"]
        replacement.resolved_model, replacement.digest, created = runtime.configured(replacement.model, profile.context, profile.temperature, progress, sampling=profile.parameters)
        evidence = run_profile(self.store, replacement, [], verify=True)
        if evidence.get("status") != "passed":
            raise LocError("Updated model failed the disposable editing check; the existing profile remains active. Downloaded artifacts are retained for inspection.")
        data = self.store.read()
        data["history"].setdefault(profile.name, []).append(asdict(profile))
        data["profiles"][profile.name] = asdict(replacement)
        data["models"][model_key(profile.endpoint, replacement.resolved_model)] = {"model": replacement.resolved_model,
            "endpoint": profile.endpoint, "installed_by_loc": created, "size": source_item["size"]}
        self.store.save(data)
        return {"status": "updated", "profile": asdict(replacement), "verification": evidence}

    def rollback(self, selected: str, yes: bool = False) -> dict:
        data = self.store.read()
        records = data["history"].get(selected, [])
        if not records:
            raise LocError("No retained profile configuration is available for rollback.")
        no_active(self.store, profile=selected)
        previous = Profile.parse(records[-1])
        item, _ = Ollama(previous.endpoint).local_model(previous.resolved_model)
        if item["digest"] != previous.digest:
            raise LocError("The retained model changed or is unavailable; rollback cannot be guaranteed.")
        confirm(f"Restore the retained configuration for {selected}?", yes)
        current = data["profiles"][selected]
        data["profiles"][selected] = records.pop()
        records.append(current)
        self.store.save(data)
        return {"status": "rolled back", "profile": selected, "model": previous.resolved_model}

    def remove_profile(self, selected: str, *, yes: bool = False, dry_run: bool = False) -> dict:
        data = self.store.read()
        if selected not in data["profiles"]:
            raise LocError("Unknown profile.")
        if not dry_run:
            no_active(self.store, profile=selected)
        result = {"profile": selected, "action": "remove profile and its rollback references", "preserved": "All installed tools and model artifacts; repository defaults may need updating."}
        if not dry_run:
            confirm(f"Remove profile {selected}, keeping its tools and models?", yes)
            data["profiles"].pop(selected)
            data["history"].pop(selected, None)
            if data.get("default") == selected:
                data["default"] = None
            self.store.save(data)
        return result

    def uninstall(self, kind: str, target: str, base: str, *, dry_run=False, yes=False, detach=False) -> dict:
        data = self.store.read()
        if kind == "model":
            target = model_name(target)
            runtime = Ollama(base)
            item = runtime.find(target)
            if item is None:
                return {"model": target, "action": "already absent"}
            refs = references(data, target, base)
            loaded = any(model_name(x["name"]) == target for x in runtime.loaded())
            plan = {"model": target, "action": "delete model reference", "references": refs, "loaded": loaded,
                    "installed_by_loc": data["models"].get(model_key(base, target), {}).get("installed_by_loc", False),
                    "reclaimable_bytes": None, "note": "Shared layers remain while other runtime models reference them. External usage is unknown."}
        else:
            if target not in TECHNOLOGIES or TECHNOLOGIES[target].kind != kind:
                raise LocError("Target does not match a supported component kind.")
            if not dry_run:
                no_active(self.store, component=target)
            plan = self.installer.removal_plan(target)
            refs = [key for key, p in data["profiles"].items() if target in {p["agent"], p["runtime"]} or target == "rtk" and p.get("rtk")]
            loaded = False
            if target == "ollama":
                try:
                    loaded = bool(Ollama(base).loaded())
                except LocError:
                    # A stopped runtime is still installed. The component remover independently
                    # inspects live processes before changing its installation.
                    loaded = None
            plan.update({"references": refs, "loaded": loaded})
        if dry_run:
            return plan
        no_active(self.store, model=target)
        if loaded:
            raise LocError("The target is loaded or serving an active workload. loc will not unload it implicitly.")
        if refs and not detach:
            raise LocError("Profiles or rollback records reference this target. Review --dry-run and use --detach to disable affected profiles and discard affected rollback references.")
        confirm(f"Remove exactly {target}? Affected references: {', '.join(refs) or 'none known'}.", yes)
        if detach:
            for ref in refs:
                key = ref.removesuffix(" (rollback)")
                if key in data["profiles"]:
                    data["profiles"][key]["state"] = "disabled"
            for key, values in list(data["history"].items()):
                data["history"][key] = [p for p in values if target not in {p.get("model"), p.get("resolved_model"), p["agent"], p["runtime"]}]
            self.store.save(data)
        if kind == "model":
            if runtime.find(target)["digest"] != item["digest"] or any(model_name(x["name"]) == target for x in runtime.loaded()):
                raise LocError("Model state changed; review removal again.")
            runtime.delete(target)
            if runtime.find(target):
                raise LocError("The runtime did not confirm model removal.")
            data = self.store.read()
            data["models"].pop(model_key(base, target), None)
            self.store.save(data)
            return {**plan, "status": "removed"}
        return self.installer.remove(target, yes=True)

    def storage(self, base: str) -> dict:
        data = self.store.read()
        rows = []
        inventory = Ollama(base).models()
        for item in inventory:
            key = model_key(base, item["name"])
            rows.append({"model": item["name"], "logical_bytes": item.get("size"), "digest": item.get("digest"),
                         "references": references(data, item["name"], base),
                         "installed_by_loc": data["models"].get(key, {}).get("installed_by_loc", False)})
        physical = physical_storage(inventory)
        return {"models": rows, "total_physical_bytes": physical["allocated_bytes"], "storage": physical,
                "note": "Logical model sizes share blobs and must not be summed. Reclaimable bytes remain unknown until the runtime removes unreferenced blobs."}

    def clean(self, base: str, *, dry_run: bool = True, yes: bool = False) -> dict:
        report = self.storage(base)
        loaded = {model_name(x["name"]) for x in Ollama(base).loaded()}
        candidates = [row["model"] for row in report["models"] if row["installed_by_loc"] and not row["references"] and row["model"] not in loaded]
        result = {"candidates": candidates, "preserved": "Reused models, all software installations, referenced/loaded artifacts, and runtime partial downloads of unknown ownership.", "reclaimable_bytes": None}
        if not dry_run and candidates:
            confirm("Remove these unreferenced loc-created model references: " + ", ".join(candidates) + "?", yes)
            for candidate in candidates:
                self.uninstall("model", candidate, base, yes=True)
        return result
