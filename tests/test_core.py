import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from loc_cli.cli import main, completion
from loc_cli.core import LocError, Profile, Store, atomic_json, endpoint, model_name, project_default, redact
from loc_cli.hardware import recommend


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "state")

    def test_normalize_model(self):
        self.assertEqual(model_name("qwen3"), "qwen3:latest")
        self.assertEqual(model_name("user/model:q4"), "user/model:q4")

    def test_reject_unsafe_model_names(self):
        for model in ["../x", "-model", "a b", "https://host/model", "a;rm", "a/b/c", "model:cloud", ""]:
            with self.subTest(model=model), self.assertRaises(LocError):
                model_name(model)

    def test_loopback_only(self):
        self.assertEqual(endpoint("http://localhost:11434/"), "http://127.0.0.1:11434")
        for value in ["https://api.example.com", "http://127.0.0.1:80@evil:90", "http://127.0.0.1:11434/v1", "http://127.0.0.1:11434?x=1", "http://0.0.0.0:11434"]:
            with self.subTest(value=value), self.assertRaises(LocError):
                endpoint(value)

    def test_context_has_useful_headroom(self):
        with self.assertRaises(LocError):
            Profile("a", "claude", "qwen3", context=8192).validate()
        Profile("a", "claude", "qwen3", context=8192, output_tokens=1024, map_tokens=0).validate()

    def test_profile_rejects_unexpected_fields(self):
        with self.assertRaises(LocError):
            Profile.parse({"name": "a", "agent": "claude", "model": "qwen3", "command": "rm -rf"})

    def test_readonly_store_does_not_create_files(self):
        self.store.read()
        self.assertFalse(self.store.root.exists())

    def test_atomic_state_and_reentrant_lock(self):
        with self.store.lock():
            with self.store.lock():
                state = self.store.read()
                state["profiles"]["code"] = asdict(Profile("code", "claude", "qwen3").validate())
                self.store.save(state)
        self.assertIn("code", self.store.read()["profiles"])
        self.assertFalse(list(self.store.root.glob("*.tmp")))

    def test_lock_excludes_other_processes(self):
        script = "from pathlib import Path; from loc_cli.core import Store, LocError; import sys\ntry:\n with Store(Path(sys.argv[1])).lock(timeout=.1): pass\nexcept LocError:\n sys.exit(7)"
        with self.store.lock():
            result = subprocess.run([sys.executable, "-c", script, str(self.store.root)], capture_output=True)
        self.assertEqual(result.returncode, 7, result.stderr)

    def test_corrupt_state_is_preserved(self):
        self.store.root.mkdir()
        self.store.path.write_text("broken")
        with self.assertRaises(LocError):
            self.store.read()
        self.assertEqual(self.store.path.read_text(), "broken")

    def test_future_schema_rejected(self):
        atomic_json(self.store.path, {"schema": 999})
        with self.assertRaises(LocError):
            self.store.read()

    def test_project_default_stops_at_repository_boundary(self):
        atomic_json(self.root / ".loc.json", {"schema": 1, "profile": "outside"})
        repo = self.root / "repo"
        (repo / ".git").mkdir(parents=True)
        child = repo / "src"
        child.mkdir()
        self.assertIsNone(project_default(child))
        atomic_json(repo / ".loc.json", {"schema": 1, "profile": "inside"})
        self.assertEqual(project_default(child), "inside")

    def test_repository_configuration_cannot_execute_commands(self):
        atomic_json(self.root / ".loc.json", {"schema": 1, "profile": "x", "command": "evil"})
        with self.assertRaises(LocError):
            project_default(self.root)

    def test_portable_export_excludes_machine_paths_and_resolved_alias(self):
        p = Profile("code", "claude", "qwen3", resolved_model="loc-foo", digest="a" * 64).validate()
        payload = p.portable()["profile"]
        self.assertNotIn("endpoint", payload)
        self.assertNotIn("resolved_model", payload)
        self.assertNotIn("digest", payload)

    def test_redaction(self):
        result = redact({"api_key": "abc", "authorization": "Bearer secret", "message": str(Path.home()) + "/project"})
        self.assertNotIn("abc", json.dumps(result))
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["message"], "~/project")

    def test_recommendations_label_estimates_and_memory_fit(self):
        result = recommend(self.store, "claude", [], hardware={"memory_bytes": 8 * 1024 ** 3, "disk_free_bytes": 100 * 1024 ** 3})
        self.assertTrue(all("estimated_memory_bytes" in row for row in result["recommendations"]))
        self.assertFalse(all(row["fits_estimate"] for row in result["recommendations"]))

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = main(["--home", str(self.store.root), *args])
        return code, output.getvalue()

    def test_completion_has_no_state_side_effects(self):
        code, output = self.cli("_complete")
        self.assertEqual(code, 0)
        self.assertIn("setup", output)
        self.assertFalse(self.store.root.exists())
        for shell in ["bash", "zsh", "fish", "powershell"]:
            self.assertIn("loc", completion(shell))

    def test_import_is_pending_and_duplicate_name_blocked(self):
        path = self.root / "export.json"
        atomic_json(path, Profile("portable", "claude", "qwen3").validate().portable())
        code, output = self.cli("profile", "import", str(path), "--json")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.store.profile("portable").state, "pending")
        code, _ = self.cli("profile", "import", str(path))
        self.assertEqual(code, 2)

    def test_import_rejects_machine_specific_or_executable_fields(self):
        path = self.root / "export.json"
        data = Profile("portable", "claude", "qwen3").validate().portable()
        data["profile"]["endpoint"] = "http://localhost:12"
        atomic_json(path, data)
        code, _ = self.cli("profile", "import", str(path))
        self.assertEqual(code, 2)

    def test_offline_update_never_fetches(self):
        with patch("loc_cli.distribution.latest_release") as fetch:
            code, output = self.cli("self", "update", "--offline")
            self.assertEqual(code, 2)
            fetch.assert_not_called()

    def test_malformed_profile_is_an_actionable_error(self):
        code, _ = self.cli("setup", "../bad", "--agent", "claude", "--model", "qwen3", "--dry-run")
        self.assertEqual(code, 2)

    def test_status_cli_json_flag_after_command(self):
        code, output = self.cli("profiles", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["profiles"], [])


if __name__ == "__main__":
    unittest.main()
