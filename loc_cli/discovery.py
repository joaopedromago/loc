"""Bounded installation discovery. Failed detection is never absence."""

from __future__ import annotations

import os
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .core import LocError, Store, capture, platform_name


@dataclass(frozen=True)
class Technology:
    executable: str
    kind: str
    url: str
    brew: str | None = None
    cask: bool = False
    winget: str | None = None
    npm: str | None = None


TECHNOLOGIES = {
    "ollama": Technology("ollama", "runtime", "https://ollama.com/download", "ollama", True, "Ollama.Ollama"),
    "claude": Technology("claude", "agent", "https://code.claude.com/docs/en/setup", "claude-code", True, "Anthropic.ClaudeCode", "@anthropic-ai/claude-code"),
    "opencode": Technology("opencode", "agent", "https://opencode.ai/docs/", "opencode", False, "AnomalyCo.OpenCode", "opencode-ai"),
    "aider": Technology("aider", "agent", "https://aider.chat/docs/install.html"),
    "rtk": Technology("rtk", "helper", "https://github.com/rtk-ai/rtk", "rtk"),
    "llmfit": Technology("llmfit", "helper", "https://github.com/AlexsJones/llmfit", "llmfit"),
    "git": Technology("git", "dependency", "https://git-scm.com/downloads", "git", False, "Git.Git"),
    "python": Technology("python3", "dependency", "https://www.python.org/downloads/"),
    "uv": Technology("uv", "dependency", "https://docs.astral.sh/uv/getting-started/installation/", "uv", False, "astral-sh.uv"),
    "pipx": Technology("pipx", "dependency", "https://pipx.pypa.io/stable/installation/", "pipx"),
    "node": Technology("node", "dependency", "https://nodejs.org/en/download", "node", False, "OpenJS.NodeJS.LTS"),
    "loc": Technology("loc", "manager", "https://github.com/joaopedromago/loc"),
}


@dataclass
class Installation:
    path: str | None
    owner: str
    evidence: str
    executable: bool = True


@dataclass
class Detection:
    component: str
    status: str
    installations: list[Installation] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    selected: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def require(self) -> Installation:
        usable = [x for x in self.installations if x.executable]
        if self.selected:
            usable = [x for x in usable if x.path == self.selected]
        if len(usable) != 1 or self.status in {"unknown", "absent"} or self.status == "multiple" and not self.selected:
            raise LocError(f"{self.component}: {self.status}. Inspect 'loc scan'; register its existing executable with 'loc register {self.component} PATH'.")
        return usable[0]


