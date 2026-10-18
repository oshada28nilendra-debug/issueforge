import json
import tempfile
import unittest
from pathlib import Path

from issueforge.engine import investigate
from issueforge.policy import Snapshot

CANDIDATE = "import unittest\nclass TestBug(unittest.TestCase):\n def test_bug(self):\n  self.assertEqual(1, 2)\n"
PASS = {"kind": "pass", "tests": 1, "log": "OK"}
FAIL = {"kind": "assertion_failure", "tests": 1, "signature": "same", "log": "AssertionError"}


class RecordedSandbox:
    """Simulates execution outcomes. Never presented as real Docker execution."""

    def __init__(self, values):
        self.values = iter(values)

    def preflight(self):
        return {"kind": "ready"}

    def run(self, *args):
        return next(self.values)


class ScriptedProvider:
    mode = "test_double"
    usage = {}

    def __init__(self, actions):
        self.actions = iter(actions)
        self.calls = 0

    def complete(self, messages):
        self.calls += 1
        return next(self.actions)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        repo = self.root / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("x = 1")
        self.snapshot = Snapshot.capture(repo)
        self.out = self.root / "evidence"

    def test_candidate_exports_evidence_and_stable_verdict(self):
        result = investigate(
            self.snapshot, "x is wrong", RecordedSandbox([PASS, FAIL, FAIL]), self.out, candidate=CANDIDATE
        )
        self.assertEqual(result["status"], "reproduced")
        self.assertEqual(result["model_mode"], "supplied_candidate")
        self.assertFalse(result["live_model_verified"])
        self.assertEqual(json.loads((self.out / "report.json").read_text())["status"], "reproduced")
        self.assertTrue((self.out / "test_reproduction.py").exists())
        self.assertEqual(result["source_digest"], self.snapshot.digest)

    def test_tool_loop_can_read_then_propose(self):
        provider = ScriptedProvider(
            [
                {"action": "read", "path": "app.py"},
                {"action": "propose", "hypothesis": "wrong output", "test_code": CANDIDATE},
            ]
        )
        result = investigate(self.snapshot, "x wrong", RecordedSandbox([PASS, FAIL, FAIL]), self.out, provider=provider)
        self.assertEqual(result["status"], "reproduced")
        self.assertEqual(result["model_mode"], "test_double")
        self.assertEqual(len(result["events"]), 2)
        self.assertFalse(result["live_model_verified"])

    def test_missing_sandbox_avoids_model_and_returns_blocker(self):
        class Blocked(RecordedSandbox):
            def preflight(self):
                return {"kind": "blocked", "reason": "Docker unavailable", "tests": 0}

        result = investigate(self.snapshot, "bug", Blocked([]), self.out, candidate=CANDIDATE)
        self.assertEqual(result["status"], "could_not_investigate")
        self.assertIn("Docker", result["blocker"])
        self.assertTrue((self.out / "report.md").exists())

    def test_failing_baseline_stops_investigation(self):
        result = investigate(self.snapshot, "bug", RecordedSandbox([FAIL]), self.out, candidate=CANDIDATE)
        self.assertEqual(result["status"], "could_not_investigate")
        self.assertEqual(result["proposals"], [])

    def test_output_is_never_overwritten(self):
        self.out.mkdir()
        (self.out / "valuable.txt").write_text("keep")
        with self.assertRaises(FileExistsError):
            investigate(self.snapshot, "bug", RecordedSandbox([PASS]), self.out, candidate=CANDIDATE)
        self.assertEqual((self.out / "valuable.txt").read_text(), "keep")

    def test_no_result_when_agent_stops_without_proposal(self):
        provider = ScriptedProvider([{"action": "stop", "reason": "insufficient details"}])
        result = investigate(self.snapshot, "bug", RecordedSandbox([PASS]), self.out, provider=provider)
        self.assertEqual(result["status"], "could_not_investigate")
        self.assertIn("insufficient", result["blocker"])

    def test_agent_cannot_read_outside_snapshot(self):
        provider = ScriptedProvider(
            [{"action": "read", "path": "/etc/passwd"}, {"action": "stop", "reason": "no evidence"}]
        )
        result = investigate(self.snapshot, "bug", RecordedSandbox([PASS]), self.out, provider=provider)
        self.assertIn("error", result["events"][0]["observation"])
        self.assertNotIn("root:", json.dumps(result))

    def test_control_failure_prevents_reproduced_verdict(self):
        result = investigate(
            self.snapshot,
            "bug",
            RecordedSandbox([PASS, FAIL, FAIL, FAIL]),
            self.out,
            candidate=CANDIDATE,
            control=self.snapshot,
        )
        self.assertEqual(result["status"], "could_not_investigate")
        self.assertFalse(result["control_verified"])
