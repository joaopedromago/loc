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
    p = argparse.ArgumentParser(prog="loc", description="Set up and run local coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  loc setup daily\n  loc run daily\n  loc run --help\n\nUse --home PATH before the command, or set LOC_HOME.")
    p.add_argument("--version", action="version", version="loc " + __version__, help="Show the loc version and exit.")
    p.add_argument("--home", type=Path, metavar="PATH", help="Folder for loc state (also LOC_HOME).")
    p.add_argument("--json", action="store_true", help="Print results as JSON.")
    subs = p.add_subparsers(dest="command", required=True, title="commands", metavar="COMMAND",
                           help="Run 'loc COMMAND --help' for details.")

    def command(key, description, example, *, actions=None, note=None):
        footer = []
        if actions:
            width = max(map(len, actions))
            footer.append("Actions:\n" + "\n".join(f"  {action:<{width}}  {summary}" for action, summary in actions.items()))
        footer.append("Example:\n  " + example)
        if note:
            footer.append(note)
        sub = subs.add_parser(key, help=description, description=description,
                              formatter_class=argparse.RawDescriptionHelpFormatter, epilog="\n\n".join(footer))
        sub.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print results as JSON.")
        return sub

    def mutation(sub):
        sub.add_argument("--dry-run", action="store_true", help="Preview changes without applying them.")
        sub.add_argument("--yes", action="store_true", help="Skip confirmation for the selected changes.")

    def runtime_address(sub):
        sub.add_argument("--endpoint", default="http://127.0.0.1:11434", metavar="URL",
                         help="Local Ollama URL (default: %(default)s).")

    setup = command("setup", "Create or finish a coding profile.", "loc setup daily --model qwen3-coder:30b",
                    note="A profile pairs an agent with a local model. Existing profiles keep their\nsaved settings. Use a new name to choose different settings.")
    setup.add_argument("name", nargs="?", help="Profile name; asks if omitted in a terminal.")
    setup.add_argument("--agent", choices=["claude", "opencode", "aider"], help="Agent for new profiles (default: claude).")
    setup.add_argument("--model", help="Exact Ollama model tag, e.g. qwen3-coder:30b.")
    setup.add_argument("--context", type=int, metavar="TOKENS", help="Context size in tokens (new profile: 32768).")
    setup.add_argument("--output-tokens", type=int, metavar="TOKENS", help="Max reply tokens (new profile: 4096).")
    setup.add_argument("--map-tokens", type=int, metavar="TOKENS", help="Code-map budget for Aider (new profile: 1024).")
    setup.add_argument("--temperature", type=float, metavar="NUMBER", help="Randomness, 0 to 2 (new profile: 0.2).")
    setup.add_argument("--rtk", action="store_true", default=None, help="Add RTK guidance; install RTK if missing.")
    setup.add_argument("--resume", action="store_true", help="Continue a saved setup.")
    setup.add_argument("--offline", action="store_true", help="Use only installed tools and models.")
    setup.add_argument("--accept-model-change", action="store_true", help="Accept a changed model when setting up an import.")
    mutation(setup)
    runtime_address(setup)
    command("scan", "Find installed tools and check your hardware.", "loc scan")
    models = command("models", "List models or find one for your machine.", "loc models recommend --agent claude", actions={
        "list": "Show installed models (default).", "recommend": "Suggest models that fit your machine.",
        "catalog": "Show the saved model catalog.", "refresh": "Fetch catalog updates; needs internet."})
    models.add_argument("action", choices=["list", "recommend", "catalog", "refresh"], nargs="?", default="list", help="What to do; see Actions below.")
    models.add_argument("--name", "-n", dest="names_only", action="store_true", help="For list: print only model names, one per line; --json gives an array.")
    models.add_argument("--agent", choices=["claude", "opencode", "aider"], default=DEFAULT_AGENT, help="Agent to recommend models for (default: %(default)s).")
    models.add_argument("--context", type=int, default=32768, metavar="TOKENS", help="Context size for recommendations (default: %(default)s).")
    models.add_argument("--preference", choices=["balanced", "speed", "quality"], default="balanced", help="What to favor in recommendations (default: %(default)s).")
    models.add_argument("--offline", action="store_true", help="Use local metadata; do not refresh online.")
    runtime_address(models)
    command("profiles", "List saved profiles and the global default.", "loc profiles")
    profiles = command("profile", "View, move, or remove saved profiles.", "loc profile export daily --file daily.json", actions={
        "list": "List saved profiles.", "show": "Show one profile's settings.",
        "remove": "Remove a profile; keep its tools and models.", "export": "Write portable settings to JSON.",
        "import": "Read JSON settings; run setup before using them."})
    profiles.add_argument("action", choices=["list", "show", "remove", "export", "import"], help="What to do; see Actions below.")
    profiles.add_argument("target", nargs="?", help="Profile name, or a JSON file for import.")
    profiles.add_argument("--file", type=Path, metavar="PATH", help="JSON file to import or export.")
    profiles.add_argument("--name", dest="import_name", metavar="NAME", help="Name to give an imported profile.")
    mutation(profiles)
    use = command("use", "Choose the default profile for loc run.", "loc use daily --project")
    use.add_argument("name", help="Saved profile to use by default.")
    use.add_argument("--project", action="store_true", help="Set the default for this repository only.")
    run = command("run", "Start a saved coding profile.", "loc run daily -- --continue",
                  note="Use a profile name, not a model tag. Create one with loc setup.\nArguments after -- go to the agent. Example: loc run daily -- --help\nWithout a name, use the repository default, then the global default.")
    run.add_argument("name", nargs="?", help="Saved profile; uses your default if omitted.")
    run.add_argument("--dry-run", action="store_true", help="Show what would run without starting the agent.")
    run.add_argument("--offline", action="store_true", help="Block outside network access; macOS Claude/Aider only.")
    diagnose = command("doctor", "Check profiles and explain setup problems.", "loc doctor daily --verify")
    diagnose.add_argument("name", nargs="?", help="Profile to check; checks all if omitted.")
    diagnose.add_argument("--verify", action="store_true", help="Ask the agent to edit a temporary test file.")
    diagnose.add_argument("--timeout", type=int, default=240, metavar="SECONDS", help="Time limit for the edit test (default: %(default)s).")
    diagnose.add_argument("--report", nargs="?", const="loc-diagnostic-report.json", type=Path, metavar="PATH", help="Save a local report (default file: loc-diagnostic-report.json).")
    diagnose.add_argument("--offline", action="store_true", help="Run the edit test offline; macOS Claude/Aider only.")
    stat = command("status", "Show profiles, running models, and runtime health.", "loc status daily")
    stat.add_argument("name", nargs="?", help="Profile to inspect; shows all if omitted.")
    runtime_address(stat)
    update = command("update", "Update a profile's model or an installed tool.", "loc update daily --check",
                     note="Choose a profile or --component, not both. For loc itself, use loc self update.")
    update.add_argument("name", nargs="?", help="Profile to update; uses your default if omitted.")
    update.add_argument("--check", action="store_true", help="Check for updates without applying them.")
    update.add_argument("--offline", action="store_true", help="Refuse network updates; leave installed versions in place.")
    update.add_argument("--component", choices=["ollama", "claude", "opencode", "aider", "rtk", "llmfit"], help="Update this tool instead of a profile's model.")
    mutation(update)
    rollback = command("rollback", "Restore a profile's saved model configuration.", "loc rollback daily")
    rollback.add_argument("name", help="Profile with a saved rollback entry.")
    rollback.add_argument("--yes", action="store_true", help="Restore without asking for confirmation.")
    install = command("install", "Install a missing tool, or reuse it if present.", "loc install ollama --dry-run")
    install.add_argument("component", choices=[x for x in TECHNOLOGIES if x != "loc"], help="Tool to install or reuse; unsupported routes give instructions.")
    install.add_argument("--offline", action="store_true", help="Reuse installed tools only; do not download anything.")
    mutation(install)
    uninstall = command("uninstall", "Remove one chosen tool or model.", "loc uninstall model qwen3-coder:30b --dry-run",
                        note="Removal is blocked while the target is in use. Use loc self uninstall\nto remove loc itself.")
    uninstall.add_argument("kind", choices=["agent", "runtime", "helper", "model"], help="Type of item to remove.")
    uninstall.add_argument("target", help="Tool name or exact model tag to remove.")
    uninstall.add_argument("--detach", action="store_true", help="Disable linked profiles and drop their rollback entries.")
    mutation(uninstall)
    runtime_address(uninstall)
    register = command("register", "Tell loc which installed executable to use.", "loc register ollama /path/to/ollama")
    register.add_argument("component", choices=list(TECHNOLOGIES), help="Installed tool to select.")
    register.add_argument("path", type=Path, help="Path to its existing executable; installs nothing.")
    storage = command("storage", "Show model sizes, shared storage, and profile links.", "loc storage")
    runtime_address(storage)
    clean = command("clean", "Find unused model references created by loc.", "loc clean --apply",
                    note="Previews by default. Shared models and models still in use are kept.")
    mutation(clean)
    clean.add_argument("--apply", action="store_true", help="Remove the eligible unused references.")
    runtime_address(clean)
    runtime = command("runtime", "Start or check the local Ollama service.", "loc runtime start", actions={
        "start": "Start the installed service, or reuse it if running.", "status": "Check the service version and address."})
    runtime.add_argument("action", choices=["start", "status"], help="What to do; see Actions below.")
    runtime_address(runtime)
    manager = command("self", "Manage the loc installation itself.", "loc self update --check", actions={
        "info": "Show the version, path, and installation manager.", "update": "Install a newer GitHub release through the same manager.",
        "uninstall": "Remove loc; keep profiles, tools, and models."})
    manager.add_argument("action", choices=["info", "update", "uninstall"], help="What to do; see Actions below.")
    manager.add_argument("--check", action="store_true", help="For update: check without applying changes.")
    manager.add_argument("--offline", action="store_true", help="Block self-update; keep the installed version.")
    mutation(manager)
    complete = command("completion", "Print a script for shell tab completion.", "loc completion zsh",
                       note="Load the output through your shell's completion setup. Shell files are not edited.")
    complete.add_argument("shell", choices=["bash", "zsh", "fish", "powershell"], help="Shell that will use the completion script.")
    command("_complete", "List completion words for shell scripts.", "loc _complete")
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
        return "\n".join(COMMANDS + sorted(store.read()["profiles"]) + ["-h", "--help", "--json", "--dry-run", "--offline", "--yes", "--name", "-n"])
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
        if args.names_only:
            return [model["name"] for model in models]
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
    names_only = args.command == "models" and args.names_only
    store = Store(args.home)
    try:
        if forwarded and args.command != "run":
            raise LocError("Arguments after -- are supported only by loc run.")
        if names_only and args.action != "list":
            raise LocError("--name/-n is only supported by loc models list (the default action).")
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
        elif names_only:
            for model in result:
                print(model)
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