class Discovery:
    def __init__(self, store: Store | None = None, *, system: str | None = None, home: Path | None = None):
        self.store = store or Store()
        self.system = system or platform_name()
        self.home = home or Path.home()
        self.records = self.store.read().get("components", {})
        self.cache: dict[str, Detection] = {}
        self.brew_records: tuple[set, set] | None = None
        self.brew_error = False
        self.tool_records = None
        self.npm_root = None

    def _tools(self) -> tuple[dict, list[str]]:
        if self.tool_records is not None:
            return self.tool_records
        records, issues = {}, []
        for manager in ("pipx", "uv"):
            binary = shutil.which(manager)
            if not binary:
                continue
            try:
                result = capture([binary, "list", "--json"] if manager == "pipx" else [binary, "tool", "list"])
                if result.returncode:
                    issues.append(f"{manager} tool records could not be inspected.")
                    continue
                if manager == "pipx":
                    data = json.loads(result.stdout)
                    for package, record in data.get("venvs", {}).items():
                        main = record.get("metadata", {}).get("main_package", {})
                        records[package] = manager
                        for app in main.get("apps", []):
                            records[app] = manager
                else:
                    for line in result.stdout.splitlines():
                        if line and not line.startswith((" ", "-")):
                            records[line.split()[0]] = manager
            except (LocError, ValueError, KeyError, TypeError):
                issues.append(f"{manager} tool records could not be inspected.")
        self.tool_records = (records, issues)
        return self.tool_records

    def _brew(self) -> tuple[set, set]:
        if self.brew_records is None:
            self.brew_records = (set(), set())
            brew = shutil.which("brew")
            if brew:
                for index, flag in enumerate(("--formula", "--cask")):
                    try:
                        r = capture([brew, "list", flag, "-1"], env=dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1"))
                        if r.returncode:
                            self.brew_error = True
                        else:
                            self.brew_records[index].update(r.stdout.split())
                    except LocError:
                        self.brew_error = True
        return self.brew_records

    def paths(self, key: str) -> list[Path]:
        executable = TECHNOLOGIES[key].executable
        names = [executable]
        if key == "python":
            names += ["python", "py"]
        if self.system == "windows":
            names = [x + suffix for x in names for suffix in (".exe", ".cmd", ".bat", "")]
        directories = [Path(x) for x in os.environ.get("PATH", "").split(os.pathsep) if x]
        directories += [self.home / ".local/bin", self.home / ".cargo/bin", self.home / ".opencode/bin",
                        Path("/usr/local/bin"), Path("/usr/bin"), Path("/opt/homebrew/bin"), self.home / "bin"]
        patterns = [".nvm/versions/node/*/bin", ".local/share/pipx/venvs/*/bin", ".local/pipx/venvs/*/bin",
                    ".local/share/uv/tools/*/bin", ".local/share/loc/venv/bin", "Library/Application Support/pipx/venvs/*/bin"]
        for pattern in patterns:
            directories += list(self.home.glob(pattern))
        if self.system == "macos":
            directories += [Path("/Applications/Ollama.app/Contents/Resources"),
                            self.home / "Applications/Ollama.app/Contents/Resources"]
        if self.system == "windows":
            local = Path(os.environ.get("LOCALAPPDATA", self.home / "AppData/Local"))
            appdata = Path(os.environ.get("APPDATA", self.home / "AppData/Roaming"))
            directories += [local / "Programs/Ollama", local / "Microsoft/WinGet/Links", appdata / "npm",
                            self.home / "scoop/shims", self.home / ".local/bin"]
            directories += list((local / "Programs/Python").glob("Python*")) if (local / "Programs/Python").exists() else []
            directories += list((local / "pipx/venvs").glob("*/Scripts")) if (local / "pipx/venvs").exists() else []
        result = [directory / item for directory in directories for item in names]
        if self.records.get(key, {}).get("path"):
            result.insert(0, Path(self.records[key]["path"]))
        return result

    def _owner(self, path: Path, key: str) -> str:
        text = str(path.resolve(strict=False)).replace("\\", "/")
        tech = TECHNOLOGIES[key]
        if "/Cellar/" in text or "/Caskroom/" in text:
            return "brew-cask" if tech.cask else "brew"
        if "/pipx/venvs/" in text or "/pipx/shared/" in text:
            return "pipx"
        if "/uv/tools/" in text:
            return "uv"
        if "/node_modules/" in text and tech.npm:
            return "npm"
        if key == "claude" and "/.local/share/claude/" in text:
            return "native"
        if key == "opencode" and "/.opencode/bin/" in text:
            return "native"
        if key == "ollama" and "/Ollama.app/" in text:
            return "manual"
        previous = self.records.get(key, {})
        if previous.get("path") and Path(previous["path"]).resolve(strict=False) == path.resolve(strict=False):
            return previous.get("owner", "unknown")
        return "unknown"

    def _windows_records(self, key: str, installs: list, issues: list) -> None:
        try:
            import winreg
        except ImportError:
            issues.append("Windows installation registry is unavailable.")
            return
        aliases = {"claude": ["claude code"], "aider": ["aider"], "node": ["node.js"], "python": ["python"], "loc": ["loc-coding"]}.get(key, [key])
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", 0, winreg.KEY_READ | view) as root:
                        for i in range(winreg.QueryInfoKey(root)[0]):
                            with winreg.OpenKey(root, winreg.EnumKey(root, i)) as item:
                                try:
                                    display = winreg.QueryValueEx(item, "DisplayName")[0].lower()
                                    if any(display == a or display.startswith(a + " ") for a in aliases):
                                        if not installs:
                                            installs.append(Installation(None, "manual", "Windows uninstall registry", False))
                                except FileNotFoundError:
                                    continue
                except FileNotFoundError:
                    continue
                except OSError:
                    issues.append("An applicable Windows installation registry could not be inspected.")

    def detect(self, key: str, refresh: bool = False) -> Detection:
        if key not in TECHNOLOGIES:
            raise LocError(f"Unsupported component: {key}")
        if key in self.cache and not refresh:
            return self.cache[key]
        if refresh:
            self.brew_records = None
            self.brew_error = False
            self.tool_records = None
        installations, issues, seen = [], [], set()
        try:
            candidates = self.paths(key)
        except OSError:
            candidates = []
            issues.append("An installation directory could not be inspected.")
        for path in candidates:
            try:
                path.lstat()
                identity = str(path.resolve(strict=False))
                if identity in seen:
                    continue
                seen.add(identity)
                installations.append(Installation(str(path.absolute()), self._owner(path, key), "executable location",
                                                  path.is_file() and (self.system == "windows" or os.access(path, os.X_OK))))
            except FileNotFoundError:
                continue
            except OSError:
                issues.append("An executable location could not be inspected.")
        if self.system in {"macos", "linux"}:
            formulae, casks = self._brew()
            tech = TECHNOLOGIES[key]
            if tech.brew and tech.brew in formulae | casks:
                owner = "brew-cask" if tech.brew in casks else "brew"
                found = False
                for item in installations:
                    if item.owner in {"brew", "brew-cask"} or (key == "ollama" and "/Applications/" in (item.path or "")):
                        item.owner = owner
                        found = True
                if not found:
                    installations.append(Installation(None, owner, "Homebrew package record; executable unresolved", False))
            if self.brew_error:
                issues.append("Homebrew installation records could not be fully inspected.")
        if self.system == "linux":
            package = {"claude": "claude-code", "aider": "aider-chat", "python": "python3", "node": "nodejs"}.get(key, key)
            for manager, args in [("dpkg-query", ["-W", "-f=${db:Status-Status}", package]), ("rpm", ["-q", package])]:
                binary = shutil.which(manager)
                if not binary:
                    continue
                try:
                    r = capture([binary, *args])
                    if r.returncode == 0 and (manager != "dpkg-query" or r.stdout.strip() == "installed"):
                        if not installations:
                            installations.append(Installation(None, manager, "system package record", False))
                        for item in installations:
                            if item.path and item.path.startswith("/usr/bin/"):
                                item.owner = manager
                    elif r.returncode not in {0, 1}:
                        issues.append(f"{manager} records could not be inspected.")
                except LocError:
                    issues.append(f"{manager} records could not be inspected.")
        if self.system == "windows":
            self._windows_records(key, installations, issues)
        records, tool_issues = self._tools()
        issues.extend(tool_issues)
        package = {"aider": "aider-chat", "loc": "loc-coding"}.get(key, key)
        if key in records or package in records:
            manager = records.get(key, records.get(package))
            if not any(item.owner == manager for item in installations):
                installations.append(Installation(None, manager, "managed tool package record; executable unresolved", False))
        npm_package = TECHNOLOGIES[key].npm
        if npm_package and shutil.which("npm"):
            try:
                if self.npm_root is None:
                    result = capture([shutil.which("npm"), "root", "-g"])
                    if result.returncode or not result.stdout.strip():
                        raise LocError("npm inspection failed")
                    self.npm_root = Path(result.stdout.strip())
                package_path = self.npm_root / npm_package
                if package_path.exists() and not any(item.owner == "npm" for item in installations):
                    installations.append(Installation(None, "npm", "npm package directory; executable unresolved", False))
            except LocError:
                issues.append("npm installation records could not be inspected.")
        markers = {"ollama": [self.home / ".ollama", Path("/Applications/Ollama.app")],
                   "claude": [self.home / ".local/share/claude/versions"],
                   "opencode": [self.home / ".opencode/bin"],
                   "aider": [self.home / ".local/share/pipx/venvs/aider-chat"],
                   "loc": [self.home / ".local/share/loc/venv"]}
        if not installations:
            for marker in markers.get(key, []):
                if marker.exists():
                    issues.append("Existing application files were found, but its executable is unresolved.")
            if self.records.get(key, {}).get("endpoint"):
                issues.append("An existing runtime service is recorded; locate its installation instead of reinstalling.")
        # An explicit registration resolves the chosen executable, not unknown package ownership.
        selected = self.records.get(key, {}).get("path") if self.records.get(key, {}).get("registered") else None
        status = "present" if installations else "unknown" if issues else "absent"
        if len(installations) > 1 and not selected:
            status = "multiple"
        if installations and not any(i.executable for i in installations):
            status = "unusable"
        result = Detection(key, status, installations, list(dict.fromkeys(issues)), selected)
        self.cache[key] = result
        return result

    def register(self, key: str, path: Path) -> dict:
        if key not in TECHNOLOGIES or not path.is_file() or not os.access(path, os.X_OK):
            raise LocError("Register a supported component's existing executable file.")
        data = self.store.read()
        prior = data["components"].get(key, {})
        data["components"][key] = {**prior, "path": str(path.absolute()), "owner": self._owner(path, key),
                                  "registered": True, "installed_by_loc": prior.get("installed_by_loc", False)}
        self.store.save(data)
        return data["components"][key]
