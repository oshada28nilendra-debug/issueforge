"""Docker-only execution. There is deliberately no host-code execution fallback."""

import hashlib
import json
import os
import re
import selectors
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .policy import redact


@dataclass(frozen=True)
class SandboxConfig:
    image: str = "python:3.12-slim"
    timeout: int = 25
    max_output: int = 65_536


def decode_result(output: str, returncode: int) -> dict:
    records = [
        line[len("ISSUEFORGE_RESULT=") :] for line in output.splitlines() if line.startswith("ISSUEFORGE_RESULT=")
    ]
    try:
        if len(records) != 1:
            raise ValueError()
        record = json.loads(records[0])
        if (
            not isinstance(record, dict)
            or type(record.get("tests")) is not int
            or record["tests"] < 0
            or type(record.get("skipped")) is not int
            or not isinstance(record.get("failures"), list)
            or not isinstance(record.get("errors"), list)
            or not isinstance(record.get("trace"), str)
        ):
            raise ValueError()
        if not all(isinstance(x, str) for x in record["failures"] + record["errors"]):
            raise ValueError()
    except (ValueError, TypeError):
        return {
            "kind": "error",
            "reason": "Missing or malformed runner evidence",
            "tests": 0,
            "log": redact(output[-4000:]),
        }
    kind = "pass"
    if record["errors"] or returncode not in (0, 1):
        kind = "error"
    elif record["failures"]:
        kind = "assertion_failure" if returncode == 1 else "error"
    elif record["tests"] == 0 or record["skipped"]:
        kind = "no_tests"
    elif returncode != 0:
        kind = "error"
    normalized = re.sub(r"Ran \d+ tests? in [0-9.]+s", "Ran tests", record["trace"])
    normalized = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", normalized)
    return {
        "kind": kind,
        "tests": record["tests"],
        "failures": record["failures"],
        "errors": record["errors"],
        "skipped": record["skipped"],
        "signature": hashlib.sha256(normalized.encode()).hexdigest(),
        "log": redact(record["trace"]),
        "returncode": returncode,
    }


class DockerSandbox:
    backend = "docker"

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:@-]{0,240}", self.config.image)
            or not 1 <= self.config.timeout <= 120
            or not 1024 <= self.config.max_output <= 1_000_000
        ):
            raise ValueError("Invalid sandbox image or resource limits")

    def preflight(self) -> dict:
        if not shutil.which("docker"):
            return {"kind": "blocked", "reason": "Docker CLI is unavailable; no host fallback exists", "tests": 0}
        for args, reason in [
            (["info", "--format", "{{.OSType}}"], "Docker daemon unavailable"),
            (["image", "inspect", self.config.image], "Sandbox image not cached; build/pull it explicitly"),
        ]:
            try:
                result = subprocess.run(["docker", *args], capture_output=True, timeout=8, check=False)
            except (OSError, subprocess.TimeoutExpired):
                return {"kind": "blocked", "reason": reason, "tests": 0}
            if result.returncode != 0:
                return {"kind": "blocked", "reason": reason, "tests": 0}
            if args[0] == "info" and result.stdout.strip() != b"linux":
                return {"kind": "blocked", "reason": "Linux containers required", "tests": 0}
        return {"kind": "ready"}

    def command(self, repo: Path, case: Path, mode: str, name: str) -> list[str]:
        if mode not in {"baseline", "trial"}:
            raise ValueError("Unknown sandbox mode")
        paths = [repo.resolve(), case.resolve(), Path(__file__).with_name("harness.py").resolve()]
        if any("," in str(p) or "\n" in str(p) for p in paths):
            raise ValueError("Unsupported mount path")
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--memory=256m",
            "--memory-swap=256m",
            "--cpus=1",
            "--ulimit",
            "nofile=128:128",
            "--user=65534:65534",
            "--log-driver=none",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=32m,mode=1777",
            "--mount",
            f"type=bind,src={paths[0]},dst=/repo,readonly",
            "--mount",
            f"type=bind,src={paths[1]},dst=/case,readonly",
            "--mount",
            f"type=bind,src={paths[2]},dst=/opt/issueforge/harness.py,readonly",
            "--workdir",
            "/tmp",
            "--env",
            "HOME=/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--entrypoint",
            "python",
            self.config.image,
            "-I",
            "-B",
            "/opt/issueforge/harness.py",
            mode,
        ]

    def run(self, repo: Path, case: Path, mode: str = "trial") -> dict:
        preflight = self.preflight()
        if preflight["kind"] != "ready":
            return preflight
        name = "issueforge-" + uuid.uuid4().hex
        command = self.command(repo, case, mode, name)
        start = time.monotonic()
        output = bytearray()
        reason = None
        process = None
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
            )
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() - start > self.config.timeout:
                        reason = "timeout"
                        break
                    for key, _ in selector.select(timeout=0.1):
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        output.extend(chunk)
                        if len(output) > self.config.max_output:
                            reason = "output_limit"
                            break
                    if reason:
                        break
            if reason:
                process.kill()
            code = process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            reason = "runner_failure"
            code = -1
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=3)
                process.stdout.close()
            # Killing the Docker client alone does not necessarily stop its container.
            try:
                cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=8, check=False)
                if cleanup.returncode != 0 and b"No such container" not in cleanup.stderr:
                    reason = "cleanup_failed"
            except (OSError, subprocess.TimeoutExpired):
                reason = "cleanup_failed"
        if reason:
            return {
                "kind": "timeout" if reason == "timeout" else "error",
                "reason": reason,
                "tests": 0,
                "log": redact(output[: self.config.max_output].decode(errors="replace")),
            }
        result = decode_result(output.decode(errors="replace"), code)
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        return result
