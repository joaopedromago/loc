"""A per-session loopback gateway restricted to one locally verified model."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .core import LocError, Profile, model_name
from .ollama import Ollama


class Gateway:
    def __init__(self, runtime: Ollama, profile: Profile, port: int = 0):
        self.runtime, self.profile = runtime, profile
        self.model = profile.resolved_model or profile.model
        self.item, self.info = runtime.local_model(self.model)
        if profile.digest and self.item["digest"] != profile.digest:
            raise LocError("The selected model digest changed. Inspect 'loc doctor' before running or updating.")
        self.requests = 0
        self.errors = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send_json(self, value, code=200):
                raw = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                route = urlsplit(self.path).path
                if route == "/api/tags":
                    self.send_json({"models": [outer.item]})
                elif route == "/v1/models":
                    self.send_json({"object": "list", "data": [{"id": outer.model, "object": "model", "owned_by": "local"}]})
                elif route == "/api/version":
                    self.send_json({"version": outer.runtime.version()})
                elif route == "/api/ps":
                    self.send_json({"models": [m for m in outer.runtime.loaded() if m.get("name") == outer.model]})
                else:
                    self.send_json({"error": "This local gateway only exposes model inference."}, 403)

            def do_POST(self):
                route = urlsplit(self.path).path
                if route not in {"/api/show", "/api/chat", "/api/generate", "/v1/messages", "/v1/chat/completions", "/v1/completions", "/v1/messages/count_tokens"}:
                    self.send_json({"error": "This operation is not allowed by the local inference gateway."}, 403)
                    return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if size <= 0 or size > 16 * 1024 * 1024:
                        raise LocError("Invalid request size.")
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict) or model_name(body.get("model", body.get("name", ""))) != outer.model:
                        raise LocError("The requested model differs from the selected local profile.")
                    if route == "/api/show":
                        self.send_json(outer.info)
                        return
                    # Revalidate local identity before inference, including updates made outside loc.
                    actual, _ = outer.runtime.local_model(outer.model)
                    if actual["digest"] != outer.item["digest"]:
                        raise LocError("Model changed during this session; start a new verified session.")
                    if route in {"/api/chat", "/api/generate"}:
                        body["options"] = {**body.get("options", {}), "num_ctx": outer.profile.context,
                                           "num_predict": outer.profile.output_tokens, "temperature": outer.profile.temperature}
                    else:
                        body["max_tokens"] = min(body.get("max_tokens") or outer.profile.output_tokens, outer.profile.output_tokens)
                        body["temperature"] = outer.profile.temperature
                    outer.requests += 1
                    with outer.runtime.open(route, body, timeout=600) as upstream:
                        self.send_response(upstream.status)
                        self.send_header("Content-Type", upstream.headers.get("Content-Type", "application/json"))
                        self.send_header("Connection", "close")
                        self.end_headers()
                        while chunk := upstream.read1(8192):
                            self.wfile.write(chunk)
                            self.wfile.flush()
                except (LocError, ValueError, TypeError) as exc:
                    outer.errors += 1
                    self.send_json({"error": str(exc) if isinstance(exc, LocError) else "Invalid inference request."}, 400)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
