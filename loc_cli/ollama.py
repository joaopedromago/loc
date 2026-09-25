"""Ollama's local API. Never follow redirects or inherit HTTP proxies."""

from __future__ import annotations

import hashlib
import json
import socket
import shlex
import urllib.error
import urllib.request
from typing import Callable

from .core import LocError, endpoint, model_name


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocError("The local runtime attempted an HTTP redirect; request blocked.")


def parameters(info: dict) -> dict:
    result = {}
    for line in info.get("parameters", "").splitlines():
        try:
            parts = shlex.split(line)
            if len(parts) == 2:
                try:
                    value = json.loads(parts[1])
                except ValueError:
                    value = parts[1]
                result[parts[0]] = value
        except ValueError:
            continue
    return result


class Ollama:
    def __init__(self, base: str = "http://127.0.0.1:11434", timeout: float = 10):
        self.base = endpoint(base)
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def open(self, path: str, data: dict | None = None, method: str | None = None, timeout: float | None = None):
        request = urllib.request.Request(self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"}, method=method)
        try:
            return self.opener.open(request, timeout=timeout or self.timeout)
        except urllib.error.HTTPError as exc:
            # Upstream bodies can contain prompts or private paths; never expose them by default.
            raise LocError(f"Ollama returned HTTP {exc.code} for {path}. Check 'loc doctor'.") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise LocError(f"Cannot reach Ollama at {self.base}. Start the existing runtime with 'loc runtime start'.") from exc

    def request(self, path: str, data: dict | None = None, method: str | None = None) -> dict:
        with self.open(path, data, method) as response:
            try:
                value = json.load(response)
                if not isinstance(value, dict) or value.get("error"):
                    raise ValueError("unexpected response")
                return value
            except (ValueError, TypeError) as exc:
                raise LocError("The runtime returned an invalid API response.") from exc

    def version(self) -> str:
        return self.request("/api/version").get("version", "unknown")

    def models(self) -> list[dict]:
        value = self.request("/api/tags").get("models")
        if not isinstance(value, list):
            raise LocError("Ollama did not return a model inventory; presence is unknown.")
        return value

    def recommendation_inventory(self) -> list[dict]:
        """Read local capability metadata without loading models or changing the runtime."""
        result = []
        for item in self.models():
            if item["name"].startswith("loc-"):
                continue
            if item.get("remote_host") or item.get("remote_model") or not item.get("size"):
                result.append({**item, "local_verified": False})
                continue
            try:
                info = self.show(item["name"])
            except LocError:
                # Do not use catalog capability claims for an installed but unverified model.
                result.append({**item, "local_verified": False})
                continue
            if info.get("remote_host") or info.get("remote_model") or "completion" not in info.get("capabilities", []):
                result.append({**item, "local_verified": False})
                continue
            maximum = [v for k, v in info.get("model_info", {}).items()
                       if k.endswith(".context_length") and type(v) is int and v > 0]
            details = dict(item.get("details", {}))
            if maximum:
                details["context_length"] = max(maximum)
            result.append({**item, "local_verified": True, "capabilities": info.get("capabilities", []), "details": details})
        return result

    def loaded(self) -> list[dict]:
        return self.request("/api/ps").get("models", [])

    def find(self, name: str) -> dict | None:
        target = model_name(name)
        return next((m for m in self.models() if model_name(m.get("name", m.get("model", ""))) == target), None)

    def show(self, name: str) -> dict:
        return self.request("/api/show", {"model": model_name(name)})

    def local_model(self, name: str) -> tuple[dict, dict]:
        item = self.find(name)
        if item is None:
            raise LocError(f"Model is not installed: {name}. Run 'loc setup' to obtain it.")
        info = self.show(name)
        if info.get("remote_host") or info.get("remote_model") or item.get("remote_host") or not item.get("size", 0):
            raise LocError("This model redirects to hosted inference or has no local weights.")
        if "completion" not in info.get("capabilities", item.get("capabilities", [])):
            raise LocError("The model does not expose completion capability.")
        return item, info

    def stream(self, route: str, data: dict, progress: Callable[[dict], None] | None = None) -> dict:
        final = {}
        with self.open(route, {**data, "stream": True}, timeout=300) as response:
            for line in response:
                if not line.strip():
                    continue
                try:
                    final = json.loads(line)
                except ValueError as exc:
                    raise LocError("Interrupted or invalid progress response; retry setup to resume.") from exc
                if final.get("error"):
                    raise LocError("Ollama could not complete the operation. Check available disk space and the exact model name; retry to resume.")
                if progress:
                    progress({k: final[k] for k in ("status", "total", "completed") if k in final})
        if final.get("status") != "success":
            raise LocError("The runtime did not confirm completion. The operation remains pending.")
        return final

    def pull(self, name: str, progress: Callable | None = None) -> None:
        self.stream("/api/pull", {"model": model_name(name)}, progress)
        self.local_model(name)

    def configured(self, source: str, context: int, temperature: float, progress: Callable | None = None, sampling: dict | None = None) -> tuple[str, str, bool]:
        item, info = self.local_model(source)
        identity = json.dumps([item["digest"], context, temperature, sampling or {}], separators=(",", ":"), sort_keys=True)
        target = "loc-" + hashlib.sha256(identity.encode()).hexdigest()[:20] + ":latest"
        existing = self.find(target)
        created = existing is None
        if created:
            # Ollama shares content-addressed weight blobs. This creates configuration metadata only.
            self.stream("/api/create", {"model": target, "from": model_name(source),
                        "parameters": {**(sampling or {}), "num_ctx": context, "temperature": temperature}}, progress)
        else:
            params = parameters(self.show(target))
            if params.get("num_ctx") != context or params.get("temperature") != temperature or any(params.get(k) != v for k, v in (sampling or {}).items()):
                raise LocError("A conflicting managed model name exists; refusing to overwrite it.")
        resolved, _ = self.local_model(target)
        return target, resolved["digest"], created

    def copy(self, source: str, target: str) -> None:
        if self.find(target):
            raise LocError("The rollback reference already exists; refusing to replace it.")
        self.request("/api/copy", {"source": model_name(source), "destination": model_name(target)})

    def delete(self, name: str) -> None:
        self.request("/api/delete", {"model": model_name(name)}, "DELETE")

    def chat(self, model: str, prompt: str, context: int) -> dict:
        with self.open("/api/chat", {"model": model, "messages": [{"role": "user", "content": prompt}],
                                   "stream": False, "think": False, "options": {"num_ctx": context, "num_predict": 128}}, timeout=180) as response:
            return json.load(response)
