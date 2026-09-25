"""Validated state, atomic persistence, and process coordination."""

from __future__ import annotations

import contextlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit


class LocError(Exception):
    """An actionable user error, without a traceback or sensitive subprocess output."""


def name(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", value):
        raise LocError("Names must use 1–64 letters, numbers, underscores, or hyphens.")
    return value


def model_name(value: str) -> str:
    if not isinstance(value, str) or len(value) > 180 or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9_.-]*(?:/[a-zA-Z0-9][a-zA-Z0-9_.-]*)?(?::[a-zA-Z0-9][a-zA-Z0-9_.-]*)?", value
    ):
        raise LocError("Use an Ollama model name, optionally namespace/name:tag; URLs and paths are not models.")
    if "cloud" in value.lower():
        raise LocError("Cloud models are outside loc's local-inference scope.")
    return value if ":" in value.rsplit("/", 1)[-1] else value + ":latest"


def endpoint(value: str) -> str:
    try:
        p = urlsplit(value)
        port = p.port
        valid = (p.scheme == "http" and p.hostname in {"127.0.0.1", "localhost", "::1"}
                 and port is not None and 1 <= port <= 65535 and not p.username and not p.password
                 and p.path in {"", "/"} and not p.query and not p.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise LocError("The runtime endpoint must be a loopback HTTP address with an explicit port.")
    host = "[::1]" if p.hostname == "::1" else "127.0.0.1"
    return f"http://{host}:{port}"


@dataclass
class Profile:
    name: str
    agent: str
    model: str
    context: int = 32768
    output_tokens: int = 4096
    map_tokens: int = 1024
    temperature: float = 0.2
    endpoint: str = "http://127.0.0.1:11434"
    runtime: str = "ollama"
    digest: str | None = None
    source_digest: str | None = None
    resolved_model: str | None = None
    state: str = "pending"
    rtk: bool = False
    parameters: dict = field(default_factory=dict)

    def validate(self) -> "Profile":
        name(self.name)
        if self.agent not in {"claude", "opencode", "aider"} or self.runtime != "ollama":
            raise LocError("Supported profiles pair claude, opencode, or aider with ollama.")
        self.model = model_name(self.model)
        self.endpoint = endpoint(self.endpoint)
        for key, low, high in [("context", 8192, 262144), ("output_tokens", 512, 32768), ("map_tokens", 0, 8192)]:
            val = getattr(self, key)
            if type(val) is not int or not low <= val <= high:
                raise LocError(f"{key} must be an integer between {low} and {high}.")
        if self.output_tokens + self.map_tokens + 4096 >= self.context:
            raise LocError("Context must leave at least 4096 tokens beyond output and repository-map budgets.")
        if type(self.temperature) not in {int, float} or not 0 <= self.temperature <= 2:
            raise LocError("temperature must be a number between 0 and 2.")
        if type(self.rtk) is not bool or self.state not in {"pending", "ready", "disabled"}:
            raise LocError("Invalid profile state or rtk setting.")
        allowed_parameters = {"top_k", "top_p", "min_p", "repeat_penalty", "repeat_last_n", "seed"}
        if not isinstance(self.parameters, dict) or set(self.parameters) - allowed_parameters:
            raise LocError("Only supported numeric sampling parameters may be included in a profile.")
        for key, value in self.parameters.items():
            if type(value) not in {int, float} or not -1 <= value <= 2 ** 32:
                raise LocError(f"Invalid sampling parameter: {key}")
        for digest in (self.digest, self.source_digest):
            if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest)):
                raise LocError("Invalid model digest.")
        if self.resolved_model is not None:
            self.resolved_model = model_name(self.resolved_model)
        return self

    @classmethod
    def parse(cls, data: dict) -> "Profile":
        try:
            return cls(**data).validate()
        except (TypeError, ValueError) as exc:
            raise LocError("Invalid profile fields; exports must contain declarative profile data only.") from exc

    def portable(self) -> dict:
        data = asdict(self)
        for key in ("endpoint", "resolved_model", "state", "digest"):
            data.pop(key)
        return {"schema": 1, "profile": data}


