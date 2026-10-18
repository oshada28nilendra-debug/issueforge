"""HTTP contract tests use a local simulated server, NOT a real language model."""

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from issueforge.provider import CompatibleProvider, ModelError


class Handler(BaseHTTPRequestHandler):
    received = []
    reply = None
    code = 200

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.__class__.received.append((self.path, data))
        self.send_response(self.__class__.code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self.__class__.reply).encode())

    def log_message(self, *args):
        pass


class TransportTests(unittest.TestCase):
    def setUp(self):
        Handler.received = []
        Handler.code = 200
        Handler.reply = {
            "choices": [{"message": {"content": json.dumps({"action": "stop", "reason": "done"})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.provider = CompatibleProvider(f"http://127.0.0.1:{self.server.server_port}/v1", "simulated")
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_real_http_serialization_and_usage(self):
        result = self.provider.complete([{"role": "user", "content": "test"}])
        self.assertEqual(result["action"], "stop")
        self.assertEqual(Handler.received[0][0], "/v1/chat/completions")
        self.assertEqual(Handler.received[0][1]["model"], "simulated")
        self.assertEqual(self.provider.usage["prompt_tokens"], 10)
        self.assertEqual(self.provider.calls, 1)

    def test_http_errors_are_sanitized(self):
        Handler.code = 401
        Handler.reply = {"secret": "not-for-report"}
        with self.assertRaisesRegex(ModelError, "401") as result:
            self.provider.complete([])
        self.assertNotIn("not-for-report", str(result.exception))

    def test_malformed_envelope(self):
        Handler.reply = {"choices": []}
        with self.assertRaisesRegex(ModelError, "Malformed"):
            self.provider.complete([])

    def test_malformed_usage_does_not_crash(self):
        Handler.reply["usage"] = ["unexpected"]
        with self.assertRaises(ModelError):
            self.provider.complete([])

    def test_null_message_content_is_reported(self):
        Handler.reply["choices"][0]["message"]["content"] = None
        with self.assertRaises(ModelError):
            self.provider.complete([])
