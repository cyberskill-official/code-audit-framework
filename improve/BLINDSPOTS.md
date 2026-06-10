# Blind-spot register

The single authoritative list of what this protocol + harness **cannot see**.
Scattered declarations (rules.json coverage notes, evals/README, retro
watchlists, README caveats) point here. One row per blind spot; never delete a
row — change its status.

Statuses: **ACCEPTED** (inherent limit, documented, mitigation is process or
hooks/CI) · **MITIGATED** (tripwire or check reduces exposure; not a proof) ·
**CLOSED** (mechanically checked by the harness).

Last full review: **2026-06-10** (post-1.0.0 ownership review). The seven
previously declared blind spots (BS-01…BS-07) were re-verified against
`evals/validate.py` and all fixtures; the review found **four additional ones**
(BS-08…BS-11), two of them demonstrated by live exploit before fixing.

| # | Blind spot | First declared | Status |
|---|---|---|---|
| BS-01 | **Execution authenticity** — the validator checks artifact *form*; it cannot prove a pasted "raw output" came from actually running the command. Wholesale fabrication of plausible output passes. | evals/README (live-agent gap) | ACCEPTED — hard guarantees belong in deterministic hooks/CI in the target repo (README caveat 1) |
| BS-02 | **Resume behavior (R4)** — whether a session truly resumed from artifacts instead of restarting is a live-agent property; no fixture can exercise it. | rules.json R4 coverage note | ACCEPTED |
| BS-03 | **3-strike counting (R6)** — only the end artifact (BLOCKED + "Root cause:") is checkable; the validator cannot count in-session attempts. | rules.json R6 coverage note | ACCEPTED — artifact half is trapped by B08 |
| BS-04 | **Citation authenticity (R2)** — a present URL is checkable; that it was *actually fetched* and is *relevant* is not (no network in the validator, by design). | pre-release retro cycle-5 | ACCEPTED — retro item 2 covers it by judgment |
| BS-05 | **Behavioral preservation (R3)** — the validator substring-matches protected paths in task rows (tripwire, can false-positive on prose); semantic behavior-preservation needs the target repo's own tests. | rules.json R3 coverage note; pre-release retro cycle-4 | ACCEPTED — tripwire stands (B09) |
| BS-06 | **Padding and change value (R7)** — whether findings were manufactured or changes were genuinely valuable is human judgment (retro items 3 and 9); the harness only guarantees padding is never *required*. | evals/README; G02 positive path | ACCEPTED — retro rubric is the control |
| BS-07 | **Finite denylists** — GUI_TOOLS and SECRET_PATTERNS cannot enumerate the world; the R1/R8 prose is the rule, the validator is a tripwire. | README caveats; pre-release retro cycle-4 | MITIGATED — pattern set extended 2026-06-10 (Anthropic/OpenAI/Google/GitLab/npm token formats) |
| BS-08 | **Gated-mode evasion via omitted approval artifact** — a run that echoes `Mode: gated`, executes tasks, and never writes an `Approved:` line validated CLEAN (check only fired when the line existed). Demonstrated by live exploit 2026-06-10 (`validate.py --run` on a synthetic gated run → "CLEAN — no violations"). 2nd observation of the cycle-4 family (FAILURE_LOG). | This review | PROMOTION QUEUED — candidate edit per FAILURE_LOG: `Mode:` echo in Scope & method + validator gate (campaign 2) |
| BS-09 | **Run completeness is unknowable** — `--run` passes a docs/ directory with no HANDOFF.md (legitimate for mid-flight runs), so a "finished" run that skipped Phase 5 also validates clean. | This review | ACCEPTED — documented in evals/README + rules.json P5 note; completed-run reviews must confirm HANDOFF.md exists |
| BS-10 | **Registry/fixture/baseline drift** — nothing read rules.json: a rule could reference a deleted fixture (or a fixture could sit unregistered) and the suite stayed green. Demonstrated 2026-06-10: `grep -c rules.json evals/*.py evals/*.sh` → 0. | This review | CLOSED — `validate.py --all` now cross-checks rules.json ↔ fixtures/ both directions and fails on drift |
| BS-11 | **Version-reference drift** — AUDIT.md title, package.json, baseline.json, README, and index.html each carry a version with no consistency check; observed in the wild (package.json said 2.1.1 while its lockfile said 1.0.0 pre-release). | This review | MITIGATED — `run-evals.sh --record` refuses to pin a baseline when AUDIT.md and package.json versions disagree |

**Watchlist (not blind spots — nothing is unseen, kept for completeness):**
Phase 4 stop rule (b) cannot fire before (a) at small LOOP_BUDGET — harmless
overlap, wording cost exceeds benefit (pre-release retro cycle-4).

**Review cadence:** re-verify this register at every campaign start and
whenever validate.py changes. Adding a blind spot here requires the same
evidence bar as a FAILURE_LOG row.
