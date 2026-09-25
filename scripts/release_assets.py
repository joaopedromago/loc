"""Prepare the small release bundle; never include model weights or local state."""

import argparse
import hashlib
import shutil
import tomllib
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dist", type=Path, default=Path("dist"), help="Directory containing the built wheel and source archive.")
destination = parser.parse_args().dist
destination.mkdir(exist_ok=True)
version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
expected = {f"loc_coding-{version}-py3-none-any.whl", f"loc_coding-{version}.tar.gz",
            "install.py", "install.sh", "install.ps1", "SHA256SUMS"}
unexpected = {path.name for path in destination.iterdir()} - expected
if unexpected:
    raise SystemExit(f"Unexpected release files: {sorted(unexpected)}. Use a clean output directory.")
for name in [f"loc_coding-{version}-py3-none-any.whl", f"loc_coding-{version}.tar.gz"]:
    if not (destination / name).is_file():
        raise SystemExit(f"Missing build artifact: {name}")
for name in ["install.py", "install.sh", "install.ps1"]:
    shutil.copyfile(Path("scripts") / name, destination / name)
assets = sorted(path for path in destination.iterdir() if path.is_file() and path.name != "SHA256SUMS")
(destination / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in assets))
