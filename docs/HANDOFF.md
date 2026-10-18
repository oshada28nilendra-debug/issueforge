# GitHub delivery

Designated repository: https://github.com/oshada28nilendra-debug/issueforge

Feature branch: `feat/issueforge-first-release`; base: `main`.
The original repository contained only its initial README and no license or extra instructions.
Pull request: https://github.com/oshada28nilendra-debug/issueforge/pull/1 . The PR is open and unmerged. Do not merge automatically.

CI includes Python 3.11/3.12/3.13 host checks and a separate Linux Docker job.
All four jobs passed on the implementation commit; see `delivery/github-ci.json`.
The archive's local blocked Docker run is historical evidence.

A real-model fixture investigation has now passed and its generated test was reviewed.
Evidence: https://github.com/oshada28nilendra-debug/issueforge/actions/runs/39096221948 .
Remaining release action: user review and merge of PR #1. Broader real-issue
evaluation remains future work, not a completed benchmark.
No provider API keys or model weights are included. No paid model calls are authorized
by repository designation alone.
