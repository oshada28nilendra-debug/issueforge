# Security boundaries and limitations

IssueForge treats repository files, issue text, model output and logs as untrusted.
Never run `issueforge/harness.py` directly against someone else's repository on the
host. The execution path uses Docker only and refuses a missing/unready backend.

Containers receive a temporary, filtered source snapshot and candidate test through
read-only mounts. No host Docker socket, home directory, credentials, network or
original repository is mounted. Processes run as UID/GID 65534 with capabilities
dropped, privilege escalation disabled, a read-only root filesystem, bounded tmpfs,
CPU/memory/PID/file limits and a per-run timeout. Output is capped and cleanup is
attempted after every run, including timeout. Failed cleanup makes the result
inconclusive; check `docker ps -a --filter name=issueforge-` and remove leftover
containers yourself if the daemon was unavailable.

These settings reduce exposure; they do not guarantee isolation from hostile code.
Docker shares the host kernel. Use a dedicated disposable VM for genuinely hostile
repositories; do not expose this CLI as a public execution service. Remote Docker
daemons are not supported: bind mount paths must exist on the Docker host.

Snapshot capture rejects final-component symlinks and excludes symlinked directories,
hidden/config/secret-named files and unsupported formats. It assumes no adversary is
concurrently modifying parent directories on the host. Do not ingest repositories
from a concurrently hostile shared filesystem. Byte budgets and allowed suffixes
are not a complete defense against hidden secrets or harmful content.

Redaction is best effort. Keys embedded in unusual source forms can be missed.
Before transmitting source, inspect all included files and confirm you are permitted
to send them to the chosen provider. `--allow-remote` permits HTTPS source transfer
and possible provider costs. No provider credentials are passed to a container.
HTTP redirects are disabled; provider response bodies are omitted from errors.
A local proxy might itself use a paid remote backend: check its configuration.

The AST validator checks test shape only. It cannot prove that a test is safe,
meaningful or related to the issue. In-process unittest records are not tamper-proof
against the tested code. A repository can monkeypatch modules or fabricate stdout.
Treat the report as debugging evidence requiring human review, not an attestation.

Reports can contain sensitive paths, business logic, failure data or untrusted text.
Review before sharing or rendering. No telemetry or automatic external uploads are
implemented in this package. No complete-security or compliance claim is made.

To report a vulnerability, privately contact the repository owner using an available
private channel. Do not post credentials or exploit details in a public issue.
