import contextlib
import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from loc_cli.core import LocError, Profile, Store
from loc_cli.discovery import Detection, Installation
from loc_cli.lifecycle import Lifecycle, model_key, references
from loc_cli.ollama import Ollama
from tests.support import RuntimeFixture


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime_fixture = RuntimeFixture()
        cls.runtime_fixture.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.runtime_fixture.__exit__()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "state")
        self.life = Lifecycle(self.store)
        self.fake = self.runtime_fixture
        self.fake.inventory.clear()
        self.fake.info.clear()
        self.fake.operations.clear()
        self.fake.loaded = []
        self.fake.fail_pull = False
        self.fake.add("qwen3:4b")
        self.profile = Profile("code", "claude", "qwen3:4b", endpoint=self.fake.base).validate()
        self.addCleanup(patch.stopall)
        patch("loc_cli.lifecycle.agent_version", return_value=(2, "2.1.0")).start()
        patch.object(self.life.discovery, "detect", side_effect=lambda key, **kw: Detection(key, "present", [Installation("/fixture/" + key, "manual", "fixture")])).start()
        patch("loc_cli.lifecycle.inspect_hardware", return_value={"disk_free_bytes": 1_000_000_000_000}).start()

    def setup(self):
        with self.store.lock():
            return self.life.setup(self.profile, yes=True)

    def test_existing_model_is_reused_and_setup_is_idempotent(self):
        self.setup()
        self.setup()
        self.assertEqual([x[0] for x in self.fake.operations], ["create"])
        self.assertEqual(self.store.profile("code").state, "ready")

    def test_two_profiles_share_configuration_and_weights(self):
        first = self.setup()
        self.profile.name = "second"
        second = self.setup()
        self.assertEqual(first["profile"]["resolved_model"], second["profile"]["resolved_model"])
        self.assertEqual([x[0] for x in self.fake.operations], ["create"])

    def test_dry_run_has_no_mutation(self):
        self.life.setup_plan(self.profile)
        self.assertFalse(self.store.path.exists())
        self.assertEqual(self.fake.operations, [])

    def test_failed_download_stays_pending_then_resumes(self):
        self.profile.model = "new-model:latest"
        self.fake.fail_pull = True
        with self.assertRaises(LocError):
            self.setup()
        self.assertEqual(self.store.profile("code").state, "pending")
        self.fake.fail_pull = False
        self.setup()
        self.assertEqual(self.store.profile("code").state, "ready")

    def test_setup_rejects_overwriting_profile_configuration(self):
        self.setup()
        self.profile.context = 16384
        with self.assertRaises(LocError):
            self.setup()

    def test_missing_model_offline_is_not_pulled(self):
        self.profile.model = "missing:latest"
        with self.assertRaises(LocError):
            self.life.setup(self.profile, yes=True, offline=True)
        self.assertEqual(self.fake.operations, [])

    def test_cloud_redirect_model_is_rejected(self):
        self.fake.info["qwen3:4b"]["remote_host"] = "https://cloud.example"
        with self.assertRaises(LocError):
            self.setup()
        self.assertEqual(self.fake.operations, [])

    def test_imported_source_digest_mismatch_is_not_accepted_silently(self):
        self.profile.source_digest = "b" * 64
        with self.assertRaises(LocError):
            self.setup()
        self.assertEqual(self.store.profile("code").state, "pending")

    def test_model_without_tools_rejected_for_claude(self):
        self.fake.info["qwen3:4b"]["capabilities"] = ["completion"]
        with self.assertRaises(LocError):
            self.setup()

    def test_profile_removal_preserves_all_models(self):
        self.setup()
        before = set(self.fake.inventory)
        self.life.remove_profile("code", yes=True)
        self.assertEqual(before, set(self.fake.inventory))
        self.assertEqual(self.store.read()["profiles"], {})

    def test_referenced_model_cannot_be_uninstalled_implicitly(self):
        self.setup()
        with self.assertRaises(LocError):
            self.life.uninstall("model", self.profile.resolved_model, self.fake.base, yes=True)
        self.assertIn(self.profile.resolved_model, self.fake.inventory)

    def test_explicit_model_removal_disables_references(self):
        self.setup()
        self.life.uninstall("model", self.profile.resolved_model, self.fake.base, yes=True, detach=True)
        self.assertNotIn(self.profile.resolved_model, self.fake.inventory)
        self.assertEqual(self.store.profile("code").state, "disabled")

    def test_loaded_model_is_preserved(self):
        self.setup()
        self.fake.loaded = [{"name": self.profile.resolved_model}]
        with self.assertRaises(LocError):
            self.life.uninstall("model", self.profile.resolved_model, self.fake.base, yes=True, detach=True)

    def test_cleanup_only_selects_owned_unreferenced_models(self):
        self.setup()
        alias = self.profile.resolved_model
        self.life.remove_profile("code", yes=True)
        report = self.life.clean(self.fake.base)
        self.assertEqual(report["candidates"], [alias])
        self.assertIn(alias, self.fake.inventory)
        self.life.clean(self.fake.base, dry_run=False, yes=True)
        self.assertIn("qwen3:4b", self.fake.inventory)
        self.assertNotIn(alias, self.fake.inventory)

    def test_removal_preview_does_not_delete(self):
        self.setup()
        result = self.life.uninstall("model", self.profile.resolved_model, self.fake.base, dry_run=True)
        self.assertEqual(result["references"], ["code"])
        self.assertFalse(any(x[0] == "delete" for x in self.fake.operations))

    def test_absent_uninstall_is_idempotent(self):
        result = self.life.uninstall("model", "missing:latest", self.fake.base, yes=True)
        self.assertEqual(result["action"], "already absent")

    def test_storage_does_not_sum_shared_weights(self):
        self.setup()
        self.assertIsNone(self.life.storage(self.fake.base)["total_physical_bytes"])

    def test_rollback_requires_retained_artifact(self):
        self.setup()
        data = self.store.read()
        previous = asdict(self.profile)
        previous["resolved_model"] = "missing:latest"
        data["history"]["code"] = [previous]
        self.store.save(data)
        with self.assertRaises(LocError):
            self.life.rollback("code", True)

    def test_failed_update_retains_working_profile(self):
        self.setup()
        original = self.store.read()["profiles"]["code"]
        with patch.object(self.life, "update_check", return_value={"update_available": True, "source": "new:latest", "estimated_download_bytes": 1}), patch("loc_cli.lifecycle.run_profile", return_value={"status": "failed"}):
            with self.assertRaises(LocError):
                self.life.update(self.profile, yes=True)
        self.assertEqual(self.store.read()["profiles"]["code"], original)

    def test_successful_update_retains_rollback_and_can_restore(self):
        self.setup()
        original_model = self.profile.resolved_model
        with patch.object(self.life, "update_check", return_value={"update_available": True, "source": "new:latest", "estimated_download_bytes": 1}), patch("loc_cli.lifecycle.run_profile", return_value={"status": "passed"}):
            self.life.update(self.profile, yes=True)
        self.assertNotEqual(self.store.profile("code").resolved_model, original_model)
        self.life.rollback("code", True)
        self.assertEqual(self.store.profile("code").resolved_model, original_model)

    def test_stopped_runtime_uninstall_preview_does_not_require_running_service(self):
        with patch.object(self.life.installer, "removal_plan", return_value={"action": "manual", "path": "/fixture/ollama"}), patch("loc_cli.lifecycle.Ollama.loaded", side_effect=LocError("runtime stopped")):
            result = self.life.uninstall("runtime", "ollama", self.fake.base, dry_run=True)
        self.assertIsNone(result["loaded"])

    def test_profile_removal_preview_is_available_during_active_session(self):
        self.setup()
        with patch("loc_cli.lifecycle.no_active", side_effect=LocError("active")):
            result = self.life.remove_profile("code", dry_run=True)
        self.assertEqual(result["profile"], "code")


if __name__ == "__main__":
    unittest.main()
