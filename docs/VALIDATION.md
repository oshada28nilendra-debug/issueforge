# Validation record — 2026-10-18-morning

Decision: **narrow and proceed with an implementation for review**, not a novelty
or product-market-fit claim. Container execution and live-model effectiveness remain
unverified in this delivery environment.

## User, pain and proposed value

Target user: a maintainer triaging small Python/unittest repositories.
Pain: turning an informal issue into an executable test, while distinguishing the
reported bug from missing dependencies or a misleading failure.
Proposed differentiator: a deliberately small reproduction-only workflow exporting
source fingerprints, two fresh execution attempts and optional known-fixed controls.
It preserves the original checkout and exposes inconclusive outcomes explicitly.

These are design choices, not evidence that alternatives cannot do the same thing.
No user interviews or willingness-to-adopt study have been conducted. The hypothesis
is that a focused artifact is easier to audit and integrate into manual triage than
a broad repair workflow; this needs testing with maintainers.

## Alternatives actually inspected

| Alternative | Observed capability | Implication for this project |
| --- | --- | --- |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | General issue-solving agent; current README points to mini-SWE-agent | Reproduction alone is not novel. Keep scope and audit artifacts explicit. |
| [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk) | SDK for agents with local/ephemeral workspaces and tool integrations | Do not claim sandboxing or agent tooling as an invention. Offer a smaller focused workflow. |
| [AutoGen](https://github.com/microsoft/autogen) | General multi-agent framework; current README refers users to its successor | A framework is an alternative implementation route, not proof of demand for another swarm. No AutoGen dependency is used. |
| [SWE-Doctor, July 2026](https://arxiv.org/abs/2607.00990) | Research studies runtime diagnoses derived from bug reproduction tests | Grounded reproduction is an active research topic. No paper metrics are claimed for IssueForge. |

The SWE-Doctor abstract reports that some reproduction-test outcomes can mislead
patch generation. This supports conservatism about failure evidence, not a claim
that IssueForge solves that research problem. Only the abstract was reviewed;
no experimental claims from the paper were independently replicated.

## Technical and licensing checks

- [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility): local
  Chat Completions endpoint shape is documented. A real HTTP adapter is implemented,
  with a local simulated-server contract test. No installed model was exercised.
- [Docker run reference](https://docs.docker.com/reference/cli/docker/container/run/):
  network, mount, capability, user and resource arguments checked against official
  documentation. Docker is absent locally, so operational correctness is unverified.
- Python standard-library unittest, urllib, dataclasses, pathlib and subprocess APIs
  are used; no third-party Python runtime dependencies or copied competitor code.
- New original code uses MIT. Competitor code is not incorporated. No external
  dataset, model weights, image layers or papers are redistributed.
- Setuptools is used only for optional package builds. Docker/Python base images and
  separately installed models carry their own licensing obligations.

## Acceptance criteria and actual status

| Criterion | Status |
| --- | --- |
| Inspect a bounded source snapshot without importing target code | Verified locally |
| Agent read/search/propose loop with a real HTTP adapter | Implemented; orchestrator tested with doubles; HTTP contract tested with simulated server |
| Avoid host fallback when Docker is absent | Verified locally, including CLI report |
| Preserve input files and reject overwriting existing evidence | Verified locally |
| Classify stable failures, errors, passes and inconsistent outcomes | Verified with deterministic records |
| Run buggy fixture twice and pass fixed control in real containers | Blocked locally; explicit opt-in tests and CI job supplied |
| Produce a relevant reproducer using a real model | Not verified; requires a configured model plus Docker |
| GitHub PR and CI | Repository designated after initial delivery; CI pending |

## What could invalidate the product

The workflow may be too narrow for maintainers' real dependency environments; a
small model may not produce useful tests; manual test-relevance review may dominate
triage time; broad agents may already provide a better experience. A failed runtime
check or weak real-issue results should trigger scope revision, not inflated claims.

Next validation: run the included container suite, test one local model, then use a
small set of permitted real issues with a manually reviewed reproduction oracle.
Compare the same model with one-shot test generation under the same context and
request budget. Record correctness, false reproductions, model calls, latency and
failure causes; no results exist yet.
