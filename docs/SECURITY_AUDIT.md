# Security and privacy audit — 18 October 2026

## Assessment

No credentials were detected by the scans described below. This is a bounded
source/history review, not a penetration test, proof of complete security, or proof
that nobody accessed public information. The repository is public.

The documented local workflow has useful isolation and consent boundaries. It is
appropriate for controlled evaluation of code you own or are authorized to inspect,
subject to the limitations in SECURITY.md. It is not approved as a public service
for running arbitrary hostile repositories.

## Scope and evidence

Baseline: `f536534b78b112fbae58186288d512b751ae0655` (merged main).
The subsequent audit branch changes were scanned again before publication.

| Check | Result |
| --- | --- |
| Gitleaks 8.30.1 current working directory | No findings |
| Gitleaks reachable Git history, `--log-opts=--all` | No findings; scanner examined 8 non-empty commits; 9 reachable commits total |
| Git commit metadata exported and separately scanned | No credential findings; personal author email found by metadata review |
| Five available ZIP archives, extracted as text without executing code | No findings across 74 prepared entries including metadata |
| New redaction regressions | 4 tests pass; quoted JSON, authorization headers, database URLs and unchanged ordinary code |
| Full local suite | 59 tests discovered; 56 passed; 3 real-Docker tests skipped because Docker is unavailable locally |
| Ruff lint/format and Python compilation | Passed |

The archives were `IssueForge-2026-10-18-source.zip`,
`live-model-first-attempt.zip`, `live-model-second-attempt.zip`,
`live-model-third-attempt.zip` and `issueforge-live-model-passed.zip`.
They include the available source package and downloaded model-run reports/logs.
This does not cover every GitHub account repository, historic workflow artifact,
issue attachment, deleted/unreachable commit, third-party copy or local device.

Scanner source: [Gitleaks](https://github.com/gitleaks/gitleaks).
Downloaded the official 8.30.1 Linux release and verified its SHA-256 against the
release checksums before execution. Archive SHA-256:
`551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`.
No source was uploaded to an external scanning service. Credential values are not
included in this report. Automated detection can miss custom/encoded secrets.

## Findings and changes

### Public personal email in commit metadata

The reachable public history uses a Gmail author address. Its value is deliberately
not repeated here. This is contact information exposure, not evidence of an API-key
leak. Use GitHub's private/noreply commit email for future commits and enable email
privacy in account settings. Existing commits and copies retain their metadata.
History was not rewritten, and changing account settings does not remove old copies.

### Incomplete best-effort redaction

The previous redactor missed quoted JSON secret keys, HTTP Bearer/Basic credentials
and passwords inside database URLs. Synthetic regression tests reproduced the gaps;
the new implementation filters those forms and preserves JSON delimiters.

This finding is a potential disclosure path when users put credentials in ordinary
source/issue/log text. It is **not** evidence that a real credential was disclosed.
Redaction remains best effort. Model-generated executable candidates are preserved
verbatim and may themselves include sensitive information. Review all artifacts
before publishing them. Do not use redaction as permission to submit secret files.

### Preventive secret scanning

The `secret-scan` workflow scans reachable Git history on pushes, pull requests and
manual dispatch. Its Gitleaks binary is version/checksum pinned. It has read-only
repository permissions and does not upload scan reports or call a model provider.
Checkout credentials are not persisted by this workflow. A passing scan has the
same detection limits as the local scan.

## Runtime review

- Target code is executed only in Docker with network disabled, read-only mounts,
  non-root identity, dropped capabilities, no-new-privileges and bounded resources.
  The host Docker socket and API credentials are not mounted/passed to target code.
- The HTTP adapter requires explicit remote consent and HTTPS for remote endpoints,
  refuses redirects and avoids including provider response bodies in errors.
- Model actions are bounded read/search/propose/stop operations. AST checks are
  shape checks; Docker shares the host kernel and test telemetry is spoofable.
- Snapshot exclusions reduce accidental secret exposure but cannot identify every
  embedded secret. Concurrent hostile filesystem mutation is outside the threat model.
- Local reports can contain private paths, code and test data. The CLI does not
  automatically upload them. CI intentionally publishes fixture evidence artifacts.

## What remains unknown

Private GitHub security alerts/settings, organization logs, API-provider account
logs, key inventories and end-user devices were not accessible in this review.
No claim is made that those systems are clean or that nobody downloaded public
content. If a real credential is later found, revoke/rotate it at its provider
first; deleting the text alone does not revoke access.

Review [GitHub secret scanning guidance](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning)
for native alert coverage. This audit does not establish that those alerts are enabled.
