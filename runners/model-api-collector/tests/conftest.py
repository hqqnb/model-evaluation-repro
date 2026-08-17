import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest


@pytest.fixture
def fake_server():
    state = SimpleNamespace(requests=[], retry_counts={})

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            request_json = json.loads(body)
            state.requests.append(
                {
                    "path": self.path,
                    "headers": dict(self.headers),
                    "json": request_json,
                }
            )

            if self.path == "/status/429":
                self._send_json(
                    429,
                    {"error": {"message": "rate limited", "type": "rate_limit"}},
                )
                return
            if self.path == "/v1/chat/completions-json":
                self._send_json(
                    200,
                    {
                        "choices": [
                            {
                                "message": {"content": "normal answer"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 2, "completion_tokens": 2},
                    },
                )
                return
            if self.path == "/v1/responses-incomplete-json":
                self._send_json(
                    200,
                    {
                        "model": "Opus 5",
                        "status": "incomplete",
                        "output": [],
                    },
                )
                return
            if self.path == "/convert-not-implemented":
                self._send_json(
                    500,
                    {
                        "error": {
                            "type": "convert_request_failed",
                            "message": "not implemented",
                        }
                    },
                )
                return
            if self.path == "/retry-once":
                count = state.retry_counts.get(self.path, 0) + 1
                state.retry_counts[self.path] = count
                if count == 1:
                    self._send_json(
                        503,
                        {"error": {"message": "temporary upstream failure"}},
                    )
                    return
                self._send_json(
                    200,
                    {
                        "choices": [
                            {
                                "message": {"content": "recovered answer"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 2, "completion_tokens": 2},
                    },
                )
                return
            if self.path == "/upstream-404-once":
                count = state.retry_counts.get(self.path, 0) + 1
                state.retry_counts[self.path] = count
                if count == 1:
                    self._send_json(
                        404,
                        {
                            "error": {
                                "message": "bad response status code 404",
                                "type": "upstream_error",
                                "code": "bad_response_status_code",
                            }
                        },
                    )
                    return
                self._send_json(
                    200,
                    {
                        "choices": [
                            {
                                "message": {"content": "recovered upstream answer"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                    },
                )
                return
            if self.path == "/v1/responses" and not request_json.get(
                "stream", True
            ):
                self._send_json(
                    200,
                    {
                        "model": "Opus 5",
                        "status": "completed",
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": "normal response",
                                    }
                                ],
                            }
                        ],
                        "usage": {
                            "input_tokens": 4,
                            "output_tokens": 2,
                            "total_tokens": 6,
                        },
                    },
                )
                return

            if self.path == "/slow":
                time.sleep(0.2)
                self._send_json(200, {"choices": []})
                return

            if self.path == "/invalid-sse":
                events = [b"data: {broken\n\n"]
            elif self.path == "/broken-stream":
                events = [
                    b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
                ]
            elif self.path == "/eof-done":
                events = [
                    b'data: {"choices":[{"delta":{"content":"complete"},"finish_reason":"stop"}]}\n\n',
                    b"data: [DONE]\n",
                ]
            elif self.path == "/reasoning-first":
                events = [
                    b'data: {"choices":[{"delta":{"reasoning_content":"thought"}}]}\n\n',
                    b'data: {"choices":[{"delta":{"content":"answer"},"finish_reason":"stop"}]}\n\n',
                    b"data: [DONE]\n\n",
                ]
            elif self.path == "/done-without-finish":
                events = [
                    b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n',
                    b"data: [DONE]\n\n",
                ]
            elif self.path == "/responses-incomplete-completed":
                events = [
                    b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"partial"}\n\n',
                    b'event: response.completed\ndata: {"type":"response.completed","response":{"model":"Opus 5","status":"incomplete","usage":{"input_tokens":6,"output_tokens":1,"total_tokens":7}}}\n\n',
                ]
            elif self.path == "/v1/responses-effective-stream":
                events = [
                    b'event: response.created\ndata: {"type":"response.created","response":{"model":"claude-opus-5","status":"in_progress","temperature":1,"top_p":1,"reasoning":null,"tools":[]}}\n\n',
                    b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"effective answer"}\n\n',
                    b'event: response.completed\ndata: {"type":"response.completed","response":{"model":"claude-opus-5","status":"completed","temperature":1,"top_p":1,"reasoning":null,"tools":[],"usage":{"input_tokens":4,"output_tokens":2,"total_tokens":6}}}\n\n',
                ]
            elif self.path == "/v1/responses":
                events = [
                    b'event: response.created\ndata: {"type":"response.created","response":{"status":"in_progress"}}\n\n',
                    b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"hello"}\n\n',
                    b'event: response.completed\ndata: {"type":"response.completed","response":{"model":"Opus 5","status":"completed","usage":{"input_tokens":6,"output_tokens":1,"total_tokens":7}}}\n\n',
                ]
            else:
                events = [
                    b'data: {"choices":[{"delta":{"content":"\xe4\xbd\xa0"}}]}\n\n',
                    b'data: {"choices":[{"delta":{"content":"\xe5\xa5\xbd"},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":2}}\n\n',
                    b"data: [DONE]\n\n",
                ]

            body_length = sum(len(event) for event in events)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(body_length))
            self.send_header("X-Request-Id", "fake-request")
            self.end_headers()
            for event in events:
                midpoint = max(1, len(event) // 2)
                self.wfile.write(event[:midpoint])
                self.wfile.flush()
                time.sleep(0.01)
                self.wfile.write(event[midpoint:])
                self.wfile.flush()
                time.sleep(0.01)

        def _send_json(self, status, value):
            body = json.dumps(value).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
