# Risk Register

| Risk ID | Risk | Likelihood | Impact | Early warning | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| R-001 | Chat history diverges from repository state | Medium | High | Different models cite different facts | Read state files at startup; update handoff and commit | Project owner | Open |
| R-002 | Sensitive information is committed to Git | Low | Critical | Secrets or unredacted originals appear in working tree | Private repo, `.gitignore`, source index, secret review | Project owner | Open |
| R-003 | An AI performs an unauthorized external write | Low | High | Send/push/delete/permission action without clear approval | Read-only defaults and explicit approval boundary | Project owner | Open |
| R-004 | A writable local approval record is mistaken for human authentication or a security sandbox | Medium | High | Claims that the gate controls hostile code or untrusted actors | Document the workflow-integrity boundary; retain external permission controls; fail closed on missing/runtime-unverifiable state | Project owner | Known limitation |
| R-005 | Distributed skill/template copies omit the current gate | Low | High | Payload drift or generated project missing gate files | Synchronize canonical/native/standalone payloads; CI --check plus real standalone generation tests | Maintainer | Mitigated for Issue #2 |
