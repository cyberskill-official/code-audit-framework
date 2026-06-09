# AUDIT.md Protocol Changelog

Versioning: **MAJOR.MINOR.PATCH**

- **MAJOR** — restructured phases/rules
- **MINOR** — new rule or vector
- **PATCH** — wording/typo/clarity fix

**Rules of the loop:**

1. **One change per version.** Every released version differs from its predecessor by exactly one deliberate change.
2. **Released versions are immutable.** A change = a new file in `improve/versions/` + an entry here. Never edit a released version in place.
3. **Every change cites a trigger** — a retrospective item, a failure-log row, or an eval regression. No speculative edits.
4. **Every change is gated by the eval harness.** `python3 evals/validate.py --all` must be green before a version is released.

---

## v1.0.0 — 2026-06-10

- **Initial public release** under [cyberskill-official/code-audit-framework](https://github.com/cyberskill-official/code-audit-framework). The repository is the product: the AUDIT.md protocol plus the machinery that improves it (the `improve/` loop, the `evals/` regression gate, and the product page).
- **What 1.0.0 contains.** A ~160-line, AI-agnostic audit protocol: one-sentence role, per-project CONFIG block, 8 core rules (evidence-or-nothing, honest targets, protected core, file-is-memory, one-task micro-loop, 3-strike circuit breaker, severity-weighted findings, secret redaction), and a 6-phase state machine with a reachable stop rule.
- **Provenance.** 1.0.0 consolidates an internal pre-release lineage: a 150 KB / 1,898-line monolith prompt (4 documented production runs), a research-backed rewrite, and a 5-cycle self-improvement campaign (2026-06-10) that closed three High-severity letter-vs-intent gaps — row-traceable evidence (each measured metric's output block opens with `$ <verify command>`), durable gated-mode approvals (the `Approved:` artifact), and a single closed metric-status vocabulary across R1 and Phase 5 — each change gated by the fault-injection eval suite (**15/15 green at release**). Internal version identifiers from that lineage (v1.x-era, v2.0.0–v2.1.1) appear in `improve/FAILURE_LOG.md` and `improve/retros/`; the full history is preserved in git log prior to this release.
