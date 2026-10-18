# IssueForge evidence

Status: **could_not_investigate**

Source SHA-256: `df8ef30762c818d2cbfacec33778436432591e1ef145aa1c5c5dacb1d3b54388`

Model mode: `supplied_candidate`

Execution backend: `docker`

Model endpoint verified: `False`

Docker execution verified: `False`

A reproduced verdict means two matching assertion failures were observed.
It does not prove test relevance, root cause, or security. Review the test.

Blocker: Docker CLI is unavailable; no host fallback exists

## Limitations

- Assertion failure is mechanical evidence; human review must confirm relevance.
- Only a filtered text snapshot is executed, not a complete installed checkout.
- Only stdlib unittest projects are supported by the default image.
- Docker shares a kernel; use a disposable machine for hostile code.
- Repository code can tamper with in-process unittest telemetry; not adversarial attestation.
- Redaction is best effort; review source and reports before sharing.
