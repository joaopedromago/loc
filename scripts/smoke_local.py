#!/usr/bin/env python3
"""Opt-in live checks. Reuse installed models; never install or remove software."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loc_cli.agents import run_profile, run_agent
from loc_cli.core import Profile, Store, atomic_json
from loc_cli.diagnostics import doctor
from loc_cli.discovery import Discovery
from loc_cli.lifecycle import Lifecycle
from loc_cli.ollama import Ollama


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--agents", nargs="+", choices=["claude", "opencode", "aider"], default=["claude", "opencode", "aider"])
    parser.add_argument("--context", type=int, default=32768)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(".tmp/local-smoke"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    store = Store(args.output.absolute() / "state")
    runtime = Ollama()
    runtime.local_model(args.model)
    before = {m["name"]: m["digest"] for m in runtime.models()}
    shell = Path.home() / ".zshrc"
    shell_before = hashlib.sha256(shell.read_bytes()).hexdigest() if shell.exists() else None
    discovery = Discovery(store)
    for key in ["ollama", *args.agents]:
        discovery.detect(key).require()
    results = []
    original_run = run_agent

    def observed_run(command, env, cwd, timeout, **kwargs):
        result = original_run(command, env, cwd, timeout, **kwargs)
        if timeout is not None:
            name = Path(command[0]).name
            (args.output / f"{name}-stdout.txt").write_text(result.stdout or "", encoding="utf-8")
            (args.output / f"{name}-stderr.txt").write_text(result.stderr or "", encoding="utf-8")
        return result

    for agent in args.agents:
        profile = Profile(f"smoke-{agent}", agent, args.model, context=args.context).validate()
        with store.lock():
            Lifecycle(store).setup(profile, yes=True, offline=True)
        print(json.dumps({"agent": agent, "stage": "configured", "model": profile.resolved_model}), flush=True)
        with patch("loc_cli.agents.run_agent", side_effect=observed_run):
            result = run_profile(store, profile, [], verify=True, timeout=args.timeout, offline=args.offline)
        results.append(result)
        print(json.dumps(result), flush=True)
        atomic_json(args.output / "results.json", results)
    after = {m["name"]: m["digest"] for m in runtime.models()}
    preserved = all(after.get(name) == digest for name, digest in before.items())
    shell_after = hashlib.sha256(shell.read_bytes()).hexdigest() if shell.exists() else None
    evidence = {"results": results, "existing_models_preserved": preserved,
                "shell_configuration_preserved": shell_before == shell_after,
                "created_configuration_aliases": sorted(set(after) - set(before)),
                "note": "New aliases share existing weight blobs. Test state is retained for inspection; no original models are removed."}
    atomic_json(args.output / "evidence.json", evidence)
    print(json.dumps(evidence), flush=True)
    return 0 if preserved and shell_before == shell_after and all(r.get("status") == "passed" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
