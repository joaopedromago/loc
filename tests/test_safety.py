import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loc_cli.agents import run_agent
from loc_cli.core import LocError, Profile, Store, atomic_json
from loc_cli.discovery import Detection, Installation, Discovery
from loc_cli.hardware import validate_catalog
from loc_cli.install import Installer
from loc_cli.ollama import parameters
from loc_cli.storage import physical_storage


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "state")

    def test_corrupt_model_ownership_blocks_cleanup(self):
        data = self.store.read()
        data["models"]["http://127.0.0.1:11434|qwen3:4b"] = {"model": "qwen3:4b", "endpoint": "http://127.0.0.1:11434", "installed_by_loc": "yes"}
        atomic_json(self.store.path, data)
        with self.assertRaises(LocError):
            self.store.read()

    def test_mismatched_ownership_identity_is_rejected(self):
        data = self.store.read()
        data["models"]["wrong"] = {"model": "qwen3:4b", "endpoint": "http://127.0.0.1:11434", "installed_by_loc": True}
        atomic_json(self.store.path, data)
        with self.assertRaises(LocError):
            self.store.read()

    def test_corrupt_default_is_rejected(self):
        data = self.store.read()
        data["default"] = ["invalid"]
        atomic_json(self.store.path, data)
        with self.assertRaises(LocError):
            self.store.read()

    def test_ambiguous_package_record_requires_selection_even_with_one_executable(self):
        detection = Detection("claude", "multiple", [Installation("/one/claude", "native", "path"), Installation(None, "npm", "package", False)])
        with self.assertRaises(LocError):
            detection.require()

    def test_explicit_selection_resolves_multiple_installations(self):
        detection = Detection("claude", "multiple", [Installation("/one/claude", "native", "path"), Installation("/two/claude", "npm", "path")], selected="/two/claude")
        self.assertEqual(detection.require().path, "/two/claude")

    def test_live_runtime_without_executable_is_reused(self):
        discovery = Discovery(self.store)
        with patch.object(discovery, "detect", return_value=Detection("ollama", "absent")), patch("loc_cli.install.Ollama.version", return_value="0.34.3"), patch("loc_cli.install.subprocess.run") as run:
            result = Installer(self.store, discovery).ensure("ollama", yes=True)
            self.assertEqual(result["action"], "reuse service")
            run.assert_not_called()

    def test_aider_incompatible_python_does_not_download_another(self):
        discovery = Discovery(self.store)
        with patch.object(discovery, "detect", return_value=Detection("aider", "absent")), patch("loc_cli.install.existing_aider_python", return_value=None), patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                Installer(self.store, discovery).ensure("aider", yes=True)
            run.assert_not_called()

    def test_context_parameter_check_is_exact(self):
        self.assertEqual(parameters({"parameters": "num_ctx 132768\ntemperature 0.2"})["num_ctx"], 132768)
        self.assertNotEqual(parameters({"parameters": "num_ctx 132768"})["num_ctx"], 32768)

    def test_sampling_fields_are_declarative(self):
        p = Profile("code", "aider", "qwen3:4b", parameters={"top_k": 20, "top_p": 0.95}).validate()
        self.assertEqual(p.portable()["profile"]["parameters"]["top_k"], 20)
        with self.assertRaises(LocError):
            Profile("code", "aider", "qwen3:4b", parameters={"command": "run"}).validate()

    def test_catalog_requires_freshness_date(self):
        with self.assertRaises(LocError):
            validate_catalog({"schema": 1, "models": []})

    def test_storage_requires_matching_runtime_identity(self):
        result = physical_storage([{"name": "model:latest", "digest": "a" * 64}], self.root)
        self.assertIsNone(result["allocated_bytes"])

    def test_shared_storage_hardlinks_count_once(self):
        blobs = self.root / "blobs"
        blobs.mkdir()
        manifest = self.root / "manifests/registry.ollama.ai/library/model/latest"
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(b"manifest")
        (blobs / "sha256-one").write_bytes(b"abc")
        try:
            os.link(blobs / "sha256-one", blobs / "sha256-two")
        except OSError:
            self.skipTest("Hardlinks unavailable")
        result = physical_storage([{"name": "model:latest", "digest": hashlib.sha256(b"manifest").hexdigest()}], self.root)
        self.assertEqual(result["logical_blob_bytes"], 3)

    def test_verification_timeout_is_bounded(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run_agent([sys.executable, "-c", "import time; time.sleep(30)"], dict(os.environ), self.root, 0.1)

    def test_agent_exit_status_is_preserved(self):
        result = run_agent([sys.executable, "-c", "raise SystemExit(7)"], dict(os.environ), self.root, 5)
        self.assertEqual(result.returncode, 7)

    def test_native_opencode_uninstall_keeps_configuration_and_data(self):
        discovery = Discovery(self.store)
        detection = Detection("opencode", "present", [Installation("/native/opencode", "native", "fixture")])
        with patch.object(discovery, "detect", return_value=detection):
            command = Installer(self.store, discovery).removal_plan("opencode")["command"]
        self.assertIn("--keep-config", command)
        self.assertIn("--keep-data", command)

    def test_unknown_update_owner_never_falls_back(self):
        discovery = Discovery(self.store)
        detection = Detection("claude", "present", [Installation("/custom/claude", "unknown", "fixture")])
        with patch.object(discovery, "detect", return_value=detection), patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                Installer(self.store, discovery).update("claude", yes=True)
            run.assert_not_called()

    def test_active_component_is_not_uninstalled(self):
        installer = Installer(self.store)
        plan = {"action": "uninstall", "path": "/native/opencode", "owner": "native", "command": ["/native/opencode", "uninstall"]}
        with patch.object(installer, "removal_plan", return_value=plan), patch("loc_cli.install.running_component", return_value=True), patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                installer.remove("opencode", yes=True)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
