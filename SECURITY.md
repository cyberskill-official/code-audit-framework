# Security Policy

## Supported versions

Only the latest released version of the protocol (`AUDIT.md` on `main`) and its
validator (`evals/validate.py`) are supported. Historical snapshots in
`improve/versions/` are immutable records, not supported artifacts.

## Reporting a vulnerability

Email **info@cyberskill.world** with subject `SECURITY: code-audit-framework`.
Please do not open a public issue for anything exploitable. We aim to
acknowledge within 3 business days.

In scope:

- The validator (`evals/validate.py`) mis-parsing crafted run artifacts in a
  way that hides planted violations (validator bypasses).
- Secret-redaction gaps: a credential format that R8/`SECRET_PATTERNS` should
  plausibly catch but does not (include a sanitized example, never a live key).
- CI workflow weaknesses that would let a protocol change land unguarded.

Out of scope (by design, documented in `improve/BLINDSPOTS.md`):

- "The validator can't prove the agent actually ran the command" — execution
  authenticity is BS-01, an accepted limit; hard guarantees belong in the
  target repo's own CI.
- Prompt-injection resistance of any particular LLM running the protocol.

## Handling of secrets in this repo

This repository's own artifacts are held to the protocol's R8: credentials
never appear unredacted in any committed file. Eval fixtures that exercise the
secret-leak tripwire (e.g. `B07`, `B16`) use synthetic, non-functional values
with valid formats only.
