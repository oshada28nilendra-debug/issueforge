import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def invoke(self, *args, env=None):
        return subprocess.run(
            [sys.executable, "-m", "issueforge", *map(str, args)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_inspect_manifest_is_real_and_secret_free(self):
        result = self.invoke("inspect", "--repo", ROOT / "examples/buggy")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(result.stdout)
        self.assertIn("prices.py", manifest["files"])
        self.assertEqual(len(manifest["source_digest"]), 64)

    def test_cli_missing_docker_creates_honest_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "evidence"
            env = {**os.environ, "PATH": ""}
            result = self.invoke(
                "run",
                "--repo",
                ROOT / "examples/buggy",
                "--issue",
                ROOT / "examples/issue.md",
                "--candidate",
                ROOT / "examples/test_reproduction.py",
                "--out",
                output,
                env=env,
            )
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["status"], "could_not_investigate")
            self.assertFalse(report["live_model_verified"])
            self.assertFalse(report["sandbox_verified"])

    def test_output_inside_repository_is_rejected(self):
        result = self.invoke(
            "run",
            "--repo",
            ROOT / "examples/buggy",
            "--issue",
            ROOT / "examples/issue.md",
            "--candidate",
            ROOT / "examples/test_reproduction.py",
            "--out",
            ROOT / "examples/buggy/evidence",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside", result.stderr)

    def test_cli_does_not_execute_repository_on_inspect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "danger.py").write_text('raise RuntimeError("must not execute")')
            result = self.invoke("inspect", "--repo", root)
            self.assertEqual(result.returncode, 0)
            self.assertIn("danger.py", result.stdout)
