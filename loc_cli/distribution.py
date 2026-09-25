"""Verified GitHub release assets and updates through the existing tool owner."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__
from .core import LocError, Store, confirm, read_json
from .network import REPOSITORY, fetch


def installation_owner() -> dict:
    prefix = Path(sys.prefix)
    text = prefix.as_posix()
    owner = "unknown"
    if "/pipx/venvs/" in text:
        owner = "pipx"
    elif "/uv/tools/" in text:
        owner = "uv"
    elif (prefix / ".loc-install.json").exists():
        receipt = read_json(prefix / ".loc-install.json", {})
        if receipt.get("schema") == 1 and receipt.get("owner") == "loc-bootstrap":
            owner = "loc-bootstrap"
    try:
        dist = importlib.metadata.distribution("loc-coding")
        direct = json.loads(dist.read_text("direct_url.json") or "{}")
        if direct.get("dir_info", {}).get("editable"):
            owner = "development"
    except importlib.metadata.PackageNotFoundError:
        owner = "development"
    return {"owner": owner, "prefix": str(prefix), "python": sys.executable, "version": __version__}


def latest_release() -> dict:
    raw, _ = fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
    try:
        data = json.loads(raw)
        version = data["tag_name"].removeprefix("v")
        if not re.fullmatch(r"\d+\.\d+\.\d+", version) or data.get("prerelease") or data.get("draft"):
            raise ValueError()
        wheel_name = f"loc_coding-{version}-py3-none-any.whl"
        assets = {a["name"]: a["browser_download_url"] for a in data["assets"]}
        prefix = f"https://github.com/{REPOSITORY}/releases/download/"
        if not assets[wheel_name].startswith(prefix) or not assets["SHA256SUMS"].startswith(prefix):
            raise ValueError()
        return {"version": version, "wheel_name": wheel_name, "wheel_url": assets[wheel_name],
                "checksums_url": assets["SHA256SUMS"], "update_available": tuple(map(int, version.split("."))) > tuple(map(int, __version__.split(".")))}
    except (ValueError, KeyError, TypeError) as exc:
        raise LocError("The latest release has no compatible stable wheel/checksum pair. Use the source checkout until a release is published.") from exc


def download_release(release: dict, directory: Path) -> Path:
    raw, _ = fetch(release["checksums_url"], maximum=65536)
    expected = None
    for line in raw.decode().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == release["wheel_name"]:
            expected = parts[0]
    if not expected or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise LocError("Release checksum is missing or invalid.")
    wheel, _ = fetch(release["wheel_url"], maximum=16 * 1024 * 1024)
    if hashlib.sha256(wheel).hexdigest() != expected:
        raise LocError("Release checksum mismatch. Nothing was installed.")
    path = directory / release["wheel_name"]
    path.write_bytes(wheel)
    return path


def self_update(*, check: bool = False, dry_run: bool = False, yes: bool = False) -> dict:
    owner = installation_owner()
    release = latest_release()
    report = {**owner, "available_version": release["version"], "update_available": release["update_available"]}
    if check or dry_run or not release["update_available"]:
        return report
    if owner["owner"] not in {"uv", "pipx", "loc-bootstrap"}:
        raise LocError("This installation is not managed by a supported updater. Update its original source/channel; loc will not create a second installation.")
    confirm(f"Update loc {__version__} to {release['version']} through {owner['owner']}?", yes)
    with tempfile.TemporaryDirectory(prefix="loc-update-") as temp:
        wheel = download_release(release, Path(temp))
        if owner["owner"] == "uv":
            if not shutil.which("uv"):
                raise LocError("The original uv installation is unavailable; no alternate updater will run.")
            command = [shutil.which("uv"), "tool", "install", "--upgrade", "--python", sys.executable, "--no-python-downloads", str(wheel)]
        elif owner["owner"] == "pipx":
            if not shutil.which("pipx"):
                raise LocError("The original pipx installation is unavailable; no alternate updater will run.")
            command = [shutil.which("pipx"), "runpip", "loc-coding", "install", "--upgrade", "--no-deps", str(wheel)]
        else:
            command = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-deps", str(wheel)]
        result = subprocess.run(command, stdout=sys.stderr, env=dict(os.environ, UV_PYTHON_DOWNLOADS="never", PIP_DISABLE_PIP_VERSION_CHECK="1"))
        if result.returncode:
            raise LocError("The original updater failed. Profiles were preserved; no alternative installation was attempted.")
        result = subprocess.run([sys.executable, "-m", "loc_cli", "--version"], capture_output=True, text=True)
        if result.returncode or release["version"] not in result.stdout:
            raise LocError("Package update finished but its version could not be verified. Inspect loc self info.")
    return {**report, "status": "updated"}


def self_uninstall(*, dry_run: bool = False, yes: bool = False) -> dict:
    owner = installation_owner()
    command = None
    if owner["owner"] in {"uv", "pipx"} and shutil.which(owner["owner"]):
        command = [shutil.which(owner["owner"]), *(["tool"] if owner["owner"] == "uv" else []), "uninstall", "loc-coding"]
    elif owner["owner"] == "loc-bootstrap":
        # Removing only the package also works when the interpreter is running on Windows.
        command = [sys.executable, "-m", "pip", "uninstall", "--yes", "loc-coding"]
    result = {**owner, "command": command, "preserved": "All profiles, user data, installed agents/runtimes, model weights, and projects."}
    if dry_run:
        return result
    if not command:
        raise LocError("No verified self-uninstall route for this installation. Use its original owner; development checkouts are preserved.")
    confirm("Uninstall loc itself, preserving profiles and installed AI tools?", yes)
    if subprocess.run(command, stdout=sys.stderr).returncode:
        raise LocError("loc's package owner did not confirm successful uninstallation.")
    return {**result, "status": "uninstalled"}
