# Verification record

Latest: the real-model fixture smoke test passed; see the final section and
`delivery/live-model-verification.json`. Earlier sections retain historical checkpoints.

## Initial local verification

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

## First remote CI results

[PR #1](https://github.com/oshada28nilendra-debug/issueforge/pull/1) and [CI run](https://github.com/oshada28nilendra-debug/issueforge/actions/runs/39093841366) were inspected after publication.
Python 3.11, 3.12 and 3.13 jobs all passed: 45 host/offline tests each, with
three Docker tests deliberately skipped in those host-only jobs. The separate
Docker job ran all three actual-container tests with **3 passed, 0 skipped**.
The decoded job log was checked, not only the job badge.

Tested implementation commit: `a6816212ff44bcdbe339b4e28c092626ec806bcf`.
The following update changes delivery documentation and the ledger only.
See `delivery/github-ci.json` for exact job status and container-image digest.
The historical local blocked report is retained for provenance.

**Intermediate checkpoint (superseded below): Docker verified; live model pending.**
No real language model or paid API was exercised. The PR remains unmerged.

## Real-model GitHub Action

[Live-model run](https://github.com/oshada28nilendra-debug/issueforge/actions/runs/39096221948) passed on commit `4f4a25db601ffa5ca0c4c7275ab8a79afc3f9381`.
Ollama 0.40.6 ran Qwen2.5-Coder 7B Q4_K_M locally on the Ubuntu CPU runner with
cloud features disabled. It received the buggy snapshot and issue, not a supplied
candidate or fixed-source contents. One model call used 678 prompt tokens and
produced 124 completion tokens. No paid model API or key was used.

The generated test calls the actual prices.total function on the reported values
and asserts the expected Decimal total. Its relevance was reviewed from the saved
source. It failed with matching assertions in two fresh containers and passed on
the fixed control. The strict live-evidence gate passed, including the output hash.

Current host suite: **52 passed, 3 Docker-only skips**. The separate Docker job ran
all three actual-container tests successfully. Python 3.11/3.12/3.13 checks passed.
The following commit adds delivery evidence/documentation only.

Three earlier 1.5B attempts failed: two emitted invalid code; the third generated
runnable tests but included an unrelated assertion that failed on the fixed control.
Those failures were preserved rather than converted into successes. Prompt clarity,
syntax diagnostics and rejected-action traces were improved; the final live job
uses 7B. See `delivery/live-model-history.json` for exact revisions and run URLs.

Current status: **bounded release verified; PR #1 open for user review**. This is
one authored fixture, not a real-issue success-rate evaluation or production claim.
The retained JSON report, model/runtime digests and generated-test text document
what was actually exercised. The original local blocked report is historical.
