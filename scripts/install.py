#!/usr/bin/env python3
"""Install loc once using an existing Python and tool manager, or a shared-interpreter venv.

Run from a checkout with --source PATH, or use a published GitHub release.
This file is standalone so release installers do not require loc beforehand.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv
from pathlib import Path

REPOSITORY = "joaopedromago/loc"


def fetch(url, maximum=16 * 1024 * 1024):
    request = urllib.request.Request(url, headers={"User-Agent": "loc-bootstrap"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if not response.url.startswith("https://"):
            raise RuntimeError("Refusing an insecure download redirect.")
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise RuntimeError("Download exceeded its size limit.")
    return data


def find_existing(prefix):
    paths = [Path(p) / executable for p in os.environ.get("PATH", "").split(os.pathsep) if p
             for executable in ("loc", "loc.exe", "loc.cmd")]
    paths += [Path.home() / ".local/bin/loc", Path.home() / ".local/bin/loc.exe",
              prefix / "bin/loc", prefix / "Scripts/loc.exe"]
    for base in [Path.home() / ".local/share/pipx/venvs", Path.home() / ".local/share/uv/tools", Path.home() / ".local/pipx/venvs"]:
        if base.exists():
            paths += list(base.glob("*/bin/loc")) + list(base.glob("*/Scripts/loc.exe"))
    for path in paths:
        if path.exists() or path.is_symlink():
            return str(path)
    for manager in ("uv", "pipx"):
        executable = shutil.which(manager)
        if executable:
            command = [executable, *(["tool"] if manager == "uv" else []), "list"]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"Cannot inspect {manager} installations; refusing to assume loc is absent.")
            if re.search(r"\bloc-coding\b|\bloc_coding\b", result.stdout):
                return f"{manager} package record (executable unresolved)"
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, help="Install this local source checkout instead of a published release.")
    p.add_argument("--prefix", type=Path, help="Location for a bootstrap-owned venv; skips uv/pipx selection.")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if sys.version_info < (3, 11):
        raise RuntimeError("loc needs Python 3.11+. Select an existing compatible interpreter; no additional Python is downloaded automatically.")
    default = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "loc/venv"
               if os.name == "nt" else Path.home() / ".local/share/loc/venv")
    prefix = (args.prefix or default).expanduser().absolute()
    existing = find_existing(prefix)
    if existing:
        print(f"loc is already installed: {existing}\nUse that installation's 'loc self update'. Nothing was installed.")
        return 0
    manager = "uv" if shutil.which("uv") else "pipx" if shutil.which("pipx") else "loc-bootstrap"
    if args.prefix:
        manager = "loc-bootstrap"
    print(f"Install loc using {manager} and existing Python {sys.executable}.")
    if args.dry_run:
        return 0
    if not args.yes and (not sys.stdin.isatty() or input("Continue? [y/N] ").strip().lower() not in {"y", "yes"}):
        raise RuntimeError("Cancelled. Use --yes for the selected installation in noninteractive mode.")
    # Coordinate repeated bootstrap processes without a stale-lock recovery guess.
    lock_root = default.parent
    lock_root.mkdir(parents=True, exist_ok=True)
    with (lock_root / "bootstrap.lock").open("a+b") as lock:
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if find_existing(prefix):
            print("Another installation became available. Reuse it; no duplicate was installed.")
            return 0
        with tempfile.TemporaryDirectory(prefix="loc-install-") as temp:
            if args.source:
                source = args.source.resolve()
                if not (source / "pyproject.toml").is_file() or not (source / "loc_cli").is_dir():
                    raise RuntimeError("--source must point to a loc source checkout.")
                artifact = str(source)
            else:
                release = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/latest"))
                version = release["tag_name"].removeprefix("v")
                if not re.fullmatch(r"\d+\.\d+\.\d+", version) or release.get("draft") or release.get("prerelease"):
                    raise RuntimeError("No stable release is available.")
                filename = f"loc_coding-{version}-py3-none-any.whl"
                assets = {a["name"]: a["browser_download_url"] for a in release["assets"]}
                expected_prefix = f"https://github.com/{REPOSITORY}/releases/download/"
                if any(not assets[name].startswith(expected_prefix) for name in [filename, "SHA256SUMS"]):
                    raise RuntimeError("Unexpected release asset source.")
                checksums = fetch(assets["SHA256SUMS"], 65536).decode()
                expected = next((line.split()[0] for line in checksums.splitlines() if len(line.split()) == 2 and line.split()[1].lstrip("*") == filename), None)
                wheel = fetch(assets[filename])
                if hashlib.sha256(wheel).hexdigest() != expected:
                    raise RuntimeError("Release checksum mismatch. Nothing was installed.")
                path = Path(temp) / filename
                path.write_bytes(wheel)
                artifact = str(path)
            env = dict(os.environ, UV_PYTHON_DOWNLOADS="never", PIP_DISABLE_PIP_VERSION_CHECK="1")
            if manager == "uv":
                command = [shutil.which("uv"), "tool", "install", "--python", sys.executable, "--no-python-downloads", artifact]
            elif manager == "pipx":
                command = [shutil.which("pipx"), "install", "--python", sys.executable, artifact]
            else:
                if prefix.exists() and not (prefix / ".loc-install.json").exists():
                    raise RuntimeError("The target directory already exists without a loc ownership record; it is preserved.")
                if not prefix.exists():
                    venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(prefix)
                    (prefix / ".loc-install.json").write_text(json.dumps({"schema": 1, "owner": "loc-bootstrap"}) + "\n")
                python = prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                command = [str(python), "-m", "pip", "install", "--no-deps", artifact]
            if subprocess.run(command, env=env).returncode:
                raise RuntimeError("Installation did not complete. Existing partial state is preserved for inspection; no alternate manager was tried.")
            if manager == "loc-bootstrap":
                executable = prefix / ("Scripts/loc.exe" if os.name == "nt" else "bin/loc")
                if subprocess.run([str(executable), "--version"]).returncode:
                    raise RuntimeError("Installed command could not be verified.")
                print(f"Installed: {executable}\nAdd {executable.parent} to PATH, or invoke that path directly.")
            else:
                found = find_existing(prefix)
                if not found:
                    raise RuntimeError("The manager finished, but loc could not be detected.")
                print(f"Installed: {found}\nOpen a new terminal if loc is not yet on PATH.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"loc installer: {exc}", file=sys.stderr)
        raise SystemExit(2)
