"""Container-only unittest harness; never invoke on untrusted sources on the host."""

import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest


def main():
    sys.path[:0] = ["/repo", "/repo/src"]
    stream = io.StringIO()
    try:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            if sys.argv[1] == "baseline":
                if os.path.isdir("/repo/tests"):
                    suite = unittest.defaultTestLoader.discover("/repo/tests")
                else:
                    suite = unittest.TestSuite()
            else:
                spec = importlib.util.spec_from_file_location("issueforge_candidate", "/case/test_reproduction.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                suite = unittest.defaultTestLoader.loadTestsFromModule(module)
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        record = {
            "tests": result.testsRun,
            "failures": [t.id() for t, _ in result.failures],
            "errors": [t.id() for t, _ in result.errors],
            "skipped": len(result.skipped),
            "trace": stream.getvalue()[-24_000:],
        }
    except BaseException as exc:
        # Imports, loader failures and SystemExit cannot masquerade as failed assertions.
        record = {"tests": 0, "failures": [], "errors": [type(exc).__name__], "skipped": 0, "trace": str(exc)[:2000]}
    print("ISSUEFORGE_RESULT=" + json.dumps(record))
    return 1 if record["failures"] or record["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
