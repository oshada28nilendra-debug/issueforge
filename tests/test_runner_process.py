"""Exercise real subprocess supervision using a fake Docker CLI, never target code."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from issueforge.sandbox import DockerSandbox, SandboxConfig


class ProcessSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.marker = self.root / "cleanup"
        program = self.root / "docker"
        program.write_text(
            "#!"
            + sys.executable
            + "\n"
            + """import json, os, sys, time
if sys.argv[1] == 'info':
 print('linux')
elif sys.argv[1] == 'image':
 print('{}')
elif sys.argv[1] == 'rm':
 open(os.environ['FAKE_CLEANUP'], 'w').write('attempted')
 if os.environ.get('FAKE_MODE') == 'cleanup_failure':
  print('daemon unavailable', file=sys.stderr)
  sys.exit(1)
elif sys.argv[1] == 'run':
 mode = os.environ.get('FAKE_MODE')
 if mode == 'timeout':
  time.sleep(5)
 elif mode == 'flood':
  print('x' * 100000, flush=True)
 else:
  print('ISSUEFORGE_RESULT=' + json.dumps({'tests': 1, 'failures': [], 'errors': [], 'skipped': 0, 'trace': 'OK'}))
"""
        )
        program.chmod(0o755)

    def run_mode(self, mode):
        with patch.dict(os.environ, {"PATH": str(self.root), "FAKE_MODE": mode, "FAKE_CLEANUP": str(self.marker)}):
            return DockerSandbox(SandboxConfig(timeout=1, max_output=1024)).run(self.root, self.root)

    def test_valid_record_from_process_is_decoded_and_cleaned(self):
        result = self.run_mode("pass")
        self.assertEqual(result["kind"], "pass")
        self.assertEqual(self.marker.read_text(), "attempted")

    def test_timeout_kills_process_and_attempts_container_cleanup(self):
        result = self.run_mode("timeout")
        self.assertEqual(result["kind"], "timeout")
        self.assertTrue(self.marker.exists())

    def test_output_limit_stops_flood_and_cleans(self):
        result = self.run_mode("flood")
        self.assertEqual(result["kind"], "error")
        self.assertEqual(result["reason"], "output_limit")
        self.assertLessEqual(len(result["log"]), 1024)
        self.assertTrue(self.marker.exists())

    def test_cleanup_failure_is_not_success(self):
        result = self.run_mode("cleanup_failure")
        self.assertEqual(result["kind"], "error")
        self.assertEqual(result["reason"], "cleanup_failed")
