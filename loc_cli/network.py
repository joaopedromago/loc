"""Explicit online metadata operations. Ordinary launches never call these."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from urllib.parse import quote

from .core import LocError, model_name


REPOSITORY = "joaopedromago/loc"


def fetch(url: str, *, maximum: int = 4 * 1024 * 1024) -> tuple[bytes, dict]:
    if not url.startswith("https://"):
        raise LocError("Online metadata must use HTTPS.")
    request = urllib.request.Request(url, headers={"User-Agent": "loc-coding/0.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if not response.url.startswith("https://"):
                raise LocError("Refusing a non-HTTPS download redirect.")
            data = response.read(maximum + 1)
            if len(data) > maximum:
                raise LocError("The download exceeds its size limit.")
            return data, dict(response.headers.items())
    except (urllib.error.URLError, OSError) as exc:
        raise LocError("Online metadata is unavailable. Existing local profiles remain usable.") from exc


def remote_manifest(model: str) -> dict:
    model = model_name(model)
    repository, tag = model.rsplit(":", 1)
    if "/" not in repository:
        repository = "library/" + repository
    raw, headers = fetch(f"https://registry.ollama.ai/v2/{quote(repository, safe='/')}/manifests/{quote(tag, safe='')}")
    try:
        data = json.loads(raw)
        layers = data["layers"]
        if not isinstance(layers, list) or any(type(layer.get("size")) is not int or layer["size"] < 0 for layer in layers):
            raise ValueError()
        return {"model": model, "digest": hashlib.sha256(raw).hexdigest(), "download_bytes": sum(layer["size"] for layer in layers),
                "layers": [{"digest": layer["digest"], "size": layer["size"]} for layer in layers]}
    except (ValueError, KeyError, TypeError) as exc:
        raise LocError("Invalid upstream model manifest; update remains pending.") from exc
