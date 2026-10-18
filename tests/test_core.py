import tempfile
import unittest
from pathlib import Path

from issueforge.evidence import classify
from issueforge.policy import PolicyError, Snapshot, validate_candidate


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_ignores_secrets_and_symlinks_and_preserves_safe_source(self):
        (self.root / "app.py").write_text("def add(a, b): return a + b\n")
        (self.root / ".env").write_text("PASSWORD=secret")
        (self.root / "secret.py").symlink_to("/etc/passwd")
        (self.root / "id_rsa").write_text("private")
        snap = Snapshot.capture(self.root)
        self.assertEqual(set(snap.files), {"app.py"})
        self.assertIn("app.py", snap.context("add", 2000))
        self.assertEqual(len(snap.digest), 64)

    def test_path_traversal_rejected(self):
        (self.root / "app.py").write_text("x = 1")
        snap = Snapshot.capture(self.root)
        for name in ["../app.py", "/etc/passwd", ".env", "unknown.py"]:
            with self.subTest(name=name), self.assertRaises(PolicyError):
                snap.read(name)

    def test_snapshot_is_immutable_and_reproducible(self):
        source = self.root / "app.py"
        source.write_text("x = 1")
        snap = Snapshot.capture(self.root)
        source.write_text("x = 2")
        self.assertEqual(snap.read("app.py"), "x = 1")
        with self.assertRaises(TypeError):
            snap.files["app.py"] = "changed"
        self.assertNotEqual(snap.digest, Snapshot.capture(self.root).digest)

    def test_oversized_repository_rejected(self):
        (self.root / "app.py").write_text("x" * 200)
        with self.assertRaises(PolicyError):
            Snapshot.capture(self.root, max_bytes=100)

    def test_write_only_copies_snapshot(self):
        (self.root / "app.py").write_text("x = 1")
        snap = Snapshot.capture(self.root)
        dest = self.root / "output"
        snap.write(dest)
        self.assertEqual((dest / "app.py").read_text(), "x = 1")

    def test_hidden_folders_and_env_variants_not_sent(self):
        (self.root / ".config").mkdir()
        (self.root / ".config" / "token.py").write_text("secret")
        (self.root / "credentials.json").write_text("secret")
        (self.root / ".env.example").write_text("secret")
        (self.root / "README.md").write_text("hello")
        self.assertEqual(set(Snapshot.capture(self.root).files), {"README.md"})


class CandidateTests(unittest.TestCase):
    def test_accepts_unittest_test(self):
        validate_candidate(
            "import unittest\nclass TestBug(unittest.TestCase):\n def test_bug(self):\n  self.assertEqual(1, 2)\n"
        )

    def test_rejects_invalid_empty_or_unconditional_failure(self):
        for code in [
            "",
            "not valid python !",
            "print(1)",
            "import unittest\nclass T(unittest.TestCase):\n def test_x(self):\n  assert False\n",
        ]:
            with self.subTest(code=code), self.assertRaises(PolicyError):
                validate_candidate(code)


class EvidenceTests(unittest.TestCase):
    def test_reproduced_requires_two_same_assertion_failures(self):
        base = {"kind": "pass", "tests": 1}
        failure = {"kind": "assertion_failure", "tests": 1, "signature": "abc"}
        self.assertEqual(classify(base, [failure, failure]), "reproduced")
        self.assertEqual(classify(base, [failure]), "could_not_investigate")
        self.assertEqual(classify(base, [failure, {**failure, "signature": "different"}]), "could_not_investigate")

    def test_environment_failure_is_not_reproduction(self):
        for kind in ["error", "timeout", "blocked", "no_tests"]:
            self.assertEqual(classify({"kind": "pass"}, [{"kind": kind}] * 2), "could_not_investigate")
        self.assertEqual(classify({"kind": "assertion_failure"}, []), "could_not_investigate")

    def test_passing_candidate_does_not_reproduce(self):
        passed = {"kind": "pass", "tests": 1}
        self.assertEqual(classify(passed, [passed, passed]), "not_reproduced")

    def test_control_must_pass_when_provided(self):
        passed = {"kind": "pass", "tests": 1}
        failed = {"kind": "assertion_failure", "tests": 1, "signature": "abc"}
        self.assertEqual(classify(passed, [failed, failed], passed), "reproduced")
        self.assertEqual(classify(passed, [failed, failed], failed), "could_not_investigate")

    def test_flaky_outcome_is_inconclusive(self):
        passed = {"kind": "pass", "tests": 1}
        failed = {"kind": "assertion_failure", "tests": 1, "signature": "abc"}
        self.assertEqual(classify(passed, [failed, passed]), "could_not_investigate")


class RedactionTests(unittest.TestCase):
    def test_quoted_json_keys_are_redacted_without_breaking_structure(self):
        from issueforge.policy import redact

        secret = "sensitive-" + "fixture-value"
        text = '{"api_key": "' + secret + '", "password": "' + secret + '"}'
        clean = redact(text)
        self.assertNotIn(secret, clean)
        self.assertEqual(__import__("json").loads(clean)["api_key"], "[REDACTED]")

    def test_authorization_headers_are_redacted(self):
        from issueforge.policy import redact

        secret = "sensitive-" + "fixture-value"
        for text in [
            "Authorization: Bearer " + secret,
            "authorization: Basic " + secret,
            '{"Authorization": "Bearer ' + secret + '"}',
        ]:
            with self.subTest(text=text):
                self.assertNotIn(secret, redact(text))

    def test_database_url_credentials_are_redacted(self):
        from issueforge.policy import redact

        secret = "sensitive-" + "fixture-value"
        text = "postgresql://demo:" + secret + "@db.example.invalid/app"
        self.assertNotIn(secret, redact(text))
        self.assertIn("db.example.invalid", redact(text))

    def test_does_not_change_non_secret_test_code(self):
        from issueforge.policy import redact

        code = 'self.assertEqual(total(["0.10", "0.20"]), Decimal("0.30"))'
        self.assertEqual(redact(code), code)
