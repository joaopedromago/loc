import contextlib
import io
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from loc_cli.cli import parser, setup_profile
from loc_cli.core import LocError, Profile, Store
from loc_cli.hardware import GIB, recommend
from loc_cli.ollama import Ollama
from tests.support import RuntimeFixture


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name) / "state")
        self.hardware = {"memory_bytes": 64 * GIB, "disk_free_bytes": 100 * GIB}

    def test_fitting_qwen_coder_precedes_installed_glm_for_claude(self):
        installed = [{"name": "glm-4.7-flash:q8_0", "size": 31843415736, "capabilities": ["completion", "tools"]}]
        for preference in ("balanced", "speed", "quality"):
            with self.subTest(preference=preference):
                result = recommend(self.store, "claude", installed, preference=preference, hardware=self.hardware)
                self.assertEqual(result["preferred_model"], "qwen3-coder:30b")
                self.assertEqual(result["recommendations"][0]["model"], result["preferred_model"])
                self.assertTrue(result["recommendations"][0]["fits_estimate"])

    def test_small_machine_has_no_qwen_coder_default(self):
        result = recommend(self.store, "claude", [], hardware={**self.hardware, "memory_bytes": 12 * GIB})
        self.assertIsNone(result["preferred_model"])
        self.assertEqual(result["recommendations"][0]["model"], "qwen3:4b")
        self.assertNotIn("qwen2.5-coder:7b", [row["model"] for row in result["recommendations"]])
        self.assertIn("select an alternative explicitly", result["selection_note"])

    def test_zero_budget_is_insufficient_rather_than_unknown(self):
        result = recommend(self.store, "claude", [], hardware={**self.hardware, "memory_bytes": 2 * GIB})
        self.assertTrue(all(row["fits_estimate"] is False for row in result["recommendations"]))

    def test_unknown_memory_does_not_choose_a_default(self):
        result = recommend(self.store, "claude", [], hardware={**self.hardware, "memory_bytes": None})
        self.assertIsNone(result["preferred_model"])

    def test_explicit_agent_keeps_alternative_ranking(self):
        installed = [{"name": "glm-4.7-flash:q8_0", "size": 31843415736, "capabilities": ["completion", "tools"]}]
        result = recommend(self.store, "opencode", installed, hardware=self.hardware)
        self.assertEqual(result["agent"], "opencode")
        self.assertEqual(result["recommendations"][0]["model"], "glm-4.7-flash:q8_0")
        self.assertIsNone(result["preferred_model"])

    def test_custom_installed_coder_uses_metadata_without_loading_or_downloading(self):
        with RuntimeFixture() as runtime:
            # An older installed variant must retain its catalog family priority,
            # instead of tying every custom alias at a generic priority.
            runtime.add("qwen2.5-coder:32b")
            runtime.inventory["qwen2.5-coder:32b"]["size"] = 19000000000
            model = "qwen3.8-coder-q8-64k:latest"
            runtime.add(model)
            runtime.inventory[model].pop("capabilities")
            runtime.inventory[model].pop("details")
            runtime.inventory[model]["size"] = 29978242090
            runtime.info[model]["model_info"] = {"qwen3.context_length": 65536}
            inventory = Ollama(runtime.base).recommendation_inventory()
            result = recommend(self.store, "claude", inventory, context=65536, hardware=self.hardware)
            self.assertEqual(result["preferred_model"], model)
            self.assertEqual(result["recommendations"][0]["context"], 65536)
            self.assertEqual(runtime.operations, [])
            self.assertFalse(self.store.root.exists())

    def test_unverified_or_hosted_install_cannot_fall_back_to_catalog_claims(self):
        runtime = Ollama()
        installed = [{"name": "qwen3-coder:30b", "size": 19000000000}]
        for info in ({"remote_model": "hosted", "capabilities": ["completion", "tools"]},
                     {"capabilities": ["embedding"]}, LocError("metadata unavailable")):
            with self.subTest(info=info), patch.object(runtime, "models", return_value=installed):
                options = {"side_effect": info} if isinstance(info, Exception) else {"return_value": info}
                with patch.object(runtime, "show", **options):
                    result = recommend(self.store, "claude", runtime.recommendation_inventory(), hardware=self.hardware)
                self.assertNotIn("qwen3-coder:30b", [row["model"] for row in result["recommendations"]])

    def test_new_noninteractive_profile_defaults_to_claude_with_explicit_model(self):
        args = parser().parse_args(["setup", "daily", "--model", "qwen3-coder:30b"])
        with patch("sys.stdin.isatty", return_value=False):
            profile = setup_profile(args, self.store)
        self.assertEqual((profile.agent, profile.model, profile.endpoint),
                         ("claude", "qwen3-coder:30b", "http://127.0.0.1:11434"))

    def test_noninteractive_setup_does_not_silently_select_or_download_a_model(self):
        args = parser().parse_args(["setup", "daily", "--yes"])
        with patch("sys.stdin.isatty", return_value=False), self.assertRaisesRegex(LocError, "require --model"):
            setup_profile(args, self.store)
        self.assertFalse(self.store.root.exists())

    def test_existing_profile_keeps_its_agent_and_model(self):
        existing = Profile("existing", "aider", "glm-4.7-flash:q8_0").validate()
        data = self.store.read()
        data["profiles"][existing.name] = asdict(existing)
        self.store.save(data)
        with patch("sys.stdin.isatty", return_value=False):
            profile = setup_profile(parser().parse_args(["setup", "existing", "--resume"]), self.store)
        self.assertEqual((profile.agent, profile.model), (existing.agent, existing.model))

    def test_interactive_enter_selects_fitting_coder_and_requested_context(self):
        args = parser().parse_args(["setup", "daily", "--context", "65536"])
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["", ""]), \
             patch("loc_cli.cli.Ollama.recommendation_inventory", return_value=[]), \
             patch("loc_cli.hardware.inspect_hardware", return_value=self.hardware), contextlib.redirect_stdout(io.StringIO()):
            profile = setup_profile(args, self.store)
        self.assertEqual((profile.agent, profile.model, profile.context), ("claude", "qwen3-coder:30b", 65536))

    def test_interactive_fallback_requires_explicit_model_choice(self):
        args = parser().parse_args(["setup", "daily"])
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["", ""]), \
             patch("loc_cli.cli.Ollama.recommendation_inventory", return_value=[]), \
             patch("loc_cli.hardware.inspect_hardware", return_value={**self.hardware, "memory_bytes": 8 * GIB}), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(LocError, "require --model"):
            setup_profile(args, self.store)


if __name__ == "__main__":
    unittest.main()
