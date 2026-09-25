"""Conservative estimates, never benchmark claims."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import shutil
from pathlib import Path

from .core import LocError, Store, atomic_json, capture, model_name, platform_name, read_json

GIB = 1024 ** 3
DEFAULT_AGENT = "claude"


def is_qwen_coder(model: str) -> bool:
    family = model_name(model).split(":", 1)[0].rsplit("/", 1)[-1]
    return re.match(r"^qwen[0-9.]*-coder(?:-|$)", family, re.IGNORECASE) is not None


def coding_priority(model: str, rows: list[dict]) -> int:
    """Keep catalog family priorities for installed tags and custom configuration aliases."""
    family = model.split(":", 1)[0].rsplit("/", 1)[-1]
    matches = []
    for row in rows:
        known_family = row["model"].split(":", 1)[0]
        if family == known_family or family.startswith(known_family + "-"):
            matches.append((len(known_family), row["coding_priority"]))
    return max(matches, default=(0, 3 if "coder" in model or "glm" in model else 1))[1]


def inspect_hardware(path: Path | None = None) -> dict:
    system = platform_name()
    memory, available, gpus = None, None, []
    try:
        if system == "macos":
            memory = int(capture(["/usr/sbin/sysctl", "-n", "hw.memsize"]).stdout.strip())
            if platform.machine() == "arm64":
                gpus = [{"name": "Apple Silicon", "memory_bytes": memory, "shared_memory": True}]
            vm = capture(["/usr/bin/vm_stat"]).stdout
            import re
            page = int(re.search(r"page size of (\d+)", vm).group(1))
            available = sum(int(re.search(label + r":\s+(\d+)", vm).group(1))
                            for label in ["Pages free", "Pages inactive"]) * page
        elif system == "linux":
            values = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines()}
            memory, available = values.get("MemTotal"), values.get("MemAvailable")
        elif system == "windows":
            class Memory(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in
                            ["total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended"]]
            info = Memory()
            info.length = ctypes.sizeof(info)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info)):
                memory, available = info.total, info.available
    except (LocError, OSError, ValueError, AttributeError):
        pass
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        try:
            r = capture([nvidia, "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"])
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    gpu, total, free = [x.strip() for x in line.split(",")]
                    gpus.append({"name": gpu, "memory_bytes": int(total) * 1024 ** 2,
                                 "available_bytes": int(free) * 1024 ** 2, "shared_memory": False})
        except (LocError, ValueError):
            pass
    target = path or Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama/models"))
    while not target.exists() and target != target.parent:
        target = target.parent
    try:
        disk_free = shutil.disk_usage(target).free
    except OSError:
        disk_free = None
    return {"platform": system, "architecture": platform.machine(), "logical_cpus": os.cpu_count(),
            "memory_bytes": memory, "available_memory_bytes": available, "gpus": gpus,
            "disk_free_bytes": disk_free, "disk_location": str(target),
            "limits": "Available memory is a snapshot. CPU speed, AMD/Intel accelerator capacity, runtime buffers, and KV cache fit require local validation."}


def catalog(store: Store) -> dict:
    data = read_json(store.root / "catalog.json")
    return validate_catalog(data or json.loads(Path(__file__).with_name("catalog.json").read_text()))


def validate_catalog(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("models"), list):
        raise LocError("Unsupported model catalog schema.")
    if not isinstance(data.get("updated"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["updated"]):
        raise LocError("The model catalog must include a valid freshness date.")
    if len(data["models"]) > 200:
        raise LocError("Model catalog is too large.")
    for row in data["models"]:
        if not isinstance(row, dict) or set(row) != {"model", "bytes", "context", "coding_priority", "tools", "source"}:
            raise LocError("Invalid model catalog entry.")
        model_name(row["model"])
        if any(type(row[k]) is not int or row[k] <= 0 for k in ("bytes", "context", "coding_priority")) or type(row["tools"]) is not bool:
            raise LocError("Invalid catalog estimates.")
        if not row["source"].startswith("https://ollama.com/library/"):
            raise LocError("Catalog entries must reference the upstream Ollama library.")
    return data


def recommend(store: Store, agent: str, installed: list[dict], context: int = 32768, preference: str = "balanced", hardware: dict | None = None) -> dict:
    hardware = hardware or inspect_hardware()
    data = catalog(store)
    candidates = {model_name(row["model"]): dict(row, installed=False) for row in data["models"]}
    for item in installed:
        model = model_name(item["name"])
        if model.startswith("loc-") or item.get("remote_host") or item.get("remote_model") or not item.get("size") or item.get("local_verified") is False:
            candidates.pop(model, None)
            continue
        known = candidates.get(model, {})
        candidates[model] = {"model": model, "bytes": item["size"],
            "context": item.get("details", {}).get("context_length", known.get("context", 32768)),
            "coding_priority": known.get("coding_priority", coding_priority(model, data["models"])),
            "tools": "tools" in item.get("capabilities", []) if "capabilities" in item else known.get("tools"),
            "source": known.get("source", "installed runtime inventory"), "installed": True}
    memory = hardware["memory_bytes"]
    budget = max(0, memory - max(4 * GIB, memory * 0.25)) if memory else None
    results = []
    for row in candidates.values():
        if agent != "aider" and row.get("tools") is not True:
            continue
        selected_context = min(context, row["context"])
        estimate = int(row["bytes"] * 1.15 + selected_context / 32768 * 2 * GIB)
        fits = estimate <= budget if budget is not None else None
        row.update({"context": selected_context, "estimated_memory_bytes": estimate, "fits_estimate": fits,
                    "preferred_pairing": agent == DEFAULT_AGENT and is_qwen_coder(row["model"]),
                    "reason": "Weights plus conservative runtime/cache estimate; quality and throughput are not benchmarked."})
        gpu_capacity = max((gpu.get("memory_bytes", 0) for gpu in hardware.get("gpus", [])), default=0)
        row["accelerator_fit_estimate"] = estimate <= gpu_capacity * 0.9 if gpu_capacity else None
        row["execution_note"] = "Full accelerator placement estimated" if row["accelerator_fit_estimate"] else "CPU execution or partial offload may be needed; throughput is unmeasured"
        row["rank"] = 8 if row["installed"] else 0
        row["rank"] += (-row["bytes"] / GIB if preference == "speed" else row["coding_priority"] * 5)
        results.append(row)
    results.sort(key=lambda row: ({True: 2, None: 1, False: 0}[row["fits_estimate"]],
                                 row["preferred_pairing"], row.pop("rank")), reverse=True)
    preferred = next((row for row in results if row["preferred_pairing"] and row["fits_estimate"] is True), None)
    return {"agent": agent, "runtime": "ollama", "hardware": hardware, "catalog_updated": data["updated"], "memory_budget_bytes": budget,
            "preferred_model": preferred["model"] if preferred else None,
            "selection_note": ("Preferred setup: Claude Code with a local Qwen Coder model. Memory fit and tool support come first."
                               + (" No compatible Qwen Coder candidate has a positive fit estimate; select an alternative explicitly." if not preferred else ""))
                               if agent == DEFAULT_AGENT else "Using the explicitly selected agent; compatible alternatives remain available.",
            "recommendations": results, "qualification": "Estimated candidates, not a guarantee of best quality or fit. Run doctor --verify after setup."}