def home_dir() -> Path:
    if os.environ.get("LOC_HOME"):
        return Path(os.environ["LOC_HOME"]).expanduser().absolute()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "loc"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/loc"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "loc"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        if path.stat().st_size > 4 * 1024 * 1024:
            raise LocError(f"Configuration exceeds the 4 MiB limit: {path.name}")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LocError(f"Cannot read {path.name}; preserve it and repair the invalid configuration.") from exc


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".loc-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root or home_dir()
        self.path = self.root / "state.json"
        self._lock_depth = 0

    def read(self) -> dict:
        data = read_json(self.path, {"schema": 1, "profiles": {}, "components": {}, "models": {}, "history": {}, "default": None})
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise LocError("Unsupported loc state schema. Use a compatible loc version.")
        for key in ("profiles", "components", "models", "history"):
            if not isinstance(data.get(key), dict):
                raise LocError(f"Invalid state section: {key}")
        if data.get("default") is not None:
            name(data["default"])
        for key, value in data["profiles"].items():
            if Profile.parse(value).name != key:
                raise LocError("Profile name does not match its state key.")
        for key, entries in data["history"].items():
            name(key)
            if not isinstance(entries, list):
                raise LocError("Invalid rollback history.")
            for value in entries:
                Profile.parse(value)
        for key, value in data["models"].items():
            if not isinstance(value, dict) or type(value.get("installed_by_loc")) is not bool:
                raise LocError("Invalid model ownership record; cleanup is blocked.")
            if key != endpoint(value.get("endpoint")) + "|" + model_name(value.get("model")):
                raise LocError("Model ownership identity is inconsistent; cleanup is blocked.")
        for key, value in data["components"].items():
            name(key)
            if not isinstance(value, dict) or type(value.get("installed_by_loc", False)) is not bool:
                raise LocError("Invalid component ownership record.")
        return data

    def save(self, data: dict) -> None:
        atomic_json(self.path, data)

    @contextlib.contextmanager
    def lock(self, timeout: float = 10) -> Iterator[None]:
        if self._lock_depth:
            self._lock_depth += 1
            try:
                yield
            finally:
                self._lock_depth -= 1
            return
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / "operation.lock").open("a+b") as f:
            if f.tell() == 0:
                f.write(b"0")
                f.flush()
            deadline = time.monotonic() + timeout
            while True:
                try:
                    f.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LocError("Another loc operation is running. Retry after it finishes.")
                    time.sleep(0.1)
            self._lock_depth = 1
            try:
                yield
            finally:
                self._lock_depth = 0
                f.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_UN)

    def profile(self, selected: str | None, cwd: Path | None = None) -> Profile:
        data = self.read()
        selected = selected or project_default(cwd or Path.cwd()) or data.get("default")
        if not selected:
            raise LocError("Choose a profile: loc run NAME, or set a default with loc use NAME.")
        if selected not in data["profiles"]:
            raise LocError(f"Unknown profile: {selected}")
        return Profile.parse(data["profiles"][selected])


def project_root(cwd: Path) -> Path:
    for directory in [cwd, *cwd.parents]:
        if (directory / ".git").exists():
            return directory
    return cwd


def project_default(cwd: Path) -> str | None:
    for directory in [cwd, *cwd.parents]:
        config = directory / ".loc.json"
        if config.exists():
            data = read_json(config)
            if not isinstance(data, dict) or set(data) != {"schema", "profile"} or data["schema"] != 1:
                raise LocError(".loc.json may contain only schema: 1 and a profile name.")
            return name(data["profile"])
        if (directory / ".git").exists():
            break
    return None


def capture(args: list[str], timeout: float = 15, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LocError(f"Could not inspect {Path(args[0]).name}: {type(exc).__name__}.") from exc


def confirm(message: str, yes: bool = False) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise LocError(message + " Run interactively or supply --yes after reviewing --dry-run.")
    if input(message + " [y/N] ").strip().lower() not in {"y", "yes"}:
        raise LocError("Cancelled; no further changes made.")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("<redacted>" if re.search(r"secret|password|authorization|api.?key|auth.?token|cookie", k, re.I)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = value.replace(str(Path.home()), "~")
        value = re.sub(r"(?i)Bearer\s+\S+", "Bearer <redacted>", value)
        value = re.sub(r"(?i)([?&](?:token|key|secret|password)=)[^&\s]+", r"\1<redacted>", value)
    return value


def platform_name() -> str:
    return {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(platform.system(), "unsupported")
