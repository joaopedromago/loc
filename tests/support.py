from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class RuntimeFixture:
    """A real local HTTP fixture, with observable downloads and shared configurations."""
    def __init__(self):
        self.inventory = {}
        self.info = {}
        self.operations = []
        self.loaded = []
        self.fail_pull = False
        self.version = "0.34.3"
        self.add("qwen3:4b")
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, value, code=200):
                body = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/api/tags":
                    self.respond({"models": list(fixture.inventory.values())})
                elif self.path == "/api/ps":
                    self.respond({"models": fixture.loaded})
                elif self.path == "/api/version":
                    self.respond({"version": fixture.version})
                else:
                    self.respond({}, 404)

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                model = data.get("model")
                if self.path == "/api/show":
                    self.respond(fixture.info.get(model, {}), 200 if model in fixture.inventory else 404)
                elif self.path == "/api/pull":
                    fixture.operations.append(("pull", model))
                    if fixture.fail_pull:
                        self.respond({"error": "interrupted"})
                    else:
                        fixture.add(model)
                        self.respond({"status": "success"})
                elif self.path == "/api/create":
                    fixture.operations.append(("create", model))
                    fixture.add(model, digest=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest())
                    fixture.info[model]["parameters"] = "\n".join(f"{k} {v}" for k, v in data["parameters"].items())
                    self.respond({"status": "success"})
                elif self.path == "/api/copy":
                    source, target = data["source"], data["destination"]
                    fixture.add(target, digest=fixture.inventory[source]["digest"])
                    self.respond({})
                elif self.path in {"/api/chat", "/v1/messages", "/v1/chat/completions"}:
                    fixture.operations.append(("inference", data))
                    self.respond({"message": {"role": "assistant", "content": "ok"}, "done": True})
                else:
                    self.respond({}, 404)

            def do_DELETE(self):
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                fixture.operations.append(("delete", data["model"]))
                fixture.inventory.pop(data["model"], None)
                fixture.info.pop(data["model"], None)
                self.respond({})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def add(self, model, digest=None):
        self.inventory[model] = {"name": model, "model": model, "size": 2_500_000_000,
                                 "digest": digest or hashlib.sha256(model.encode()).hexdigest(),
                                 "capabilities": ["completion", "tools"], "details": {"context_length": 32768}}
        self.info[model] = {"capabilities": ["completion", "tools"], "parameters": "num_ctx 32768",
                            "model_info": {"qwen3.context_length": 32768}}

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
