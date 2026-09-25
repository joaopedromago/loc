"""Session-scoped agent configuration; no edits to global agent or shell files."""

from __future__ import annotations

import contextlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from .core import LocError, Profile, Store, atomic_json, capture, read_json
from .discovery import Discovery
from .gateway import Gateway
from .ollama import Ollama


GUIDANCE = (
    "Work on the requested coding task. Preserve repository instructions and existing changes. "
    "Search for relevant symbols and read targeted file sections before expanding context. "
    "Avoid generated files, dependencies, and broad command output unless needed. "
    "Keep explanations concise, preserve failure details, and run relevant checks. "
    "When summarizing history, retain requirements, decisions, changed files, failures, and next steps."
)


def run_agent(command: list[str], env: dict, cwd: Path | None, timeout: int | None, *, json_output: bool = False) -> subprocess.CompletedProcess:
    """Keep interactive terminal behavior and stop only our verification process tree on timeout."""
    captured = timeout is not None
    process = subprocess.Popen(command, env=env, cwd=cwd, text=captured,
        stdout=subprocess.PIPE if captured else sys.stderr if json_output else None, stderr=subprocess.PIPE if captured else None,
        start_new_session=captured and os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if captured and os.name == "nt" else 0)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        if process.poll() is None:
            if captured and os.name != "nt":
                os.killpg(process.pid, signal.SIGTERM)
            elif captured and os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            else:
                process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                if captured and os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.communicate()
        raise


