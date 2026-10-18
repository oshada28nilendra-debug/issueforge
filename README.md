# IssueForge

**Turn a Python bug report into a reviewable reproduction test and an evidence bundle.**

IssueForge is a small AI investigation tool for maintainers triaging Python issues.
An agent can inspect a bounded source snapshot, search it, propose a unittest test,
and revise it using observed execution feedback. Execution happens only in restricted
Docker containers. The original repository is never mounted or edited.

**Release status:** [PR #1](https://github.com/oshada28nilendra-debug/issueforge/pull/1) is open for review. Host checks on Python
3.11/3.12/3.13 and all three real Docker tests [passed in CI](https://github.com/oshada28nilendra-debug/issueforge/actions/runs/39093841366).
Real language-model generation and effectiveness remain unverified.
See [verification](docs/VERIFICATION.md) for the exact checks and blockers.

## Why use it?

A plausible debugging explanation is not a reproduction. IssueForge exports the test,
source fingerprint, baseline outcome, two independent runs, optional fixed-checkout
control, and readable/machine-readable reports. It separates assertion failures from
missing dependencies, runner errors, passing tests, and inconsistent outcomes.

This is a focused triage workflow, not an autonomous repair platform. It does not
claim an advantage over existing coding agents without comparative evaluation.
[Validation and alternatives](docs/VALIDATION.md) explain the product decision.

## Requirements

- Python 3.11+; no Python runtime packages beyond the standard library.
- Linux with Docker Engine, or Windows using WSL2 plus Docker Desktop's Linux engine.
  Run these shell commands inside WSL. Native Windows pipes are not supported.
- A deliberately prepared, trusted image. The default is `python:3.12-slim`.
- For AI generation: a running local OpenAI-compatible model endpoint, or an explicitly
  authorized HTTPS endpoint and its API key. Local models still require enough RAM.

`inspect`, help and host-side tests work without Docker or a model.
Repository/test code is **never** executed on the host as a fallback.

## Quickstart: supplied regression test, no AI calls

From the extracted project directory:

```bash
python -m issueforge inspect --repo examples/buggy
# This is a deliberate dependency download; inspect image provenance before use.
docker pull python:3.12-slim
python -m issueforge doctor
python -m issueforge run \
  --repo examples/buggy \
  --issue examples/issue.md \
  --candidate examples/test_reproduction.py \
  --control-repo examples/fixed \
  --out runs/currency-demo
```

Use a **new** output directory for every run. An existing path is rejected.
On a working Docker setup the authored example is intended to produce two matching
assertion failures on the buggy version and a pass on the fixed control. That
container outcome was **verified in GitHub Actions**; see the linked CI run.
The build environment itself has no Docker daemon. The candidate is a supplied fixture,
not an AI-generated result.

Without Docker the CLI exits 3 and writes an honest `could_not_investigate` report.
The actual local blocked-run evidence is included at `delivery/blocked-demo/`.

## Generate a test using a local model

Install Ollama separately and explicitly download a model your machine can support.
Run `ollama list` to obtain an installed model name; replace `YOUR_INSTALLED_MODEL`:

```bash
python -m issueforge run \
  --repo examples/buggy --issue examples/issue.md \
  --model YOUR_INSTALLED_MODEL \
  --endpoint http://localhost:11434/v1 \
  --control-repo examples/fixed \
  --out runs/local-model
```

The model must support Chat Completions JSON-object responses and the selected
request parameters. Provider compatibility beyond the tested HTTP contract is
unverified. Small models may return invalid actions or weak tests; these are
reported, not silently promoted to successes.

For an authorized remote compatible provider, set `ISSUEFORGE_API_KEY` securely in
your environment and pass its HTTPS `--endpoint`, `--model`, and `--allow-remote`.
That flag explicitly consents to transmitting filtered source/issue content and
possible provider charges. No paid API was called while building this release.
Redaction cannot guarantee secret removal: review source before using any model.
A localhost proxy can itself call cloud models; configure its billing separately.

## Commands and configuration

| Option / command | Meaning |
| --- | --- |
| `inspect --repo PATH` | Print included files and SHA-256; imports no target code |
| `doctor [--image IMAGE]` | Check Linux Docker daemon and cached image; no pull |
| `run --repo PATH --issue FILE --out NEW_PATH` | Investigate one local checkout |
| `--candidate FILE` | Evaluate supplied unittest code; no model use |
| `--model NAME` | Use the structured investigation loop instead |
| `--control-repo PATH` | Require candidate to pass on a known-fixed snapshot |
| `--endpoint URL` | Compatible `/v1` base; default `http://localhost:11434/v1` |
| `--allow-remote` | Explicit consent for remote source transfer/API use |
| `--image IMAGE` | Owner-prepared image with project dependencies; no auto-install |
| `--timeout N` | Per-container timeout, 1–120 seconds, default 25 |
| `--model-timeout N` | Model-request timeout, 1–120 seconds, default 30 |
| `--max-steps N` | Model call limit, 1–12, default 6; at most 3 proposed tests |
| `ISSUEFORGE_BASE_URL` | Endpoint default; CLI option overrides it |
| `ISSUEFORGE_API_KEY` | Model credential, never forwarded into containers |
| `ISSUEFORGE_DOCKER_TESTS=1` | Opt in to actual Docker integration tests |

`.env.example` is a configuration reference; dotenv files are not automatically loaded.
Exit codes: **0** stable assertion failure observed; **1** candidate passes;
**2** invalid input/configuration; **3** inconclusive, blocked, or incomplete evidence.
For `inspect` and `doctor`, 0 means that command succeeded, not reproduction.

## Evidence semantics

- `reproduced`: baseline is usable, two fresh runs have the same normalized
  assertion-failure trace, and a supplied fixed control passes if provided.
- `not_reproduced`: both runs pass. This says nothing about other inputs or tests.
- `could_not_investigate`: environment/loader errors, timeout, inconsistent outcomes,
  insufficient evidence, failed control, or unavailable sandbox.

An assertion can be wrong. A generated test can be unrelated to the reported bug.
The verdict proves neither causality nor test relevance; inspect the candidate.
A fixed control improves evidence but is not automatically authored or validated.

Each evidence directory contains `report.json`, `report.md`, and a `candidate_N.py`
for each evaluated proposal. A stable reproducer is also exported as
`test_reproduction.py`. Source hashes refer to the filtered snapshot, not a Git commit.
Raw repository snapshots are not retained in the evidence directory.

## Architecture

The CLI validates consent and paths. `policy.py` makes an immutable, bounded text
snapshot without importing target code. `engine.py` mediates `read`, `search`,
`propose`, and `stop` actions. `provider.py` handles HTTP and structured responses.
`sandbox.py` enforces execution arguments and time/output limits. The container
harness runs unittest; `evidence.py` determines the conservative mechanical verdict.

No swarm is needed for this slice: the dependency between test proposals and
execution feedback is sequential. Token/call/context limits, explicit stopping,
and recorded tool observations keep the investigation bounded.

Model requests have a configurable timeout (30 seconds by default) and a 1,600 completion-token limit per call;
there are no automatic HTTP retries. This caps request counts, not currency spend.
Context is bounded to 70,000 serialized characters per request. Source snapshots
are limited to 500 files, 2 MB total, and 256 KB per file. Binary assets, hidden files,
symlinks, common build directories and secret-named files are excluded.

## Verification and development

```bash
python -m unittest discover -v
python -m compileall -q issueforge
# With Docker and a deliberately cached image:
ISSUEFORGE_DOCKER_TESTS=1 python -m unittest tests.test_docker_integration -v
# Optional developer linter:
python -m pip install ruff
ruff check .
```

HTTP tests use a local **simulated server**; orchestration tests use a **test-double
sandbox**. Neither establishes live model or Docker behavior. CI config includes
separate host and real-container jobs; both passed on the implementation commit.
See `delivery/github-ci.json` for the exact revision and evidence.

## Limits and next work

- Small stdlib/unittest projects only by default. No pytest adapter, dependency
  auto-installation, arbitrary shell tools, package builds or repair generation.
- Text-only snapshots omit data fixtures and may change the target environment.
- Docker is not a microVM and not a hostile multi-tenant security boundary.
- Repository code can tamper with in-process test telemetry; there is no independent
  execution attestation. Logs and model text remain untrusted.
- AST checks reject trivial unconditional failures, but are not a security analyzer.
- No real-issue evaluation or user adoption study has been performed. The proposed
  adoption advantage remains a hypothesis.

See [security](SECURITY.md), [contribution guidance](CONTRIBUTING.md),
[verification](docs/VERIFICATION.md), and [GitHub handoff](docs/HANDOFF.md).

## License

MIT for original source. No competitor source, benchmark corpus, model weights or
container images are bundled. External dependencies retain their own licenses and
service terms; review those before deployment or redistribution.

## Real-model GitHub Action

`.github/workflows/live-model.yml` is separate from the ordinary checks. It runs
Ollama 0.40.6 (pinned image digest) and `qwen2.5-coder:7b-instruct-q4_K_M` locally
on a standard Ubuntu CPU runner. No hosted model API, key or paid inference endpoint
is used. Cloud features are disabled and the server binds to loopback. The job has
a 20-minute timeout, bounded requests and limited model-container resources.

For a same-repository PR touching source, fixtures, tests or this workflow, the job
runs automatically. After the workflow is merged to the default branch, it also
supports **Actions → live-model → Run workflow**. It does not run on fork PRs.
No workflow uses `pull_request_target` or repository write permissions.

The model receives the buggy source snapshot and issue, **not** a supplied regression
test or the fixed checkout. It must generate a test through the normal agent loop.
The test must fail with matching assertions twice on the buggy source and pass on
the known-fixed control. `scripts/verify_live_evidence.py` also requires live-model
mode, actual recorded output tokens, executed tests and a matching artifact hash.

Every attempt uploads `live-model-evidence-RUN_ID-ATTEMPT` for 14 days, including
the generated test, report, verification gate and runtime/model metadata when
available. A failed model run fails the job and retains its evidence; it is never
replaced with an offline candidate. Download and inspect the artifact from the run.
The first run is pending; a workflow definition is not itself proof of inference.

The 7B Qwen model is about 4.7 GB in this quantization, Apache-2.0 licensed, and
selected for a small CPU smoke test, not as a claim of best model quality. See
[model](https://ollama.com/library/qwen2.5-coder:7b-instruct-q4_K_M),
[Ollama Docker](https://docs.ollama.com/docker), and
[release](https://github.com/ollama/ollama/releases/tag/v0.40.6).
A passing authored fixture is only integration evidence, not a real-world benchmark.
