import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from loc_cli.agents import configuration
from loc_cli.core import Profile
from loc_cli.gateway import Gateway
from loc_cli.ollama import Ollama
from tests.support import RuntimeFixture


PUBLIC = "qwen3-coder:30b"
INTERNAL = "loc-0123456789abcdef:latest"


class ModelIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = RuntimeFixture()
        cls.runtime.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.runtime.__exit__()

    def setUp(self):
        self.runtime.inventory.clear()
        self.runtime.info.clear()
        self.runtime.operations.clear()
        self.runtime.loaded = []
        self.runtime.inference_response = None
        self.runtime.add(PUBLIC)
        self.runtime.add(INTERNAL)
        self.profile = Profile("daily", "claude", PUBLIC, resolved_model=INTERNAL,
                               digest=self.runtime.inventory[INTERNAL]["digest"], endpoint=self.runtime.base).validate()

    def request(self, gateway, route, body=None):
        request = urllib.request.Request(gateway.base + route,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"})
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=5)

    def test_all_agents_receive_public_name_and_model_identity_guidance(self):
        with tempfile.TemporaryDirectory() as temp:
            for agent, major in [("claude", 2), ("opencode", 1), ("opencode", 2), ("aider", 0)]:
                with self.subTest(agent=agent, major=major):
                    self.profile.agent = agent
                    directory = Path(temp) / f"{agent}-{major}"
                    command, env = configuration(self.profile, "http://127.0.0.1:12345", directory, "/agent", major)
                    selected = command[command.index("--model") + 1]
                    self.assertIn(PUBLIC, selected)
                    self.assertNotIn(INTERNAL, json.dumps(command) + json.dumps(env))
                    self.assertIn(f"Inference model: {PUBLIC} (local Ollama)", (directory / "instructions.md").read_text())
                    if agent == "claude":
                        for key in ["ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                                    "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_SMALL_FAST_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"]:
                            self.assertEqual(env[key], PUBLIC)
                    for path in directory.iterdir():
                        self.assertNotIn(INTERNAL, path.read_text())

    def test_discovery_and_loaded_models_publish_original_name(self):
        self.runtime.loaded = [self.runtime.inventory[INTERNAL], self.runtime.inventory[PUBLIC]]
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            for route in ["/api/tags", "/api/ps"]:
                with self.request(gateway, route) as response:
                    rows = json.load(response)["models"]
                self.assertEqual(len(rows), 1)
                self.assertEqual((rows[0]["name"], rows[0]["model"]), (PUBLIC, PUBLIC))
                self.assertEqual(rows[0]["digest"], self.profile.digest)
            with self.request(gateway, "/v1/models") as response:
                self.assertEqual(json.load(response)["data"][0]["id"], PUBLIC)

    def test_public_metadata_reports_configured_alias_settings(self):
        self.runtime.info[PUBLIC]["parameters"] = "num_ctx 8192"
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            for field in ["model", "name"]:
                with self.request(gateway, "/api/show", {field: PUBLIC}) as response:
                    self.assertEqual(json.load(response)["parameters"], "num_ctx 32768")
        self.assertEqual(self.runtime.operations, [])

    def test_every_inference_protocol_routes_public_name_to_pinned_alias(self):
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            for route in ["/api/chat", "/api/generate", "/v1/messages", "/v1/chat/completions", "/v1/completions"]:
                with self.subTest(route=route), self.request(gateway, route, {"model": PUBLIC, "stream": False}) as response:
                    self.assertEqual(json.load(response)["model"], PUBLIC)
                self.assertEqual(self.runtime.operations[-1][1]["model"], INTERNAL)
            self.assertEqual(gateway.errors, 0)

    def test_json_rewrites_metadata_without_changing_generated_content(self):
        payload = {"model": INTERNAL, "content": [{"type": "text", "text": "Inspect " + INTERNAL},
                   {"type": "tool_use", "input": {"model": INTERNAL}}], "usage": {"output_tokens": 7}}
        self.runtime.inference_response = ("application/json", json.dumps(payload).encode())
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            with self.request(gateway, "/v1/messages", {"model": PUBLIC, "stream": False}) as response:
                actual = json.load(response)
        self.assertEqual(actual, {**payload, "model": PUBLIC})

    def test_anthropic_stream_rewrites_message_start_preserving_text_and_events(self):
        start = {"type": "message_start", "message": {"model": INTERNAL, "content": []}}
        delta = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Use " + INTERNAL + " — voilà"}}
        body = ("event: message_start\r\ndata: " + json.dumps(start) + "\r\n\r\n"
                "event: content_block_delta\r\ndata: " + json.dumps(delta, ensure_ascii=False) + "\r\n\r\n"
                "event: message_stop\r\ndata: {\"type\":\"message_stop\"}\r\n\r\n").encode()
        self.runtime.inference_response = ("text/event-stream; charset=utf-8", body)
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            with self.request(gateway, "/v1/messages", {"model": PUBLIC, "stream": True}) as response:
                actual = response.read().decode()
        events = [json.loads(line[5:]) for line in actual.splitlines() if line.startswith("data:")]
        self.assertEqual(events[0]["message"]["model"], PUBLIC)
        self.assertEqual(events[1], delta)
        self.assertIn("event: message_stop\r\n", actual)
        self.assertTrue(actual.endswith("\r\n\r\n"))

    def test_openai_stream_preserves_done_and_tool_payload(self):
        payload = {"model": INTERNAL, "choices": [{"delta": {"tool_calls": [{"function": {"arguments": json.dumps({"model": INTERNAL})}}]}}]}
        body = ("data: " + json.dumps(payload) + "\n\ndata: [DONE]\n\n").encode()
        self.runtime.inference_response = ("text/event-stream", body)
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            with self.request(gateway, "/v1/chat/completions", {"model": PUBLIC, "stream": True}) as response:
                actual = response.read()
        event = json.loads(actual.splitlines()[0][5:])
        self.assertEqual(event, {**payload, "model": PUBLIC})
        self.assertTrue(actual.endswith(b"data: [DONE]\n\n"))

    def test_native_stream_translates_each_model_field_and_preserves_response_text(self):
        events = [{"model": INTERNAL, "response": INTERNAL + " ✓", "done": False},
                  {"model": INTERNAL, "done": True, "eval_count": 4}]
        self.runtime.inference_response = ("application/x-ndjson", b"".join((json.dumps(event, ensure_ascii=False) + "\n").encode() for event in events))
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            with self.request(gateway, "/api/generate", {"model": PUBLIC, "stream": True}) as response:
                actual = [json.loads(line) for line in response]
        self.assertEqual(actual, [{**event, "model": PUBLIC} for event in events])

    def test_public_name_cannot_bypass_alias_digest_checks(self):
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            self.runtime.inventory[INTERNAL]["digest"] = "f" * 64
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(gateway, "/api/chat", {"model": PUBLIC})
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
        self.assertEqual(self.runtime.operations, [])

    def test_source_tag_change_does_not_reroute_inference_away_from_pinned_alias(self):
        self.runtime.inventory[PUBLIC]["digest"] = "f" * 64
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            with self.request(gateway, "/api/chat", {"model": PUBLIC}) as response:
                self.assertEqual(json.load(response)["model"], PUBLIC)
        self.assertEqual(self.runtime.operations[-1][1]["model"], INTERNAL)

    def test_only_public_profile_name_is_accepted(self):
        with Gateway(Ollama(self.runtime.base), self.profile) as gateway:
            for model in [INTERNAL, "another:latest", "qwen:cloud"]:
                with self.subTest(model=model), self.assertRaises(urllib.error.HTTPError) as error:
                    self.request(gateway, "/api/chat", {"model": model})
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
        self.assertEqual(self.runtime.operations, [])


if __name__ == "__main__":
    unittest.main()
