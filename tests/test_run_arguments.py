import contextlib
import io
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from loc_cli.agents import configuration, validate_args
from loc_cli.cli import main
from loc_cli.core import Profile, Store


class RunArgumentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "run")
        data = self.store.read()
        data["profiles"] = {name: asdict(Profile(name, "claude", "qwen3:4b").validate())
                            for name in ("daily", "fast")}
        data["default"] = "daily"
        self.store.save(data)
        self.before = self.store.path.read_bytes()

    def invoke(self, args, *, leading=None):
        output = io.StringIO()

        def launch(store, profile, forwarded, **kwargs):
            validate_args(profile.agent, forwarded)
            return {"exit_code": 0}

        with patch("loc_cli.cli.run_profile", side_effect=launch) as run, \
                patch("loc_cli.core.project_default", return_value=None), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = main(["--home", str(self.store.root), *(leading or []), *args])
        self.assertEqual(self.store.path.read_bytes(), self.before)
        return code, output.getvalue(), run

    def test_permission_flag_reaches_default_and_explicit_profiles(self):
        for selected in ([], ["fast"]):
            with self.subTest(selected=selected):
                code, output, run = self.invoke(["run", *selected, "--dangerously-skip-permissions"])
                self.assertEqual(code, 0, output)
                self.assertEqual(run.call_args.args[1].name, "fast" if selected else "daily")
                self.assertEqual(run.call_args.args[2], ["--dangerously-skip-permissions"])

    def test_agent_option_values_are_not_profile_names(self):
        for forwarded in (["--effort", "low"], ["--tools", "Read,Edit,Write"],
                          ["-p", "Explain this code", "--output-format", "json"],
                          ["--resume", "daily"], ["--effort=low", "--continue"]):
            with self.subTest(forwarded=forwarded):
                code, output, run = self.invoke(["run", *forwarded])
                self.assertEqual(code, 0, output)
                self.assertEqual(run.call_args.args[1].name, "daily")
                self.assertEqual(run.call_args.args[2], forwarded)

    def test_loc_options_before_agent_options_are_preserved(self):
        for args in (["run", "fast", "--offline", "--dry-run", "--json", "--continue"],
                     ["run", "--json", "--dry-run", "--offline", "fast", "--continue"]):
            with self.subTest(args=args):
                code, output, run = self.invoke(args)
                self.assertEqual(code, 0, output)
                self.assertEqual(json.loads(output), {"exit_code": 0})
                self.assertEqual(run.call_args.args[1].name, "fast")
                self.assertEqual(run.call_args.args[2], ["--continue"])
                self.assertEqual(run.call_args.kwargs, {"dry_run": True, "offline": True, "json_output": True})

    def test_remaining_agent_arguments_are_forwarded_verbatim(self):
        for forwarded in (["-p", "--json", "--offline"], ["--continue", "--help"],
                          ["--tools", "Read", "Edit", "--", "--dry-run"],
                          ["--off"], ["--dry-run=true"], ["Explain this code", "--help"]):
            with self.subTest(forwarded=forwarded):
                code, output, run = self.invoke(["run", "fast", *forwarded])
                self.assertEqual(code, 0, output)
                self.assertEqual(run.call_args.args[2], forwarded)
                self.assertFalse(run.call_args.kwargs["offline"])
                self.assertFalse(run.call_args.kwargs["dry_run"])

    def test_explicit_separator_still_forwards_overlapping_flags(self):
        forwarded = ["--help", "--json", "--offline", "--", "literal"]
        for selected in ([], ["fast"]):
            with self.subTest(selected=selected):
                code, output, run = self.invoke(["run", *selected, "--", *forwarded])
                self.assertEqual(code, 0, output)
                self.assertEqual(run.call_args.args[2], forwarded)

    def test_global_options_and_home_named_run_do_not_confuse_command(self):
        with patch("loc_cli.cli.Store", return_value=self.store) as store:
            code, output, run = self.invoke(["run", "--effort", "low"], leading=["--home", "run", "--json"])
        store.assert_called_once_with(Path("run"))
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output), {"exit_code": 0})
        self.assertEqual(run.call_args.args[2], ["--effort", "low"])
        with self.assertRaises(SystemExit) as error, contextlib.redirect_stderr(io.StringIO()):
            self.invoke(["models", "--unknown-agent-option"])
        self.assertEqual(error.exception.code, 2)

    def test_run_help_exits_before_launch_or_state_access(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag), patch("loc_cli.cli.Store") as store, \
                    self.assertRaises(SystemExit) as error, contextlib.redirect_stdout(io.StringIO()):
                main(["run", "fast", flag])
            self.assertEqual(error.exception.code, 0)
            store.assert_not_called()

    def test_model_and_provider_overrides_are_still_rejected(self):
        for forwarded in (["--model", "other"], ["--model=other"], ["--settings", "config.json"]):
            with self.subTest(forwarded=forwarded):
                code, output, _ = self.invoke(["run", *forwarded])
                self.assertEqual(code, 2)
                self.assertIn("override the local profile", output)

    def test_requested_permission_flag_is_passed_to_claude_without_global_changes(self):
        profile = self.store.profile("fast")
        command, env = configuration(profile, "http://127.0.0.1:12345", self.root / "session", "/claude", 2,
                                     args=["--dangerously-skip-permissions"])
        self.assertEqual(command[-1], "--dangerously-skip-permissions")
        self.assertEqual(command.count("--dangerously-skip-permissions"), 1)
        settings = json.loads((self.root / "session/claude.json").read_text())
        self.assertNotIn("permissions", settings)
        self.assertEqual(self.store.path.read_bytes(), self.before)


if __name__ == "__main__":
    unittest.main()
