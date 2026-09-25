"""Exercise the release installer without touching the user's loc installation.

--dist tests a built bundle with local download fixtures. --published uses real
GitHub downloads. Both run the distributed installer and real pip/loc commands.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True, help="Release bundle containing install.py and SHA256SUMS.")
    parser.add_argument("--published", action="store_true", help="Fetch the latest stable release from GitHub instead of fixture downloads.")
    args = parser.parse_args()
    bundle = args.dist.resolve()
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    wheel_name = f"loc_coding-{version}-py3-none-any.whl"
    checksums = (bundle / "SHA256SUMS").read_text()
    for line in checksums.splitlines():
        digest, filename = line.split()
        assert Path(filename).name == filename, filename
        assert hashlib.sha256((bundle / filename).read_bytes()).hexdigest() == digest, filename

    spec = importlib.util.spec_from_file_location("release_installer", bundle / "install.py")
    installer = importlib.util.module_from_spec(spec)
    with patch.object(sys, "dont_write_bytecode", True):
        spec.loader.exec_module(installer)
    base = f"https://github.com/{installer.REPOSITORY}/releases/download/v{version}/"
    api = f"https://api.github.com/repos/{installer.REPOSITORY}/releases/latest"
    manifest = {"tag_name": f"v{version}", "draft": False, "prerelease": False,
                "assets": [{"name": name, "browser_download_url": base + name}
                           for name in (wheel_name, "SHA256SUMS")]}
    downloads = {api: json.dumps(manifest).encode(), base + wheel_name: (bundle / wheel_name).read_bytes(),
                 base + "SHA256SUMS": checksums.encode()}

    def fetch_fixture(url, maximum=16 * 1024 * 1024):
        data = downloads[url]
        assert len(data) <= maximum
        return data

    with tempfile.TemporaryDirectory(prefix="loc-release-smoke-") as temp:
        sandbox = Path(temp).resolve()
        user = sandbox / "user"
        user.mkdir()
        empty_bin = sandbox / "empty-bin"
        empty_bin.mkdir()
        prefix = sandbox / "venv"
        state = sandbox / "state"
        # Patch only this process's home lookup, never HOME or the user's shell.
        # Children use explicit state/cache paths and run outside the checkout.
        env = {"PATH": str(empty_bin), "LOC_HOME": str(state),
               "LOCALAPPDATA": str(user / "AppData/Local"),
               "PIP_CACHE_DIR": str(sandbox / "pip-cache"), "PIP_CONFIG_FILE": os.devnull,
               "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
               "PYTHONPATH": "", "PYTHONNOUSERSITE": "1"}
        with patch.dict(os.environ, env), patch.object(Path, "home", return_value=user):
            fetch_context = contextlib.nullcontext() if args.published else patch.object(installer, "fetch", side_effect=fetch_fixture)
            with fetch_context:
                assert installer.main(["--prefix", str(prefix), "--yes"]) == 0
            executable = prefix / ("Scripts/loc.exe" if os.name == "nt" else "bin/loc")

            def run(*arguments):
                result = subprocess.run([str(executable), *arguments], cwd=sandbox, text=True, capture_output=True)
                assert result.returncode == 0, result.stdout + result.stderr
                return result.stdout

            assert run("--version").strip() == f"loc {version}"
            assert "usage:" in run("--help").lower()
            assert "usage:" in run("run", "-h").lower()
            owner = json.loads(run("self", "info", "--json"))
            assert owner["owner"] == "loc-bootstrap", owner
            assert Path(owner["prefix"]).resolve() == prefix, owner
            run("profiles", "--json")
            python = prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run([str(python), "-c",
                            "from dataclasses import asdict\n"
                            "from loc_cli.core import Store, Profile\n"
                            "s = Store()\n"
                            "with s.lock():\n"
                            "    data = s.read()\n"
                            "    data['profiles']['release-check'] = asdict(Profile(name='release-check', agent='claude', model='qwen3:4b'))\n"
                            "    s.save(data)\n"], cwd=sandbox, check=True)
            assert "release-check" in run("profiles", "--json")
            before = {p.relative_to(state): p.read_bytes() for p in state.rglob("*") if p.is_file()}
            package_before = executable.stat().st_mtime_ns
            output = io.StringIO()
            with patch.object(installer, "fetch", side_effect=AssertionError("Repeated installation must not download")), contextlib.redirect_stdout(output):
                assert installer.main(["--prefix", str(prefix), "--yes"]) == 0
            assert "already installed" in output.getvalue()
            assert executable.stat().st_mtime_ns == package_before
            result = json.loads(run("self", "uninstall", "--yes", "--json"))
            assert result["status"] == "uninstalled", result
            assert not executable.exists(), executable
            after = {p.relative_to(state): p.read_bytes() for p in state.rglob("*") if p.is_file()}
            assert before == after, "Self-uninstall changed saved user data"
    print(f"Release {version}: checksums, installation, help, ownership, duplicate prevention, and uninstall/data preservation passed.")


if __name__ == "__main__":
    main()
