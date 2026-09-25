"""Installation and removal routes; existing components never enter installation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
import json
import re
from pathlib import Path

from .core import LocError, Store, capture, confirm, platform_name
from .discovery import Discovery, TECHNOLOGIES
from .ollama import Ollama
from .network import fetch


class Installer:
    def __init__(self, store: Store, discovery: Discovery | None = None):
        self.store = store
        self.discovery = discovery or Discovery(store)

    def plan(self, key: str) -> dict:
        detection = self.discovery.detect(key)
        if key == "ollama" and not any(item.executable for item in detection.installations):
            try:
                version = Ollama().version()
                return {"component": key, "action": "reuse service", "endpoint": "http://127.0.0.1:11434", "version": version,
                        "detection": detection.to_dict(), "note": "An existing local runtime is reachable; no installation is needed."}
            except LocError:
                pass
        if detection.installations:
            return {"component": key, "action": "reuse", "detection": detection.to_dict()}
        if detection.status != "absent":
            return {"component": key, "action": "pending", "detection": detection.to_dict()}
        tech = TECHNOLOGIES[key]
        command, owner = None, "manual"
        if platform_name() == "macos" and shutil.which("brew") and tech.brew:
            # Casks are standalone apps. Formula dependency graphs may duplicate native dependencies.
            if tech.cask or key in {"rtk", "llmfit"}:
                command = [shutil.which("brew"), "install", *(["--cask"] if tech.cask else []), tech.brew]
                owner = "brew-cask" if tech.cask else "brew"
        elif platform_name() == "windows" and shutil.which("winget") and tech.winget:
            command = [shutil.which("winget"), "install", "--exact", "--id", tech.winget, "--source", "winget", "--disable-interactivity"]
            owner = "winget"
        if key == "aider":
            # Reuse an interpreter; never let an installer fetch another Python automatically.
            python = existing_aider_python()
            if python is None:
                return {"component": key, "action": "pending", "detection": detection.to_dict(),
                        "reason": "Aider needs an existing compatible Python (3.10–3.12 for this integration). No second interpreter will be installed automatically."}
            if shutil.which("uv"):
                command = [shutil.which("uv"), "tool", "install", "--python", python, "--no-python-downloads", "aider-chat"]
                owner = "uv"
            elif shutil.which("pipx"):
                command = [shutil.which("pipx"), "install", "--python", python, "aider-chat"]
                owner = "pipx"
        script_url = None
        if command is None and platform_name() in {"macos", "linux"} and shutil.which("bash") and shutil.which("curl"):
            if key == "opencode":
                script_url = "https://opencode.ai/install"
                command = [shutil.which("bash"), "<official-installer>", "--no-modify-path"]
            elif key == "claude":
                script_url = "https://claude.ai/install.sh"
                command = [shutil.which("bash"), "<official-installer>"]
            elif key == "ollama" and platform_name() == "linux":
                script_url = "https://ollama.com/install.sh"
                command = [shutil.which("bash"), "<official-installer>"]
            if script_url:
                owner = "native"
        return {"component": key, "action": "install" if command else "manual", "command": command,
                "owner": owner, "url": tech.url, "script_url": script_url, "detection": detection.to_dict()}

    def ensure(self, key: str, *, yes: bool = False, offline: bool = False) -> dict:
        plan = self.plan(key)
        if plan["action"] == "reuse service":
            data = self.store.read()
            data["components"][key] = {"path": None, "owner": "unknown", "endpoint": plan["endpoint"], "installed_by_loc": False}
            self.store.save(data)
            return plan
        if plan["action"] == "reuse":
            item = self.discovery.detect(key).require()
            self._record(key, item.path, item.owner, False)
            return {"component": key, "action": "reused", "path": item.path}
        if plan["action"] == "pending":
            raise LocError(plan.get("reason", f"{key}: detection is uncertain. Run loc scan and register its existing location."))
        if offline:
            raise LocError(f"{key} is unavailable locally. Offline mode cannot install it.")
        if self.discovery.detect(key, refresh=True).status != "absent":
            raise LocError(f"{key} appeared during setup; retry to reuse it.")
        if plan["command"]:
            confirm(f"Install missing {key} using {plan['owner']}?", yes)
            if self.discovery.detect(key, refresh=True).status != "absent":
                raise LocError("Installation state changed; retry detection.")
            with tempfile.TemporaryDirectory(prefix="loc-installer-") as temp:
                command = plan["command"]
                if plan.get("script_url"):
                    raw, _ = fetch(plan["script_url"], maximum=2 * 1024 * 1024)
                    script = Path(temp) / "install.sh"
                    script.write_bytes(raw)
                    command = [str(script) if arg == "<official-installer>" else arg for arg in command]
                if self.discovery.detect(key, refresh=True).status != "absent":
                    raise LocError("Installation appeared before the installer ran; retry to reuse it.")
                r = subprocess.run(command, stdout=sys.stderr, env=dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", UV_PYTHON_DOWNLOADS="never"))
            if r.returncode:
                raise LocError(f"{key} installation did not complete. Retry setup to inspect partial installation; no alternate installer will run.")
        else:
            if not sys.stdin.isatty():
                raise LocError(f"Manual installation required for {key}: {plan['url']}. Run setup interactively, then confirm completion.")
            confirm(f"Open the official installation page for missing {key}?", yes)
            print(plan["url"])
            webbrowser.open(plan["url"])
            if input("Complete installation, then type 'installed' to recheck (anything else cancels): ").strip().lower() != "installed":
                raise LocError("Manual setup remains pending.")
        detection = self.discovery.detect(key, refresh=True)
        item = detection.require()
        self._record(key, item.path, plan["owner"] if plan["command"] else item.owner, bool(plan["command"]))
        return {"component": key, "action": "installed", "path": item.path}

    def _record(self, key: str, path: str, owner: str, installed: bool):
        data = self.store.read()
        old = data["components"].get(key, {})
        same = old.get("path") == path
        data["components"][key] = {"path": path, "owner": owner,
            "installed_by_loc": installed or (same and old.get("installed_by_loc", False)),
            "registered": same and old.get("registered", False)}
        self.store.save(data)

    def removal_plan(self, key: str) -> dict:
        result = self.discovery.detect(key)
        if result.status == "absent":
            return {"component": key, "action": "already absent"}
        item = result.require()
        tech = TECHNOLOGIES[key]
        command = None
        if item.owner in {"brew", "brew-cask"} and tech.brew and shutil.which("brew"):
            command = [shutil.which("brew"), "uninstall", *(["--cask"] if item.owner == "brew-cask" else []), tech.brew]
        elif item.owner in {"pipx", "uv"} and key == "aider" and shutil.which(item.owner):
            command = [shutil.which(item.owner), *(["tool"] if item.owner == "uv" else []), "uninstall", "aider-chat"]
        elif item.owner == "winget" and tech.winget and shutil.which("winget"):
            command = [shutil.which("winget"), "uninstall", "--exact", "--id", tech.winget, "--disable-interactivity"]
        elif item.owner == "npm" and tech.npm and shutil.which("npm"):
            # Confirm the executable belongs to this npm prefix before using its uninstaller.
            root = capture([shutil.which("npm"), "root", "-g"]).stdout.strip()
            if root and Path(item.path).resolve().is_relative_to(Path(root).resolve()):
                command = [shutil.which("npm"), "uninstall", "-g", tech.npm]
        elif item.owner == "native" and key == "opencode":
            command = [item.path, "uninstall", "--keep-config", "--keep-data", "--force"]
        return {"component": key, "action": "uninstall" if command else "manual", "command": command,
                "path": item.path, "owner": item.owner, "url": tech.url,
                "installed_by_loc": self.store.read()["components"].get(key, {}).get("installed_by_loc", False),
                "external_usage": "unknown", "preserve": "Model weights, user configuration, projects, and unrelated tools; never use purge/zap flags."}

    def remove(self, key: str, *, yes: bool = False) -> dict:
        plan = self.removal_plan(key)
        if plan["action"] == "already absent":
            return plan
        if running_component(plan["path"]):
            raise LocError("This component has a running process outside or inside loc. Stop it before uninstalling; loc will not terminate it implicitly.")
        confirm(f"Uninstall {key} at {plan['path']} via {plan['owner']}? Other applications may use it.", yes)
        current = self.removal_plan(key)
        if current != plan:
            raise LocError("Installation state changed; inspect a new uninstall preview.")
        if plan["command"]:
            result = subprocess.run(plan["command"], stdout=sys.stderr, env=dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_INSTALL_CLEANUP="1"))
            if result.returncode:
                raise LocError("Uninstall did not complete; records are preserved for inspection.")
        else:
            if not sys.stdin.isatty():
                raise LocError(f"No verified automated removal route. Follow {plan['url']} and rerun interactively.")
            print(f"Use the official uninstall instructions, preserving model weights and user data: {plan['url']}")
            webbrowser.open(plan["url"])
            if input("Type 'uninstalled' after completing removal: ").strip().lower() != "uninstalled":
                raise LocError("Uninstallation remains pending.")
        # Retained user data can make discovery uncertain. Verify the actual selected executable disappeared.
        if Path(plan["path"]).exists():
            raise LocError("The selected executable still exists; removal is not confirmed.")
        detected = self.discovery.detect(key, refresh=True)
        if any(i.path == plan["path"] or i.evidence.startswith("Homebrew package") for i in detected.installations):
            raise LocError("Installation records remain; inspect loc scan before retrying.")
        data = self.store.read()
        data["components"].pop(key, None)
        self.store.save(data)
        return {"component": key, "action": "uninstalled", "preserved_user_data": True}

    def update_plan(self, key: str) -> dict:
        item = self.discovery.detect(key).require()
        tech = TECHNOLOGIES[key]
        command = None
        if item.owner in {"brew", "brew-cask"} and tech.brew and shutil.which("brew"):
            command = [shutil.which("brew"), "upgrade", *(["--cask"] if item.owner == "brew-cask" else []), tech.brew]
        elif item.owner == "native" and key in {"claude", "opencode"}:
            command = [item.path, "update" if key == "claude" else "upgrade"]
        elif item.owner in {"uv", "pipx"} and key == "aider" and shutil.which(item.owner):
            command = [shutil.which(item.owner), *(["tool"] if item.owner == "uv" else []), "upgrade", "aider-chat"]
        elif item.owner == "winget" and tech.winget and shutil.which("winget"):
            command = [shutil.which("winget"), "upgrade", "--exact", "--id", tech.winget, "--disable-interactivity"]
        return {"component": key, "path": item.path, "owner": item.owner, "command": command,
                "update_available": None, "url": tech.url,
                "note": "The original installer determines availability. --check/--dry-run never invokes a mutating updater."}

    def update(self, key: str, *, yes: bool = False) -> dict:
        plan = self.update_plan(key)
        if not plan["command"]:
            raise LocError(f"No verified update route for this installation. Use its original installer: {plan['url']}")
        if running_component(plan["path"]):
            raise LocError("Finish this component's active processes before updating its executable.")
        confirm(f"Check and apply {key} updates through its existing {plan['owner']} installation?", yes)
        if self.update_plan(key) != plan:
            raise LocError("Installation state changed; preview the update again.")
        if subprocess.run(plan["command"], stdout=sys.stderr, env=dict(os.environ, UV_PYTHON_DOWNLOADS="never", HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_INSTALL_CLEANUP="1")).returncode:
            raise LocError("The original updater failed. No alternate installation channel was used.")
        detected = self.discovery.detect(key, refresh=True)
        detected.require()
        return {**plan, "status": "update command completed", "detection": detected.to_dict()}


def running_component(executable: str) -> bool:
    target = Path(executable).resolve()
    if os.name == "nt":
        # Query executable paths only, never command arguments that might contain credentials.
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            raise LocError("Process inspection is unavailable; component removal/update remains pending.")
        result = capture([powershell, "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Select-Object -ExpandProperty ExecutablePath | ConvertTo-Json -Compress"])
        if result.returncode:
            raise LocError("Could not inspect active processes; removal/update remains pending.")
        try:
            values = json.loads(result.stdout)
            values = [values] if isinstance(values, str) else values or []
            return any(value and Path(value).resolve() == target for value in values)
        except (ValueError, TypeError):
            raise LocError("Invalid process inspection response; removal/update remains pending.")
    result = capture(["ps", "-axo", "comm="])
    if result.returncode:
        raise LocError("Could not inspect active processes; removal/update remains pending.")
    return any(line.strip() and Path(line.strip()).resolve() == target for line in result.stdout.splitlines())


def existing_aider_python() -> str | None:
    candidates = [sys.executable]
    for version in ["3.12", "3.11", "3.10"]:
        if path := shutil.which("python" + version):
            candidates.append(path)
        for prefix in [Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/usr/bin")]:
            path = prefix / ("python" + version)
            if path.is_file():
                candidates.append(str(path))
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        candidates += [str(path) for path in (local / "Programs/Python").glob("Python3*/python.exe")]
    for path in dict.fromkeys(candidates):
        try:
            result = capture([path, "--version"])
            match = re.search(r"Python (\d+)\.(\d+)", result.stdout or result.stderr)
            if result.returncode == 0 and match and (3, 10) <= tuple(map(int, match.groups())) < (3, 13):
                return path
        except LocError:
            continue
    return None


def start_runtime(store: Store, base: str, timeout: float = 30) -> dict:
    runtime = Ollama(base)
    try:
        return {"action": "already running", "version": runtime.version(), "endpoint": base}
    except LocError:
        pass
    installation = Discovery(store).detect("ollama").require()
    store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    log = store.root / "runtime.log"
    env = dict(os.environ, OLLAMA_HOST=base, OLLAMA_NO_CLOUD="1", OLLAMA_NUM_PARALLEL="1", OLLAMA_MAX_LOADED_MODELS="1")
    with log.open("ab") as output:
        proc = subprocess.Popen([installation.path, "serve"], env=env, stdout=output, stderr=output,
                                start_new_session=os.name != "nt", creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise LocError("Ollama could not start. Inspect loc's runtime.log; the installation was preserved.")
        try:
            version = runtime.version()
            data = store.read()
            data["runtime_process"] = {"pid": proc.pid, "endpoint": base, "path": installation.path}
            store.save(data)
            return {"action": "started", "version": version, "endpoint": base}
        except LocError:
            time.sleep(0.2)
    proc.terminate()
    raise LocError("Ollama startup timed out; the process started by loc was stopped.")
