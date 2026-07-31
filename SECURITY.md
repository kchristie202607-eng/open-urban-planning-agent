# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability in OUPAP, please **do not** open a
public issue. Instead, report it privately to the maintainer:

- Email: **maintainer@example.com** (replace with the real contact)
- Or use GitHub's private vulnerability reporting on the repository's
  **Security → Advisories** tab.

Please include:

- A description of the vulnerability and its impact
- Steps to reproduce
- Any suggested mitigation

We aim to acknowledge reports within **5 business days** and to provide a
remediation plan within **30 days**, depending on severity.

## Local-First Design (Privacy by Architecture)

OUPAP is designed so that **no confidential planning data ever leaves the
user's machine**:

- The framework (agents, workflow engine, interfaces, evaluation tools) is public.
- Project data, GIS datasets, planning documents, and enterprise knowledge
  bases remain on the local filesystem and are excluded from the repository
  by `.gitignore`.
- No telemetry, analytics, or network calls to third parties are made by the
  core engine.

Because of this design, most security concerns involve dependency hygiene and
safe handling of local files, not data exfiltration.

## Dependency Hygiene

- Keep `requirements.txt` current.
- CI runs dependency/security checks on each pull request.
- Report outdated or vulnerable dependencies through the process above.
