import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from loc_cli.agents import configuration, validate_args, clean_env
from loc_cli.core import LocError, Profile
from loc_cli.gateway import Gateway
from loc_cli.offline import agent_policy, offline_run
from loc_cli.ollama import Ollama, NoRedirect
from tests.support import RuntimeFixture


class AgentConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_configuration_does_not_modify_parent_environment(self):
        before = dict(os.environ)
        profile = Profile("test", "claude", "qwen3:4b").validate()
        command, env = configuration(profile, "http://127.0.0.1:12345", self.root, "/agent", 2)
        self.assertEqual(dict(os.environ), before)
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "http://127.0.0.1:12345")
        self.assertEqual(env["ANTHROPIC_DEFAULT_HAIKU_MODEL"], profile.model)
        self.assertNotIn("--dangerously-skip-permissions", command)

    def test_inherited_cloud_configuration_is_removed(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret", "OPENAI_BASE_URL": "https://remote", "HTTP_PROXY": "https://proxy", "OPENCODE_CONFIG": "/unrelated"}):
            env = clean_env()
        for key in ["ANTHROPIC_API_KEY", "OPENAI_BASE_URL", "HTTP_PROXY", "OPENCODE_CONFIG"]:
            self.assertNotIn(key, env)

    def test_provider_override_flags_blocked(self):
        for args in [["--model", "cloud"], ["--model=cloud"], ["--settings", "x"], ["--fallback-model", "cloud"], ["--server=https://elsewhere"]]:
            with self.subTest(args=args), self.assertRaises(LocError):
                validate_args("claude", args)
        validate_args("claude", ["--continue"])

    def test_opencode_v2_uses_standalone_and_v2_compaction(self):
        profile = Profile("test", "opencode", "qwen3:4b").validate()
        command, env = configuration(profile, "http://127.0.0.1:12345", self.root, "/agent", 2)
        data = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        self.assertIn("--standalone", command)
        self.assertIn("providers", data)
        self.assertIn("buffer", data["compaction"])
        self.assertNotIn("prune", data["compaction"])

    def test_opencode_v1_uses_v1_schema(self):
        profile = Profile("test", "opencode", "qwen3:4b").validate()
        command, env = configuration(profile, "http://127.0.0.1:12345", self.root, "/agent", 1)
        data = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        self.assertIn("provider", data)
        self.assertTrue(data["compaction"]["prune"])
        self.assertEqual(data["enabled_providers"], ["ollama"])

    def test_aider_pins_all_model_roles_and_context(self):
        profile = Profile("test", "aider", "qwen3:4b").validate()
        command, env = configuration(profile, "http://127.0.0.1:12345", self.root, "/agent", 0)
        self.assertEqual(command[command.index("--weak-model") + 1], "ollama_chat/qwen3:4b")
        settings = json.loads((self.root / "aider-models.yml").read_text())
        self.assertEqual(settings[0]["extra_params"]["num_ctx"], profile.context)
        self.assertNotIn("--yes-always", command)

    def test_unknown_agent_major_rejected(self):
        with self.assertRaises(LocError):
            configuration(Profile("a", "claude", "qwen3:4b").validate(), "http://127.0.0.1:12345", self.root, "/agent", 3)

    def test_unverified_offline_platform_fails_closed(self):
        with patch("loc_cli.offline.platform_name", return_value="windows"):
            with self.assertRaises(LocError):
                offline_run(None, Profile("a", "claude", "qwen3:4b"), [], dry_run=True, verify=False, timeout=2)

    def test_offline_agent_policy_allows_only_gateway_port(self):
        policy = agent_policy(12345)
        self.assertIn("(deny network*)", policy)
        self.assertIn('localhost:12345', policy)
        self.assertNotIn('localhost:*', policy)


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = RuntimeFixture()
        cls.fixture.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.__exit__()

    def setUp(self):
        self.fixture.add("qwen3:4b")
        self.fixture.operations.clear()
        self.profile = Profile("test", "claude", "qwen3:4b", endpoint=self.fixture.base,
                               digest=self.fixture.inventory["qwen3:4b"]["digest"], resolved_model="qwen3:4b").validate()

    def request(self, base, path, data=None):
        request = urllib.request.Request(base + path, data=json.dumps(data).encode() if data else None,
                                         headers={"Content-Type": "application/json"})
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=5)

    def test_gateway_refuses_cloud_and_other_models(self):
        with Gateway(Ollama(self.fixture.base), self.profile) as gateway:
            for name in ["gemma4:cloud", "other:latest"]:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    self.request(gateway.base, "/api/chat", {"model": name, "messages": []})
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
        self.assertEqual(self.fixture.operations, [])

    def test_gateway_blocks_management_and_web_routes(self):
        with Gateway(Ollama(self.fixture.base), self.profile) as gateway:
            for path in ["/api/pull", "/api/delete", "/api/web_search", "/v1/files"]:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    self.request(gateway.base, path, {"model": "qwen3:4b"})
                self.assertEqual(error.exception.code, 403)
                error.exception.close()

    def test_gateway_context_is_enforced(self):
        with Gateway(Ollama(self.fixture.base), self.profile) as gateway:
            with self.request(gateway.base, "/api/chat", {"model": "qwen3:4b", "messages": [], "options": {"num_ctx": 999999}}) as response:
                self.assertEqual(response.status, 200)
        self.assertEqual(self.fixture.operations[-1][1]["options"]["num_ctx"], self.profile.context)

    def test_identity_change_during_session_blocks_inference(self):
        with Gateway(Ollama(self.fixture.base), self.profile) as gateway:
            self.fixture.inventory["qwen3:4b"]["digest"] = "b" * 64
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(gateway.base, "/api/chat", {"model": "qwen3:4b"})
            error.exception.close()
        self.assertEqual(self.fixture.operations, [])

    def test_startup_digest_drift_is_rejected(self):
        self.profile.digest = "c" * 64
        with self.assertRaises(LocError):
            Gateway(Ollama(self.fixture.base), self.profile)

    def test_local_client_blocks_redirects(self):
        with self.assertRaises(LocError):
            NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://cloud.example")

    def test_gateway_inventory_exposes_only_selected_model(self):
        self.fixture.add("other:latest")
        with Gateway(Ollama(self.fixture.base), self.profile) as gateway:
            with self.request(gateway.base, "/api/tags") as response:
                models = json.load(response)["models"]
        self.assertEqual([m["name"] for m in models], ["qwen3:4b"])

    def test_legacy_metadata_name_field_is_supported(self):
        with Gateway(Ollama(self.fixture.base), self.profile) as gateway:
            with self.request(gateway.base, "/api/show", {"name": "qwen3:4b"}) as response:
                self.assertIn("completion", json.load(response)["capabilities"])
            self.assertEqual(gateway.errors, 0)


if __name__ == "__main__":
    unittest.main()
