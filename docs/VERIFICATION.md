# Verification record

Recorded: 2026-10-18T08:49:34.721574+05:30. Python 3.12.14.

- **45 tests passed; 3 real-Docker tests skipped** (48 discovered).
- Ruff lint, Ruff format check, and Python compilation passed.
- Wheel build and installed-wheel CLI smoke test passed.
- HTTP contract tests used a local simulated server, not an actual model.
- Process-supervision tests used a fake Docker executable to exercise actual
  subprocess timeout, output caps and cleanup; these are not container tests.
- Investigation-loop tests used scripted model/sandbox doubles.
- The actual CLI `run` produced `could_not_investigate`, exit 3, with a Docker
  unavailable blocker. It did not execute target code on the host.
- No real model calls, paid calls, remote GitHub changes, CI runs or deployments.

Machine-readable results: `delivery/verification.json`. Exact host-side command
logs: `delivery/unit_and_offline_tests.txt`, `delivery/lint.txt`,
`delivery/format.txt`, and `delivery/compile.txt`. Actual blocked investigation:
`delivery/blocked-demo/report.json` and `report.md`.

## Skipped checks

The three real-container cases cover the known bug plus fixed control, a passing
candidate on the fixed repository, and network/user/filesystem restrictions.
They require an available Linux Docker daemon and deliberately cached image.
Their CI job is configured but has **not** run remotely.

Live-model efficacy is unknown. Run a real local model only after Docker is ready,
then review the generated test against the reported behavior. An HTTP schema test
cannot establish model reasoning quality or provider interoperability.

## Delivery status

**Implementation delivered, essential integration verification blocked.** Do not
mark the morning slot fully verified or production-ready. The source can be
reviewed and its host-side checks reproduced now. Before claiming the full core
workflow works, complete Docker execution and a real-model investigation.

## Publication continuation

The user subsequently designated https://github.com/oshada28nilendra-debug/issueforge.
The implementation is prepared on `feat/issueforge-first-release`; remote CI is pending.
The no-repository statement above describes the initial archive checkpoint.

## Current remote CI results

[PR #1](https://github.com/oshada28nilendra-debug/issueforge/pull/1) and [CI run](https://github.com/oshada28nilendra-debug/issueforge/actions/runs/39093841366) were inspected after publication.
Python 3.11, 3.12 and 3.13 jobs all passed: 45 host/offline tests each, with
three Docker tests deliberately skipped in those host-only jobs. The separate
Docker job ran all three actual-container tests with **3 passed, 0 skipped**.
The decoded job log was checked, not only the job badge.

Tested implementation commit: `a6816212ff44bcdbe339b4e28c092626ec806bcf`.
The following update changes delivery documentation and the ledger only.
See `delivery/github-ci.json` for exact job status and container-image digest.
The historical local blocked report is retained for provenance.

**Current status: published and Docker-verified; live-model verification pending.**
No real language model or paid API was exercised. The PR remains unmerged.