def clean_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "OPENAI_", "AIDER_", "OPENCODE_", "CLAUDE_CODE_"))
           and k not in {"CLAUDECODE", "OLLAMA_API_KEY", "OLLAMA_HOST", "OLLAMA_API_BASE", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"}}
    env.update({"NO_PROXY": "127.0.0.1,localhost,::1", "no_proxy": "127.0.0.1,localhost,::1",
                "DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1"})
    return env


def agent_version(path: str, agent: str) -> tuple[int, str]:
    r = capture([path, "--version"], env=clean_env())
    if r.returncode:
        raise LocError(f"{agent} exists but its version check failed. It will not be reinstalled.")
    match = re.search(r"(?:v)?(\d+)\.\d+\.\d+", r.stdout)
    if not match:
        raise LocError(f"Could not identify {agent}'s version; refusing to guess its configuration schema.")
    return int(match.group(1)), match.group(0)


def validate_args(agent: str, args: list[str]) -> None:
    blocked = {"--model", "-m", "--fallback-model", "--settings", "--setting-sources", "--config", "--env-file",
               "--model-settings-file", "--model-metadata-file", "--weak-model", "--editor-model", "--openai-api-base",
               "--anthropic-api-key", "--api-key", "--set-env", "--server", "--attach", "--cloud", "--environment"}
    for arg in args:
        if arg.split("=", 1)[0] in blocked or arg.startswith("-m") and not arg.startswith("--"):
            raise LocError(f"{arg.split('=', 1)[0]} would override the local profile. Change the profile instead.")


def configuration(profile: Profile, base: str, directory: Path, executable: str, major: int,
                  args: list[str] | None = None, verification: bool = False) -> tuple[list[str], dict]:
    args = args or []
    validate_args(profile.agent, args)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = clean_env()
    # The gateway maps this public name to the pinned runtime configuration alias.
    model = profile.model
    agent_name = {"claude": "Claude Code", "opencode": "OpenCode", "aider": "Aider"}[profile.agent]
    identity = f"Inference model: {model} (local Ollama). {agent_name} is the coding-agent application. Use this model identifier when asked which model is running. "
    instructions = directory / "instructions.md"
    instructions.write_text(identity + GUIDANCE + (" Prefer installed RTK for supported noisy shell commands; preserve original output when needed." if profile.rtk else "") + "\n")
    if profile.agent == "claude":
        if major != 2:
            raise LocError("This loc release supports Claude Code 2.x; inspect compatibility before using another major version.")
        forced = {"ANTHROPIC_BASE_URL": base, "ANTHROPIC_AUTH_TOKEN": "ollama", "ANTHROPIC_API_KEY": "",
                  "ANTHROPIC_MODEL": model, "ANTHROPIC_DEFAULT_HAIKU_MODEL": model, "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
                  "ANTHROPIC_DEFAULT_OPUS_MODEL": model, "ANTHROPIC_SMALL_FAST_MODEL": model,
                  "CLAUDE_CODE_SUBAGENT_MODEL": model, "CLAUDE_CODE_MAX_CONTEXT_TOKENS": str(profile.context),
                  "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(profile.output_tokens), "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                  "CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT": "1", "DISABLE_AUTOUPDATER": "1"}
        env.update(forced)
        settings = {"env": forced, "model": model}
        atomic_json(directory / "claude.json", settings)
        command = [executable, "--model", model, "--settings", str(directory / "claude.json"), "--append-system-prompt", instructions.read_text()]
        if verification:
            command += ["--setting-sources", "", "--strict-mcp-config", "--no-session-persistence", "--permission-mode", "acceptEdits",
                        "--allowedTools", "Read,Edit,Write", "--tools", "Read,Edit,Write", "--output-format", "json", "-p"]
    elif profile.agent == "opencode":
        if major not in {1, 2}:
            raise LocError("This loc release supports OpenCode 1.x and 2.x.")
        selected = "ollama/" + model
        if major == 2:
            config = {"model": selected, "update": "disable", "share": "disabled",
                "providers": {"ollama": {"settings": {"baseURL": base + "/v1"},
                    "models": {model: {"limit": {"context": profile.context, "output": profile.output_tokens}}}}},
                "compaction": {"auto": True, "keep": {"tokens": min(8000, profile.context // 4)}, "buffer": profile.output_tokens + 4096},
                "tool_output": {"max_lines": 300, "max_bytes": 16000},
                "experimental": {"policies": [{"action": "provider.use", "resource": "*", "effect": "deny"},
                                               {"action": "provider.use", "resource": "ollama", "effect": "allow"}]},
                "instructions": [str(instructions)]}
            command = [executable, "run" if verification else "mini", "--standalone", "--model", selected]
            if verification:
                config["permissions"] = [{"action": "*", "resource": "*", "effect": "deny"},
                                         {"action": "read", "resource": "*", "effect": "allow"},
                                         {"action": "edit", "resource": "*", "effect": "allow"}]
        else:
            config = {"model": selected, "small_model": selected, "autoupdate": False, "share": "disabled",
                "enabled_providers": ["ollama"], "provider": {"ollama": {"npm": "@ai-sdk/openai-compatible", "name": "Local Ollama",
                    "options": {"baseURL": base + "/v1"}, "models": {model: {"name": model, "limit": {"context": profile.context, "output": profile.output_tokens}}}}},
                "compaction": {"auto": True, "prune": True, "reserved": profile.output_tokens + 4096}, "instructions": [str(instructions)]}
            command = [executable, *(["run"] if verification else []), "--model", selected]
            if verification:
                config["permission"] = {"*": "deny", "read": "allow", "edit": "allow"}
        atomic_json(directory / "opencode.json", config)
        env.update({"OPENCODE_CONFIG_CONTENT": json.dumps(config), "OPENCODE_CONFIG": str(directory / "opencode.json"),
                    "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_SHARE": "1"})
    else:
        full = "ollama_chat/" + model
        settings = [{"name": full, "edit_format": "whole", "use_repo_map": profile.map_tokens > 0,
                     "extra_params": {"num_ctx": profile.context, "temperature": profile.temperature}}]
        # JSON is valid YAML; avoid a runtime YAML parser dependency.
        atomic_json(directory / "aider-models.yml", settings)
        atomic_json(directory / "aider-metadata.json", {full: {"max_tokens": profile.context,
                    "max_input_tokens": profile.context - profile.output_tokens, "max_output_tokens": profile.output_tokens,
                    "input_cost_per_token": 0, "output_cost_per_token": 0, "litellm_provider": "ollama_chat", "mode": "chat"}})
        env.update({"OLLAMA_API_BASE": base, "AIDER_ANALYTICS": "false", "AIDER_CHECK_UPDATE": "false"})
        command = [executable, "--model", full, "--weak-model", full, "--editor-model", full,
                   "--set-env", "OLLAMA_API_BASE=" + base,
                   "--model-settings-file", str(directory / "aider-models.yml"), "--model-metadata-file", str(directory / "aider-metadata.json"),
                   "--map-tokens", str(profile.map_tokens), "--max-chat-history-tokens", str(profile.context // 4),
                   "--no-auto-commits", "--no-check-update", "--no-analytics", "--read", str(instructions)]
        if verification:
            (directory / "empty.yml").write_text("{}\n")
            (directory / "empty.env").touch()
            command += ["--config", str(directory / "empty.yml"), "--env-file", str(directory / "empty.env"),
                        "--yes-always", "--no-git", "--no-stream", "--message"]
    if verification:
        # Keep all agent caches/config writes and model-generated edits inside disposable directories.
        env.update({"XDG_DATA_HOME": str(directory / "data"), "XDG_CACHE_HOME": str(directory / "cache"),
                    "XDG_STATE_HOME": str(directory / "state"), "XDG_CONFIG_HOME": str(directory / "config"),
                    "CLAUDE_CONFIG_DIR": str(directory / "claude-home")})
    return command + args, env


def active_sessions(store: Store) -> list[dict]:
    found = []
    for path in (store.root / "sessions").glob("*.json"):
        record = read_json(path, {})
        try:
            pid = int(record["pid"])
            if os.name == "nt":
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
                if handle:
                    try:
                        code = ctypes.c_ulong()
                        if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259:
                            found.append(record)
                    finally:
                        ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(pid, 0)
                found.append(record)
        except PermissionError:
            found.append(record)
        except (ProcessLookupError, KeyError, TypeError, ValueError):
            continue
    return found


@contextlib.contextmanager
def session(store: Store, profile: Profile):
    path = store.root / "sessions" / (uuid.uuid4().hex + ".json")
    with store.lock():
        atomic_json(path, {"pid": os.getpid(), "profile": profile.name, "model": profile.resolved_model,
                          "agent": profile.agent, "endpoint": profile.endpoint})
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def run_profile(store: Store, profile: Profile, args: list[str], *, dry_run: bool = False, verify: bool = False,
                timeout: int = 240, offline: bool = False, gateway_port: int = 0, sandbox_agent: bool = False, json_output: bool = False) -> dict:
    if profile.state != "ready":
        raise LocError("This profile is not ready. Complete setup before launching it.")
    discovery = Discovery(store)
    installed = discovery.detect(profile.agent).require()
    major, version = agent_version(installed.path, profile.agent)
    runtime = Ollama(profile.endpoint)
    item, _ = runtime.local_model(profile.resolved_model or profile.model)
    if item["digest"] != profile.digest:
        raise LocError("Model identity drift detected. Review loc doctor before running this profile.")
    if offline:
        from .offline import offline_run
        return offline_run(store, profile, args, dry_run=dry_run, verify=verify, timeout=timeout, json_output=json_output)
    if dry_run:
        validate_args(profile.agent, args)
        return {"action": "launch preview", "agent": profile.agent, "version": version, "executable": installed.path,
                "model": profile.model, "resolved_model": profile.resolved_model, "runtime": profile.endpoint, "context": profile.context,
                "forwarded_arguments": args, "network": "local inference; agent tools may use the network"}
    with session(store, profile), tempfile.TemporaryDirectory(prefix="loc-session-") as temp:
        directory = Path(temp).resolve()
        with Gateway(runtime, profile, port=gateway_port) as gateway:
            command, env = configuration(profile, gateway.base, directory, installed.path, major, verification=verify)
            cwd = None
            if verify:
                cwd = directory / "workspace"
                cwd.mkdir()
                (cwd / "answer.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
                env["PWD"] = str(cwd)
                prompt = f"Read and edit the existing file {cwd / 'answer.py'}: change add(a, b) so it returns a + b. Make the actual file edit. Do not create other files or run shell commands. Reply briefly after the edit."
                if profile.agent == "opencode":
                    command += ["--file", str(cwd / "answer.py")]
                command += [prompt]
                if profile.agent == "aider":
                    command += [str(cwd / "answer.py")]
            else:
                validate_args(profile.agent, args)
                command += args
            if sandbox_agent:
                from .offline import agent_policy
                command = ["/usr/bin/sandbox-exec", "-p", agent_policy(gateway.server.server_port), *command]
            started = time.monotonic()
            try:
                result = run_agent(command, env, cwd, timeout if verify else None, json_output=json_output)
            except subprocess.TimeoutExpired:
                return {"status": "failed", "reason": "Verification timed out", "elapsed_seconds": round(time.monotonic() - started, 2)}
            except KeyboardInterrupt:
                return {"exit_code": 130}
            evidence = {"agent": profile.agent, "version": version, "model": profile.model, "resolved_model": profile.resolved_model,
                        "exit_code": result.returncode, "inference_requests": gateway.requests,
                        "gateway_errors": gateway.errors, "elapsed_seconds": round(time.monotonic() - started, 2),
                        "tokens": None, "peak_memory_bytes": None}
            if verify:
                import ast
                try:
                    tree = ast.parse((cwd / "answer.py").read_text())
                    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "add")
                    value = function.body[0].value
                    changed = (len(function.body) == 1 and isinstance(function.body[0], ast.Return) and isinstance(value, ast.BinOp)
                               and isinstance(value.op, ast.Add) and isinstance(value.left, ast.Name) and value.left.id == "a"
                               and isinstance(value.right, ast.Name) and value.right.id == "b")
                except (OSError, SyntaxError, StopIteration, AttributeError):
                    changed = False
                evidence.update({"status": "passed" if changed and result.returncode == 0 and gateway.requests > 0 else "failed",
                                 "file_edit_verified": changed, "limitation": "One disposable edit proves basic integration, not general coding quality."})
            return evidence
