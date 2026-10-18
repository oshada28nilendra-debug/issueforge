"""Bounded, source-only snapshots. Reading never imports repository code."""

import ast
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


class PolicyError(ValueError):
    """An input violates a declared boundary."""


ALLOWED_SUFFIXES = {".py", ".md", ".toml", ".txt", ".cfg", ".ini"}
EXCLUDED_DIRS = {"node_modules", "__pycache__", "venv", "env", "build", "dist"}
SENSITIVE = re.compile(r"(^\.|secret|credential|password|^id_rsa|^id_ed25519)", re.I)


def redact(text: str) -> str:
    """Best effort only: users must review sources before sending them to a model."""
    text = re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", "[REDACTED PRIVATE KEY]", text, flags=re.S
    )
    text = re.sub(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})\b", "[REDACTED]", text)


@dataclass(frozen=True)
class Snapshot:
    files: Mapping[str, str]
    digest: str

    @classmethod
    def capture(cls, root: Path, max_bytes: int = 2_000_000, max_files: int = 500):
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise PolicyError("Repository must be a local directory")
        files = {}
        total = 0
        for folder, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = sorted(
                d
                for d in dirs
                if not d.startswith(".") and d not in EXCLUDED_DIRS and not (Path(folder) / d).is_symlink()
            )
            for name in sorted(names):
                path = Path(folder) / name
                if SENSITIVE.search(name) or path.suffix not in ALLOWED_SUFFIXES or path.is_symlink():
                    continue
                # O_NOFOLLOW + fstat prevent a final-component symlink race.
                try:
                    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
                    with os.fdopen(fd, "rb") as stream:
                        import stat

                        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                            continue
                        data = stream.read(min(max_bytes + 1, 256_001))
                except OSError as exc:
                    raise PolicyError("A source file could not be read safely") from exc
                total += len(data)
                if total > max_bytes or len(files) >= max_files or len(data) > 256_000:
                    raise PolicyError("Repository exceeds source snapshot budget; provide a smaller checkout")
                try:
                    files[path.relative_to(root).as_posix()] = data.decode("utf-8")
                except UnicodeDecodeError:
                    continue
        if not files:
            raise PolicyError("No supported source files in repository")
        digest = hashlib.sha256()
        for name, content in sorted(files.items()):
            digest.update(name.encode() + b"\0" + content.encode() + b"\0")
        return cls(MappingProxyType(files), digest.hexdigest())

    def read(self, name: str) -> str:
        if name not in self.files:
            raise PolicyError("Path must name an included snapshot file")
        return self.files[name]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        if not isinstance(query, str) or not 1 <= len(query) <= 100:
            raise PolicyError("Search query must contain 1–100 characters")
        hits = []
        for name, content in self.files.items():
            for number, line in enumerate(content.splitlines(), 1):
                if query.casefold() in line.casefold():
                    hits.append({"path": name, "line": number, "text": redact(line[:240])})
                    if len(hits) >= limit:
                        return hits
        return hits

    def context(self, issue: str, limit: int = 24_000) -> str:
        tokens = set(re.findall(r"\w{3,}", issue.casefold()))
        ranked = sorted(
            self.files,
            key=lambda name: (-sum(t in (name + "\n" + self.files[name][:4000]).casefold() for t in tokens), name),
        )
        pieces = []
        remaining = limit
        for name in ranked:
            part = f"\nFILE {name}\n{redact(self.files[name])}\n"
            if remaining <= 0:
                break
            pieces.append(part[:remaining])
            remaining -= len(part)
        return "".join(pieces)

    def write(self, destination: Path):
        destination.mkdir(parents=True, exist_ok=True)
        for name, content in self.files.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def validate_candidate(code: str):
    if not isinstance(code, str) or not 1 <= len(code) <= 30_000:
        raise PolicyError("Candidate must be Python code of at most 30,000 characters")
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        raise PolicyError("Candidate is invalid Python") from exc
    methods = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
    assertions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assert)
        or (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"))
    ]
    if not methods or not assertions:
        raise PolicyError("Candidate needs unittest test methods and assertions")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Constant) and not node.test.value:
            raise PolicyError("Unconditional assertion failures are not evidence")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fail":
            raise PolicyError("Explicit self.fail is not accepted as reproduction evidence")
    # AST validation is a shape check, NOT a sandbox or proof of relevance.
