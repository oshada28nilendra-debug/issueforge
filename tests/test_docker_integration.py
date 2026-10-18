"""Real container tests: explicit opt-in, no model calls, trusted authored fixtures."""

import os
import tempfile
import unittest
from pathlib import Path

from issueforge.engine import investigate
from issueforge.policy import Snapshot
from issueforge.sandbox import DockerSandbox

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    os.environ.get("ISSUEFORGE_DOCKER_TESTS") == "1",
    "Docker integration disabled; set ISSUEFORGE_DOCKER_TESTS=1 with a cached image",
)
class DockerIntegrationTests(unittest.TestCase):
    def test_known_bug_fails_twice_and_fixed_control_passes(self):
        sandbox = DockerSandbox()
        self.assertEqual(sandbox.preflight()["kind"], "ready")
        with tempfile.TemporaryDirectory() as temp:
            report = investigate(
                Snapshot.capture(ROOT / "examples/buggy"),
                (ROOT / "examples/issue.md").read_text(),
                sandbox,
                Path(temp) / "evidence",
                candidate=(ROOT / "examples/test_reproduction.py").read_text(),
                control=Snapshot.capture(ROOT / "examples/fixed"),
            )
            self.assertEqual(report["status"], "reproduced", report)
            self.assertTrue(report["control_verified"])
            self.assertTrue(report["sandbox_verified"])
            self.assertFalse(report["live_model_verified"])

    def test_fixed_repository_does_not_reproduce(self):
        with tempfile.TemporaryDirectory() as temp:
            report = investigate(
                Snapshot.capture(ROOT / "examples/fixed"),
                (ROOT / "examples/issue.md").read_text(),
                DockerSandbox(),
                Path(temp) / "evidence",
                candidate=(ROOT / "examples/test_reproduction.py").read_text(),
            )
            self.assertEqual(report["status"], "not_reproduced", report)

    def test_container_is_unprivileged_networkless_and_readonly(self):
        code = """import os, socket, unittest
class TestBoundaries(unittest.TestCase):
 def test_nonroot(self):
  self.assertNotEqual(os.getuid(), 0)
 def test_repo_readonly(self):
  with self.assertRaises(OSError):
   open('/repo/forbidden.txt', 'w')
 def test_network(self):
  with self.assertRaises(OSError):
   socket.create_connection(('1.1.1.1', 443), timeout=1)
"""
        with tempfile.TemporaryDirectory() as temp:
            report = investigate(
                Snapshot.capture(ROOT / "examples/fixed"),
                "boundary checks",
                DockerSandbox(),
                Path(temp) / "evidence",
                candidate=code,
            )
            self.assertEqual(report["status"], "not_reproduced", report)
            self.assertEqual(report["proposals"][0]["attempts"][0]["tests"], 3)
