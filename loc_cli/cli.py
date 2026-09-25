"""The public CLI. JSON output is stable enough for automation and completion."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .agents import run_profile
from .core import LocError, Profile, Store, atomic_json, confirm, model_name, name, project_root, read_json
from .diagnostics import doctor, report, status
from .discovery import Discovery, TECHNOLOGIES
from .distribution import installation_owner, self_uninstall, self_update
from .hardware import DEFAULT_AGENT, catalog, inspect_hardware, recommend, validate_catalog
from .install import Installer, start_runtime
from .lifecycle import Lifecycle
from .network import REPOSITORY, fetch
from .ollama import Ollama


COMMANDS = ["setup", "scan", "models", "profiles", "profile", "use", "run", "doctor", "status", "update", "rollback",
            "install", "uninstall", "register", "storage", "clean", "runtime", "self", "completion"]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="loc", description="Set up, launch, and maintain local coding-agent profiles.")
    p.add_argument("--version", action="version", version="loc " + __version__)
    p.add_argument("--home", type=Path, help="Override the loc state directory (also LOC_HOME).")
    p.add_argument("--json", action="store_true", help="Print structured JSON.")
    subs = p.add_subparsers(dest="command", required=True)

    def command(key, help):
        sub = subs.add_parser(key, help=help)
        sub.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        return sub

    def mutation(sub):
        sub.add_argument("--dry-run", action="store_true", help="Preview without changing the environment.")
        sub.add_argument("--yes", action="store_true", help="Apply the explicitly selected operation without a prompt.")

    def runtime_address(sub):
        sub.add_argument("--endpoint", default="http://127.0.0.1:11434")

    setup = command("setup", "Create or resume a local coding profile.")
    setup.add_argument("name", nargs="?")
    setup.add_argument("--agent", choices=["claude", "opencode", "aider"], help="Agent for a new profile (default: claude); existing profiles keep their agent.")
    setup.add_argument("--model")
    setup.add_argument("--context", type=int)
    setup.add_argument("--output-tokens", type=int)
    setup.add_argument("--map-tokens", type=int)
    setup.add_argument("--temperature", type=float)
    setup.add_argument("--rtk", action="store_true", default=None)
    setup.add_argument("--resume", action="store_true")
    setup.add_argument("--offline", action="store_true")
    setup.add_argument("--accept-model-change", action="store_true")
    mutation(setup)
    runtime_address(setup)
    command("scan", "Discover installed components and hardware.")
    models = command("models", "List installed models or recommend a configuration.")
    models.add_argument("action", choices=["list", "recommend", "catalog", "refresh"], nargs="?", default="list")
    models.add_argument("--agent", choices=["claude", "opencode", "aider"], default=DEFAULT_AGENT)
    models.add_argument("--context", type=int, default=32768)
    models.add_argument("--preference", choices=["balanced", "speed", "quality"], default="balanced")
    models.add_argument("--offline", action="store_true")
    runtime_address(models)
    command("profiles", "List profiles.")
    profiles = command("profile", "Manage portable profile definitions.")
    profiles.add_argument("action", choices=["list", "show", "remove", "export", "import"])
    profiles.add_argument("target", nargs="?")
    profiles.add_argument("--file", type=Path)
    profiles.add_argument("--name", dest="import_name")
    mutation(profiles)
    use = command("use", "Set a global or repository default.")
    use.add_argument("name")
    use.add_argument("--project", action="store_true")
    run = command("run", "Launch the selected agent with session-scoped settings.")
    run.add_argument("name", nargs="?")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--offline", action="store_true")
    diagnose = command("doctor", "Inspect profiles; optionally verify a real disposable file edit.")
    diagnose.add_argument("name", nargs="?")
    diagnose.add_argument("--verify", action="store_true")
    diagnose.add_argument("--timeout", type=int, default=240)
    diagnose.add_argument("--report", nargs="?", const="loc-diagnostic-report.json", type=Path)
    diagnose.add_argument("--offline", action="store_true")
    stat = command("status", "Inspect runtime state without loading models.")
    stat.add_argument("name", nargs="?")
    runtime_address(stat)
    update = command("update", "Check or update a profile's source model; retain rollback references.")
    update.add_argument("name", nargs="?")
    update.add_argument("--check", action="store_true")
    update.add_argument("--offline", action="store_true")
    update.add_argument("--component", choices=["ollama", "claude", "opencode", "aider", "rtk", "llmfit"])
    mutation(update)
    rollback = command("rollback", "Restore a retained model/profile configuration.")
    rollback.add_argument("name")
    rollback.add_argument("--yes", action="store_true")
    install = command("install", "Install a missing supported component or reuse the existing one.")
    install.add_argument("component", choices=[x for x in TECHNOLOGIES if x != "loc"])
    install.add_argument("--offline", action="store_true")
    mutation(install)
    uninstall = command("uninstall", "Remove an explicitly selected component or model.")
    uninstall.add_argument("kind", choices=["agent", "runtime", "helper", "model"])
    uninstall.add_argument("target")
    uninstall.add_argument("--detach", action="store_true", help="Disable affected profiles and discard affected rollback references.")
    mutation(uninstall)
    runtime_address(uninstall)
    register = command("register", "Select an existing executable, including a custom installation location.")
    register.add_argument("component", choices=list(TECHNOLOGIES))
    register.add_argument("path", type=Path)
    storage = command("storage", "Show model ownership, references, and storage estimates.")
    runtime_address(storage)
    clean = command("clean", "Preview or remove unused model references created by loc.")
    mutation(clean)
    clean.add_argument("--apply", action="store_true", help="Apply cleanup; previews are the default.")
    runtime_address(clean)
    runtime = command("runtime", "Start or inspect the existing Ollama runtime.")
    runtime.add_argument("action", choices=["start", "status"])
    runtime_address(runtime)
    manager = command("self", "Inspect, update, or uninstall loc through its original owner.")
    manager.add_argument("action", choices=["info", "update", "uninstall"])
    manager.add_argument("--check", action="store_true")
    manager.add_argument("--offline", action="store_true")
    mutation(manager)
    complete = command("completion", "Print a shell completion script.")
    complete.add_argument("shell", choices=["bash", "zsh", "fish", "powershell"])
    hidden = command("_complete", "Internal shell completion candidates.")
    return p


def completion(shell: str) -> str:
    if shell == "bash":
        return '_loc_complete() { COMPREPLY=(); local candidate; while IFS= read -r candidate; do COMPREPLY+=("$candidate"); done < <(compgen -W "$(loc _complete)" -- "${COMP_WORDS[COMP_CWORD]}"); }\ncomplete -F _loc_complete loc\n'
    if shell == "zsh":
        return '#compdef loc\n_loc_complete() { local -a choices; choices=("${(@f)$(loc _complete)}"); compadd -- "${choices[@]}"; }\ncompdef _loc_complete loc\n'
    if shell == "fish":
        return "complete -c loc -f -a '(loc _complete)'\n"
    return "Register-ArgumentCompleter -Native -CommandName loc -ScriptBlock { param($wordToComplete) loc _complete | Where-Object { $_ -like \"$wordToComplete*\" } | ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) } }\n"


def setup_profile(args, store: Store) -> Profile:
    data = store.read()
    if not args.name:
        if args.resume:
            pending = [x for x in data["profiles"].values() if x["state"] == "pending"]
            if len(pending) == 1:
                return Profile.parse(pending[0])
        if not sys.stdin.isatty():
            raise LocError("Specify a profile name and --model for noninteractive setup. The default agent is claude.")
        args.name = input("Profile name: ").strip()
    prior = data["profiles"].get(args.name)
    if prior:
        profile = Profile.parse(prior)
    else:
        if not args.agent and sys.stdin.isatty():
            args.agent = input("Agent [claude/opencode/aider] (claude, recommended): ").strip() or DEFAULT_AGENT
        args.agent = args.agent or DEFAULT_AGENT
        if not args.model and sys.stdin.isatty():
            try:
                available = Ollama(args.endpoint).recommendation_inventory()
            except LocError:
                available = []
            recommendations = recommend(store, args.agent, available, context=args.context or 32768)
            print(recommendations["selection_note"])
            choices = recommendations["recommendations"][:5]
            for item in choices:
                print(f"  {item['model']} — estimated fit: {item['fits_estimate']}, already installed: {item['installed']}")
            preferred = recommendations["preferred_model"]
            prompt = f"Exact model name ({preferred}, recommended): " if preferred else "Exact model name: "
            args.model = input(prompt).strip() or preferred
        if not args.model:
            raise LocError("New profiles require --model (or an interactive model selection). The default agent is claude.")
        profile = Profile(args.name, args.agent, args.model, endpoint=args.endpoint)
    for key in ("agent", "model", "context", "output_tokens", "map_tokens", "temperature", "rtk"):
        value = getattr(args, key)
        if value is not None:
            setattr(profile, key, value)
    return profile.validate()


def dispatch(args, forwarded: list[str], store: Store):
    command = args.command
    life = Lifecycle(store)
    if command == "_complete":
        return "\n".join(COMMANDS + sorted(store.read()["profiles"]) + ["--help", "--json", "--dry-run", "--offline", "--yes"])
    if command == "completion":
        return completion(args.shell)
    if command == "scan":
        return {"hardware": inspect_hardware(), "components": {key: life.discovery.detect(key).to_dict() for key in TECHNOLOGIES},
                "coverage": "PATH, known native locations, Homebrew/system/Windows records, and common managed environments. Hidden/custom installations require loc register; uncertain detection blocks installation."}
    if command in {"profiles", "profile"}:
        if command == "profiles" or args.action == "list":
            data = store.read()
            return {"default": data.get("default"), "profiles": list(data["profiles"].values())}
        if args.action == "import":
            path = args.file or (Path(args.target) if args.target else None)
            if not path:
                raise LocError("Provide a profile export file.")
            data = read_json(path)
            if not isinstance(data, dict) or set(data) != {"schema", "profile"} or data["schema"] != 1:
                raise LocError("Unsupported profile export.")
            allowed = {"name", "agent", "model", "context", "output_tokens", "map_tokens", "temperature", "runtime", "source_digest", "rtk", "parameters"}
            if not isinstance(data["profile"], dict) or set(data["profile"]) - allowed:
                raise LocError("Export includes unsupported or machine-specific fields.")
            profile = Profile.parse({**data["profile"], **({"name": args.import_name} if args.import_name else {})})
            state = store.read()
            if profile.name in state["profiles"]:
                raise LocError("Profile already exists; choose --name to import under another name.")
            if not args.dry_run:
                state["profiles"][profile.name] = asdict(profile)
                store.save(state)
            return {"profile": asdict(profile), "next": f"loc setup {profile.name} --resume"}
        if not args.target:
            raise LocError("Provide a profile name.")
        profile = store.profile(args.target)
        if args.action == "show":
            return asdict(profile)
        if args.action == "remove":
            return life.remove_profile(profile.name, yes=args.yes, dry_run=args.dry_run)
        if args.action == "export":
            data = profile.portable()
            if args.file and not args.dry_run:
                if args.file.exists():
                    raise LocError("Export destination exists; choose a new file.")
                atomic_json(args.file, data)
                return {"exported": str(args.file)}
            return data
    if command == "setup":
        profile = setup_profile(args, store)
        if args.dry_run:
            return life.setup_plan(profile)
        return life.setup(profile, yes=args.yes, offline=args.offline, accept_model_change=args.accept_model_change)
    if command == "use":
        profile = store.profile(args.name)
        if args.project:
            path = project_root(Path.cwd()) / ".loc.json"
            if path.exists():
                old = read_json(path)
                if not isinstance(old, dict) or set(old) != {"schema", "profile"}:
                    raise LocError("Existing .loc.json contains unknown data; it will not be overwritten.")
            atomic_json(path, {"schema": 1, "profile": profile.name})
            return {"project_default": profile.name, "file": str(path)}
        data = store.read()
        data["default"] = profile.name
        store.save(data)
        return {"default": profile.name}
    if command == "run":
        return run_profile(store, store.profile(args.name), forwarded, dry_run=args.dry_run, offline=args.offline, json_output=args.json)
    if command == "models":
        if args.action == "catalog":
            return catalog(store)
        if args.action == "refresh":
            if args.offline:
                raise LocError("Catalog refresh requires network access and is unavailable offline.")
            raw, _ = fetch(f"https://raw.githubusercontent.com/{REPOSITORY}/main/loc_cli/catalog.json")
            try:
                data = validate_catalog(json.loads(raw))
            except ValueError as exc:
                raise LocError("Invalid catalog response; cached catalog preserved.") from exc
            atomic_json(store.root / "catalog.json", data)
            return {"status": "refreshed", "updated": data["updated"]}
        try:
            runtime = Ollama(args.endpoint)
            models = runtime.recommendation_inventory() if args.action == "recommend" else runtime.models()
        except LocError:
            if args.action != "recommend":
                raise
            models = []
        return {"models": models} if args.action == "list" else recommend(store, args.agent, models, args.context, args.preference)
    if command == "doctor":
        if args.timeout < 1:
            raise LocError("Verification timeout must be positive.")
        result = doctor(store, args.name, verify=args.verify, timeout=args.timeout, offline=args.offline)
        if args.report:
            if args.report.exists():
                raise LocError("Report destination exists; choose a new file.")
            atomic_json(args.report, report(store, result))
            result["report"] = str(args.report)
        return result
    if command == "status":
        return status(store, args.name, args.endpoint)
    if command == "update":
        if args.offline:
            raise LocError("Updates require upstream metadata. Offline profiles remain on their installed models.")
        if args.component:
            if args.name:
                raise LocError("Choose either a profile or --component, not both.")
            from .lifecycle import no_active
            no_active(store, component=args.component)
            return life.installer.update_plan(args.component) if args.check or args.dry_run else life.installer.update(args.component, yes=args.yes)
        profile = store.profile(args.name)
        return life.update_check(profile) if args.check or args.dry_run else life.update(profile, yes=args.yes)
    if command == "rollback":
        return life.rollback(args.name, args.yes)
    if command == "register":
        return life.discovery.register(args.component, args.path.expanduser().absolute())
    if command == "install":
        return life.installer.plan(args.component) if args.dry_run else life.installer.ensure(args.component, yes=args.yes, offline=args.offline)
    if command == "uninstall":
        return life.uninstall(args.kind, args.target, args.endpoint, dry_run=args.dry_run, yes=args.yes, detach=args.detach)
    if command == "storage":
        return life.storage(args.endpoint)
    if command == "clean":
        return life.clean(args.endpoint, dry_run=args.dry_run or not args.apply, yes=args.yes)
    if command == "runtime":
        return start_runtime(store, args.endpoint) if args.action == "start" else {"version": Ollama(args.endpoint).version(), "endpoint": args.endpoint}
    if command == "self":
        if args.action == "info":
            return installation_owner()
        if args.offline and args.action == "update":
            raise LocError("Self-update requires network access; offline mode preserves the current installation.")
        if args.action == "update":
            return self_update(check=args.check, dry_run=args.dry_run, yes=args.yes)
        return self_uninstall(dry_run=args.dry_run, yes=args.yes)
    raise LocError("Unknown command.")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    forwarded = []
    if "--" in argv:
        index = argv.index("--")
        argv, forwarded = argv[:index], argv[index + 1:]
    args = parser().parse_args(argv)
    store = Store(args.home)
    try:
        if forwarded and args.command != "run":
            raise LocError("Arguments after -- are supported only by loc run.")
        mutating = args.command in {"setup", "profile", "use", "update", "rollback", "install", "uninstall", "register", "clean", "runtime", "self"}
        readonly = getattr(args, "dry_run", False) or getattr(args, "check", False)
        if args.command == "profile" and args.action in {"list", "show", "export"}:
            mutating = False
        if args.command == "runtime" and args.action == "status" or args.command == "self" and args.action == "info":
            mutating = False
        if args.command == "clean" and not args.apply:
            mutating = False
        if args.command == "models" and args.action == "refresh":
            mutating = True
        with store.lock() if mutating and not readonly else contextlib.nullcontext():
            with contextlib.redirect_stdout(sys.stderr) if args.json else contextlib.nullcontext():
                result = dispatch(args, forwarded, store)
        if isinstance(result, str):
            print(result)
        elif args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            render(result)
        if isinstance(result, dict):
            if "exit_code" in result and args.command == "run":
                return result["exit_code"] if result["exit_code"] >= 0 else 128 - result["exit_code"]
            if result.get("status") == "failed":
                return 1
        return 0
    except LocError as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}))
        else:
            print("loc: " + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nloc: Interrupted. Retry setup to inspect and resume completed steps.", file=sys.stderr)
        return 130
    except (OSError, ValueError) as exc:
        print(f"loc: {type(exc).__name__}: operation could not complete. Existing state is preserved; run loc doctor.", file=sys.stderr)
        return 2


def render(value, depth: int = 0):
    if isinstance(value, dict):
        for key, item in value.items():
            label = key.replace("_", " ")
            if isinstance(item, (dict, list)):
                print("  " * depth + label + ":")
                render(item, depth + 1)
            else:
                print("  " * depth + f"{label}: {item if item is not None else 'unknown'}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (list, dict)):
                render(item, depth)
                print()
            else:
                print("  " * depth + "- " + str(item))
