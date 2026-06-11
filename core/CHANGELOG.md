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

## v1.3.0 — 2026-06-10 (improvement campaign 4, cycle 1)

- **MINOR: The backlog now echoes its protocol version.** Phase 2's "Scope & method" template line opens with `Protocol: <this file's title version>`, making every artifact self-describing. The validator gates template requirements on the stated version (a v1.0.0 artifact is judged by the v1.0.0 template — no Mode echo required; a current artifact omitting the echo is itself nonconformant), which makes mixed-version artifact fleets validate correctly from v1.3.0 forward. Net protocol size change: 0 lines (edit to an existing template line; AUDIT.md remains 164 lines).
- **Trigger:** Architect review 2026-06-10, finding F-5 (version skew) — artifacts don't state which protocol produced them, so the validator assumed the current template and false-positived on older runs. Second observation of the self-describing-artifact family (first: campaign-2's Mode echo, v1.1.0) — promotion bar met. FAILURE_LOG row promoted this cycle.
- **Harness, same cycle:** version-aware `check_template_conformance` (`CURRENT_PROTOCOL` kept in lockstep by check-docs-sync); trap `B24-missing-protocol-echo`; precision sibling `G10-legacy-version-artifact` (stated v1.0.0, no Mode echo → clean). All 30 template-conformant fixtures strengthened to the v1.3.0 Scope line. Evals: **34/34 green**, baseline re-recorded at v1.3.0.
- **Also in campaign 4 (infra, landed before this cycle):** the calibration sprint from the architect review — fence-aware parsing (F-1: quoted tool output neither trips checks nor satisfies the template; G07/B19), the Final-column escape closed (F-2: column shape selects semantics, never disables checks; B20), artifact problems became verdicts (F-3: `MALFORMED-FILE`, never tracebacks; B21), CONFIG-preflight precision (F-4: generics/redirection/`#`-values stay valid; G08), waivers v1 (`docs/AUDIT-WAIVERS.yaml` — audit-trailed, expiring suppressions; G09/B22), `--aggregate` portfolio roll-up, published report schema (`schemas/report.v1.json`, CI-validated), redaction-distance behavior pinned (B23), COMPLIANCE.md control mapping, air-gap property documented.

## v1.2.0 — 2026-06-10 (improvement campaign 3, cycle 1)

- **MINOR: Phase 0 gains a CONFIG preflight.** Three lines: if any CONFIG value still contains `<placeholder>` text, or MODE / DEPTH / BENCHMARK_MODE / SEVERITY_FLOOR is outside its allowed set, the agent STOPs and asks the human instead of improvising CONFIG. Closes the most likely first-run failure mode on a new codebase: a half-filled CONFIG silently "completed" by the agent, which then audits against invented constraints.
- **Trigger:** Structural review 2026-06-10, gap G-D — CONFIG improvisation is the documented norm for agents handed partial configs; nothing in the protocol or the validator checked CONFIG sanity (FAILURE_LOG row "CONFIG improvisation", promoted this cycle). Protocol side of `improve/BLINDSPOTS.md` BS-13.
- **Harness, same cycle (landed as the preceding infra commit):** the validator preflights the target AUDIT.md's CONFIG — `CONFIG-PLACEHOLDER` / `CONFIG-BAD-ENUM` (trap fixture `B17-config-placeholder`) — and auto-loads `PROTECTED_AREAS` into the R3 tripwire (`B18-config-autoprotect`), retiring the `--protected` double entry (gap G-F). Instruction budget: 161 → 164 lines, within the 200-line cap. Evals: **24/24 green**, baseline re-recorded at v1.2.0.
- **Also in this campaign (infra, not protocol changes):** template-conformance meta-tripwire `TEMPLATE-NONCONFORMANT` (BS-12 — non-template output no longer escapes every check; fixtures B15/G05/G06), compound exact-set fixture (B16), precision pack G03/G04 (G:B ratio 2:14 → 6:18), `--report json|sarif` findings export, `evals/scripts/retro-summary.py`, Apache-2.0 LICENSE + NOTICE, CI eval gate (suite + version-sync + baseline sha256 + snapshot immutability), CONTRIBUTING.md, SECURITY.md.

## v1.1.0 — 2026-06-10 (improvement campaign 2, cycle 1)

- **MINOR: The backlog now echoes its MODE.** Phase 2's "Scope & method" template line gains a leading `Mode: <MODE>` field. This makes the gated-mode guarantee post-hoc enforceable: the validator now flags any loop section that declares `Mode: gated` and contains executed tasks (DONE / IN-PROGRESS / BLOCKED) without an `Approved:` line — previously the check fired only when the line already existed, so *omitting it entirely* evaded the gate.
- **Trigger:** Blind-spot review 2026-06-10 (High) — live exploit demonstrated against v1.0.0: a synthetic gated run with executed tasks and zero `Approved:` lines validated "CLEAN — no violations" (`improve/BLINDSPOTS.md` BS-08). Second observation of the family first logged in pre-release cycle 4 (FAILURE_LOG) — promotion bar met.
- **Harness:** `check_approvals` fires on `Mode: gated` OR an `Approved:` line; new trap fixture `B14-gated-missing-approval` (the exploit, verbatim, as a fixture); `G01-clean-run` strengthened to exercise the positive gated path. Net protocol size change: 0 lines. Evals: **16/16 green.**

## v1.0.0 — 2026-06-10

- **Initial public release** under [cyberskill-official/code-audit-framework](https://github.com/cyberskill-official/code-audit-framework). The repository is the product: the AUDIT.md protocol plus the machinery that improves it (the `improve/` loop, the `evals/` regression gate, and the product page).
- **What 1.0.0 contains.** A ~160-line, AI-agnostic audit protocol: one-sentence role, per-project CONFIG block, 8 core rules (evidence-or-nothing, honest targets, protected core, file-is-memory, one-task micro-loop, 3-strike circuit breaker, severity-weighted findings, secret redaction), and a 6-phase state machine with a reachable stop rule.
- **Provenance.** 1.0.0 consolidates an internal pre-release lineage: a 150 KB / 1,898-line monolith prompt (4 documented production runs), a research-backed rewrite, and a 5-cycle self-improvement campaign (2026-06-10) that closed three High-severity letter-vs-intent gaps — row-traceable evidence (each measured metric's output block opens with `$ <verify command>`), durable gated-mode approvals (the `Approved:` artifact), and a single closed metric-status vocabulary across R1 and Phase 5 — each change gated by the fault-injection eval suite (**15/15 green at release**). Internal version identifiers from that lineage (v1.x-era, v2.0.0–v2.1.1) appear in `improve/FAILURE_LOG.md` and `improve/retros/`; the full history is preserved in git log prior to this release.
