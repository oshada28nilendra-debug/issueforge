import hashlib
import unittest

from scripts.verify_live_evidence import verify


class LiveEvidenceTests(unittest.TestCase):
    def report(self):
        return {
            "status": "reproduced",
            "model_mode": "live_model",
            "live_model_verified": True,
            "sandbox_verified": True,
            "control_verified": True,
            "model_calls": 1,
            "model_usage": {"completion_tokens": 100},
            "baseline": {"kind": "pass"},
            "proposals": [
                {
                    "status": "reproduced",
                    "test_sha256": hashlib.sha256(b"test code").hexdigest(),
                    "attempts": [{"kind": "assertion_failure", "tests": 1, "signature": "same"}] * 2,
                    "control": {"kind": "pass", "tests": 1},
                }
            ],
        }

    def test_accepts_actual_evidence_shape(self):
        self.assertEqual(verify(self.report(), "test code")["status"], "passed")

    def test_rejects_supplied_candidate_even_when_it_fails(self):
        report = self.report()
        report["model_mode"] = "supplied_candidate"
        with self.assertRaises(ValueError):
            verify(report, "test code")

    def test_rejects_missing_tokens_and_failed_control(self):
        for mutation in ["tokens", "control"]:
            report = self.report()
            if mutation == "tokens":
                report["model_usage"]["completion_tokens"] = 0
            else:
                report["proposals"][0]["control"]["kind"] = "assertion_failure"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify(report, "test code")

    def test_rejects_changed_artifact(self):
        with self.assertRaises(ValueError):
            verify(self.report(), "different code")

    def test_rejects_skipped_or_different_failure_trials(self):
        for mutation in ["signature", "kind"]:
            report = self.report()
            report["proposals"][0]["attempts"] = [
                {"kind": "assertion_failure", "tests": 1, "signature": "same"},
                {"kind": "assertion_failure", "tests": 1, "signature": "same"},
            ]
            report["proposals"][0]["attempts"][1][mutation] = "different"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify(report, "test code")
