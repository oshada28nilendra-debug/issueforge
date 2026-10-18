"""Validate a live-model CI report; this is a gate, not a relevance oracle."""

import argparse
import hashlib
import json
from pathlib import Path


def verify(report: dict, candidate: str) -> dict:
    required = {
        "status": "reproduced",
        "model_mode": "live_model",
        "live_model_verified": True,
        "sandbox_verified": True,
        "control_verified": True,
    }
    for field, expected in required.items():
        if report.get(field) != expected:
            raise ValueError(f"Live verification requires {field}={expected!r}")
    if report.get("model_calls", 0) < 1 or report.get("model_usage", {}).get("completion_tokens", 0) < 1:
        raise ValueError("A successful inference must record model calls and generated tokens")
    if report.get("baseline", {}).get("kind") != "pass":
        raise ValueError("Fixture baseline must pass")
    proposals = [p for p in report.get("proposals", []) if p.get("status") == "reproduced"]
    if not proposals:
        raise ValueError("No reproduced proposal")
    final = proposals[-1]
    trials = final.get("attempts", [])
    if len(trials) != 2 or any(t.get("kind") != "assertion_failure" or t.get("tests", 0) < 1 for t in trials):
        raise ValueError("Both trials must execute tests and fail assertions")
    if not trials[0].get("signature") or trials[0]["signature"] != trials[1].get("signature"):
        raise ValueError("Assertion-failure signatures must match")
    control = final.get("control") or {}
    if control.get("kind") != "pass" or control.get("tests", 0) < 1:
        raise ValueError("The generated test must execute and pass on the fixed control")
    digest = hashlib.sha256(candidate.encode()).hexdigest()
    if digest != final.get("test_sha256"):
        raise ValueError("Exported test does not match execution evidence")
    return {
        "status": "passed",
        "model_calls": report["model_calls"],
        "model_usage": report["model_usage"],
        "test_sha256": digest,
        "limit": "Fixture smoke test only; human review must confirm relevance.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        report = json.loads((args.directory / "report.json").read_text())
        candidate = (args.directory / "test_reproduction.py").read_text()
        result = verify(report, candidate)
    except (OSError, ValueError, TypeError) as exc:
        result = {"status": "failed", "reason": str(exc)}
    args.directory.mkdir(parents=True, exist_ok=True)
    (args.directory / "live-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
