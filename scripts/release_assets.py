"""Prepare the small release bundle; never include model weights or local state."""

import hashlib
import shutil
from pathlib import Path

destination = Path("dist")
destination.mkdir(exist_ok=True)
for name in ["install.py", "install.sh", "install.ps1"]:
    shutil.copyfile(Path("scripts") / name, destination / name)
assets = sorted(path for path in destination.iterdir() if path.is_file() and path.name != "SHA256SUMS")
(destination / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in assets))
