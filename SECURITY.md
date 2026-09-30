# Security policy

Skillspector Web helps people decide whether to trust third-party code, so security reports are
taken seriously.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub:
[**Security → Report a vulnerability**](https://github.com/maelbel/skillspector-web/security/advisories/new).

Include what you found, how to reproduce it, and the impact you expect. You'll get an
acknowledgement, and a fix or mitigation will be coordinated with you before anything is
disclosed.

Vulnerabilities in the scanning engine itself belong to
[NVIDIA/skillspector](https://github.com/NVIDIA/skillspector/security).

## Supported versions

Only the latest release receives security fixes.

## Scope and known limitations

The deployment model and its deliberate trade-offs — no user accounts, a shared server Claude
login, unrestricted custom AI base URLs — are described in the
[security model](./docs/SECURITY_MODEL.md). Reports that show those boundaries being
bypassed (for example reaching admin actions without the token, or scanning internal addresses)
are in scope.
