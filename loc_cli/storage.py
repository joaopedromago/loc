"""Physical storage accounting only when local manifests match runtime identities."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path


def physical_storage(models: list[dict], root: Path | None = None) -> dict:
    root = root or Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama/models"))
    result = {"verified_location": None, "allocated_bytes": None, "logical_blob_bytes": None, "partial_download_bytes": None,
              "note": "Storage is unverified until local manifests match the runtime's model identities."}
    if not models or not root.is_dir():
        return result
    try:
        for item in models:
            repository, tag = item["name"].rsplit(":", 1)
            if "/" not in repository:
                repository = "library/" + repository
            manifest = root / "manifests/registry.ollama.ai" / repository / tag
            if not manifest.is_file() or hashlib.sha256(manifest.read_bytes()).hexdigest() != item["digest"].removeprefix("sha256:"):
                return result
        seen = set()
        allocated = logical = partial = 0
        for path in (root / "blobs").iterdir():
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                result["note"] = "External blob symlinks prevent reliable physical accounting. Shared weights are preserved."
                return result
            if not stat.S_ISREG(info.st_mode):
                continue
            identity = (info.st_dev, info.st_ino)
            if identity in seen:
                continue
            seen.add(identity)
            logical += info.st_size
            allocated += getattr(info, "st_blocks", (info.st_size + 511) // 512) * 512
            if "partial" in path.name:
                partial += info.st_size
        return {"verified_location": str(root), "allocated_bytes": allocated, "logical_blob_bytes": logical,
                "partial_download_bytes": partial, "note": "Shared blob files and hardlinks counted once. Partial downloads may belong to other tools and are preserved."}
    except (OSError, ValueError, KeyError):
        return result
