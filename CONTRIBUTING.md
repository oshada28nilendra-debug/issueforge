# Contributing

Start with the README and validation record. This release targets small unittest
projects; propose scope extensions with a real user workflow and a testable boundary.

Run `python -m unittest discover -v` and `python -m compileall -q issueforge`.
With Docker available, deliberately cache the default image and run the opt-in
container suite. Run `ruff check .` if installed. Never execute untrusted fixtures on
the host. Keep regression fixtures small, original and license-compatible.

Useful next contributions: Docker-platform verification, real local-model trials,
manual relevance evaluation, a pytest harness, carefully bounded non-text fixtures,
and independently validated execution records. Add tests for behavior changes and
failure paths. Keep offline doubles visibly distinct from live integrations.

Open PRs with the user problem, behavior change, actual checks run and limitations.
Do not commit keys, provider transcripts containing private code, real private issues,
large models, container layers or generated evidence from sensitive repositories.
