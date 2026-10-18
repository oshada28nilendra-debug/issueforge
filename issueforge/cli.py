"""CLI and explicit consent boundaries."""

import argparse
import json
import os
import sys
from pathlib import Path

from .engine import investigate
from .policy import PolicyError, Snapshot
from .provider import CompatibleProvider, ModelError
from .sandbox import DockerSandbox, SandboxConfig


def read_input(path: Path, max_bytes: int) -> str:
    with path.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise PolicyError("Input exceeds size budget")
    return data.decode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="issueforge", description="Evidence-first Python bug reproduction")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Review filtered source manifest; executes no repository code")
    inspect.add_argument("--repo", required=True, type=Path)
    doctor = commands.add_parser("doctor", help="Check Docker and cached image; never pulls an image")
    doctor.add_argument("--image", default="python:3.12-slim")
    run = commands.add_parser("run", help="Investigate in restricted Docker containers")
    run.add_argument("--repo", required=True, type=Path)
    run.add_argument("--issue", required=True, type=Path)
    run.add_argument("--out", required=True, type=Path, help="New evidence directory outside repository")
    mode = run.add_mutually_exclusive_group(required=True)
    mode.add_argument("--candidate", type=Path, help="Existing unittest source; no AI call")
    mode.add_argument("--model", help="Model identifier available at endpoint")
    run.add_argument("--endpoint", default=os.environ.get("ISSUEFORGE_BASE_URL", "http://localhost:11434/v1"))
    run.add_argument(
        "--allow-remote",
        action="store_true",
        help="Consent to sending filtered sources to a remote provider and its possible API charges",
    )
    run.add_argument("--control-repo", type=Path, help="Optional known-fixed checkout; the same test must pass")
    run.add_argument("--image", default="python:3.12-slim", help="Trusted prebuilt image; never pulled automatically")
    run.add_argument("--timeout", type=int, default=25, help="Seconds per container, 1–120")
    run.add_argument("--max-steps", type=int, default=6, help="Maximum model calls, 1–12")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            snap = Snapshot.capture(args.repo)
            print(
                json.dumps(
                    {
                        "source_digest": snap.digest,
                        "files": sorted(snap.files),
                        "bytes": sum(len(v.encode()) for v in snap.files.values()),
                        "notice": "Only included text files are sent/executed; review them before using a model.",
                    },
                    indent=2,
                )
            )
            return 0
        sandbox = DockerSandbox(SandboxConfig(image=args.image, timeout=getattr(args, "timeout", 25)))
        if args.command == "doctor":
            result = sandbox.preflight()
            print(json.dumps(result, indent=2))
            return 0 if result["kind"] == "ready" else 3
        repo = args.repo.resolve(strict=True)
        out = args.out.resolve()
        controls = [repo]
        if args.control_repo:
            controls.append(args.control_repo.resolve(strict=True))
        if any(out == source or out.is_relative_to(source) for source in controls):
            raise PolicyError("Evidence output must be outside the repository and control checkout")
        snap = Snapshot.capture(repo)
        control = Snapshot.capture(args.control_repo) if args.control_repo else None
        issue = read_input(args.issue, 12_000)
        candidate = read_input(args.candidate, 30_000) if args.candidate else None
        provider = None
        if args.model:
            provider = CompatibleProvider(
                args.endpoint,
                args.model,
                os.environ.get("ISSUEFORGE_API_KEY", ""),
                allow_remote=args.allow_remote,
                max_calls=args.max_steps,
            )
        report = investigate(
            snap, issue, sandbox, out, candidate=candidate, provider=provider, control=control, max_steps=args.max_steps
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "report": str(out / "report.json"),
                    "live_model_verified": report["live_model_verified"],
                    "sandbox_verified": report["sandbox_verified"],
                    "blocker": report.get("blocker"),
                },
                indent=2,
            )
        )
        return {"reproduced": 0, "not_reproduced": 1, "could_not_investigate": 3}[report["status"]]
    except (PolicyError, ModelError, OSError, UnicodeError, ValueError) as exc:
        # File errors may contain local paths but no provider response bodies or credentials.
        print(f"issueforge: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
