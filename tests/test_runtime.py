import json
import unittest
from pathlib import Path
from unittest.mock import patch

from issueforge.sandbox import DockerSandbox, SandboxConfig, decode_result
from issueforge.provider import ModelError, CompatibleProvider


class SandboxTests(unittest.TestCase):
    def test_flags_disable_network_and_host_privileges(self):
        sandbox = DockerSandbox()
        cmd = sandbox.command(Path("/tmp/repo"), Path("/tmp/case"), "trial", "abc123")
        for flag in [
            "--read-only",
            "--cap-drop=ALL",
            "--network=none",
            "--pull=never",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--memory=256m",
            "--user=65534:65534",
        ]:
            self.assertIn(flag, cmd)
        self.assertFalse(any("docker.sock" in x for x in cmd))
        self.assertEqual(cmd[-1], "trial")

    def test_missing_docker_returns_blocked_not_host_fallback(self):
        with patch("issueforge.sandbox.shutil.which", return_value=None):
            check = DockerSandbox().preflight()
        self.assertEqual(check["kind"], "blocked")
        self.assertIn("Docker", check["reason"])

    def test_decode_requires_valid_telemetry(self):
        self.assertEqual(decode_result("junk", 0)["kind"], "error")
        self.assertEqual(decode_result("ISSUEFORGE_RESULT={}\n", 0)["kind"], "error")
        record = {"tests": 1, "failures": ["test_x"], "errors": [], "skipped": 0, "trace": "AssertionError: bad"}
        outcome = decode_result("ISSUEFORGE_RESULT=" + json.dumps(record), 1)
        self.assertEqual(outcome["kind"], "assertion_failure")
        self.assertEqual(len(outcome["signature"]), 64)

    def test_errors_outrank_failures(self):
        record = {"tests": 2, "failures": ["a"], "errors": ["b"], "skipped": 0, "trace": "ImportError"}
        self.assertEqual(decode_result("ISSUEFORGE_RESULT=" + json.dumps(record), 1)["kind"], "error")

    def test_image_cannot_inject_cli_arguments(self):
        with self.assertRaises(ValueError):
            DockerSandbox(SandboxConfig(image="--privileged"))


class ProviderTests(unittest.TestCase):
    def test_external_endpoint_requires_explicit_consent(self):
        with self.assertRaises(ModelError):
            CompatibleProvider("https://example.com/v1", "model")

    def test_http_only_permitted_on_loopback(self):
        with self.assertRaises(ModelError):
            CompatibleProvider("http://example.com/v1", "model", allow_remote=True)
        CompatibleProvider("http://127.0.0.1:11434/v1", "model")

    def test_model_required_and_budget_bounded(self):
        with self.assertRaises(ModelError):
            CompatibleProvider("http://localhost:11434/v1", "")
        provider = CompatibleProvider("http://localhost:11434/v1", "test", max_calls=1)
        provider.calls = 1
        with self.assertRaisesRegex(ModelError, "budget"):
            provider.complete([])

    def test_parser_rejects_non_object_and_accepts_fenced_json(self):
        from issueforge.provider import parse_action

        self.assertEqual(parse_action('```json\n{"action":"stop","reason":"done"}\n```')["action"], "stop")
        for value in ["[]", "garbage", '{"action": "shell"}', '{"action":"read", "path": 3}']:
            with self.subTest(value=value), self.assertRaises(ModelError):
                parse_action(value)


class MalformedInputTests(unittest.TestCase):
    def test_action_content_must_be_text(self):
        from issueforge.provider import parse_action

        for content in [None, 3, {}, []]:
            with self.subTest(content=content), self.assertRaises(ModelError):
                parse_action(content)

    def test_inconsistent_failure_exit_code_is_not_evidence(self):
        record = {"tests": 1, "failures": ["test_x"], "errors": [], "skipped": 0, "trace": "bad"}
        self.assertEqual(decode_result("ISSUEFORGE_RESULT=" + json.dumps(record), 0)["kind"], "error")
