"""Explicit offline execution with OS enforcement, failing closed elsewhere.

macOS runs a separate Ollama process reading the existing model store. Both the
runtime and agent are sandboxed; agent subprocesses can reach only the gateway.
No global runtime settings or firewall rules are changed.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from .core import LocError, Profile, Store, atomic_json, platform_name, read_json


def agent_policy(port: int) -> str:
    return f'''(version 1)
(allow default)
(deny network*)
(allow network-outbound (remote ip "localhost:{port}"))
'''


def runtime_policy(models: Path) -> str:
    return f'''(version 1)
(allow default)
(deny network*)
(allow network-bind (local ip "localhost:*"))
(allow network-inbound (local ip "localhost:*"))
(allow network-outbound (remote ip "localhost:*"))
(deny file-write* (subpath {json.dumps(str(models))}))
'''


def free_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def offline_run(store: Store, profile: Profile, args: list[str], *, dry_run: bool, verify: bool, timeout: int, json_output: bool = False) -> dict:
    if platform_name() != "macos" or not Path("/usr/bin/sandbox-exec").exists() or profile.agent == "opencode":
        raise LocError("Verified offline execution currently supports Claude Code and Aider on macOS. This combination is unsupported; loc will not silently launch it online.")
    models = Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama/models")).resolve()
    if not (models / "manifests").is_dir() or not (models / "blobs").is_dir():
        raise LocError("The local model storage directory is unknown. Set OLLAMA_MODELS to the existing store; no second download is allowed.")
    if dry_run:
        return {"action": "offline preview", "model_store": str(models), "agent": profile.agent,
                "network": "Agent and children can reach only the inference gateway. Private runtime has no external network access.",
                "memory": "A separate runtime process reads shared weights; existing sessions are preserved."}
    with tempfile.TemporaryDirectory(prefix="loc-offline-") as temp:
        directory = Path(temp)
        request = directory / "request.json"
        output = directory / "result.json"
        atomic_json(request, {"profile": asdict(profile), "store": str(store.root), "args": args, "verify": verify,
                              "timeout": timeout, "models": str(models), "result": str(output), "json_output": json_output})
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
        command = [sys.executable, "-m", "loc_cli.offline", str(request)]
        result = subprocess.run(command, env=env)
        if not output.exists():
            raise LocError("Offline worker could not establish the required sandbox. No online fallback was attempted.")
        record = read_json(output)
        if record.get("error"):
            raise LocError(record["error"])
        return record


def worker(path: Path) -> int:
    from .agents import run_profile
    from .discovery import Discovery
    from .ollama import Ollama
    request = read_json(path)
    store = Store(Path(request["store"]))
    profile = Profile.parse(request["profile"])
    result = {"status": "failed"}
    process = None
    try:
        executable = Discovery(store).detect("ollama").require().path
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        env = dict(os.environ, OLLAMA_HOST=base, OLLAMA_MODELS=request["models"], OLLAMA_NO_CLOUD="1",
                   OLLAMA_NUM_PARALLEL="1", OLLAMA_MAX_LOADED_MODELS="1", OLLAMA_KEEP_ALIVE="0")
        with (path.parent / "runtime.log").open("wb") as log:
            process = subprocess.Popen(["/usr/bin/sandbox-exec", "-p", runtime_policy(Path(request["models"])), executable, "serve"],
                                       env=env, stdout=log, stderr=log, start_new_session=True)
        deadline = time.monotonic() + 30
        client = Ollama(base, timeout=1)
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise LocError("The sandboxed runtime failed to start; offline launch was cancelled.")
            try:
                client.version()
                break
            except LocError:
                time.sleep(0.1)
        else:
            raise LocError("The sandboxed runtime did not become ready.")
        profile.endpoint = base
        result = run_profile(store, profile, request["args"], verify=request["verify"], timeout=request["timeout"], sandbox_agent=True, json_output=request.get("json_output", False))
        result["network"] = "offline enforced"
    except LocError as exc:
        result = {"error": str(exc)}
    finally:
        if process and process.poll() is None:
            import signal
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        atomic_json(Path(request["result"]), result)
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(worker(Path(sys.argv[1])))
