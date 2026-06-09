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

## v2.1.1 — 2026-06-10 (improvement cycle 3)

- **PATCH: One escape-hatch vocabulary everywhere.** Phase 5's metric Status set is now exactly `MEASURED / UNMEASURED / NOT-APPLICABLE` — the same closed set R1 defines. Previously Phase 5 said `N-A`, so an agent following R1 verbatim produced a "violation" in a fully honest handoff.
- **Trigger:** Critic cycle 3 (High) — queued from cycle-2 retro. False violations on compliant runs erode trust in the gate; two vocabularies for one concept also wastes instruction budget.
- **Harness:** `METRIC_STATUSES` updated to match; new trap fixture `B13-bad-metric-status` (Status `ESTIMATED` — fabrication-adjacent wording) closes the declared coverage gap on `HANDOFF-BAD-MSTATUS`. Evals: **15/15 green.**

## v2.1.0 — 2026-06-10 (improvement cycle 2)

- **MINOR: Gated-mode approval is now an artifact.** Phase 2 (gated) requires the decision to be recorded as an `Approved: <ID>, <ID>` (or `Approved: none`) line under the loop's heading; Phase 3 may execute only listed tasks, in this session or any future one.
- **Trigger:** Critic cycle 2 finding (High) — with approval living only in conversation, R4 ("the file system is your only memory") meant a resumed session could not know what was approved: gated mode silently degraded to autonomous across sessions. Concrete violation of the protocol's one human-control guarantee (v1's `status: APPROVED` provided this; v2.0.0 dropped it in the rewrite).
- **Harness:** new invariant `GATED-UNAPPROVED-EXEC` + trap fixture `B12-gated-unapproved-exec`; `G01-clean-run` strengthened to exercise the positive approved path. Evals: **14/14 green.**

## v2.0.1 — 2026-06-10 (improvement cycle 1)

- **PATCH: Evidence must be row-traceable.** Phase 2 and Phase 5 templates now require each measured metric's fenced output block to open with the literal line `$ <verify command>`. Previously an agent could paste ONE output block while claiming N "measured" rows — partial fabrication that satisfied the letter of R1.
- **Trigger:** Critic cycle 1 finding (High) — concrete exploit demonstrable against v2.0.0 wording; eval gap confirmed (B01 trapped *zero* blocks but not *under-provisioned* blocks).
- **Harness:** new violation `R1-UNLINKED-OUTPUT` + trap fixture `B11-unlinked-output`. Bring-up exposed and fixed a validator bug (`norm()` stripped `*` inside shell commands, breaking command↔output matching on B07). Evals: **13/13 green.**

## v2.0.0 — 2026-06-10

- **MAJOR: Complete rewrite from first principles** (research-backed re-engineering report, June 2026). Replaces the v1.x monolith (~150 KB, 1,898 lines, 40+ registered rules) with a ~160-line protocol: one-sentence role, per-project CONFIG block, 8 core rules, 6-phase state machine.
- **Trigger:** Four documented production failure modes of v1-style prompts:
  1. Reward-hacking the "empirical truth" rule (metrics "verified via static code analysis", GUI profilers listed as CLI commands) → fixed by **R1** verbatim-output evidence gate + `UNMEASURED`/`NOT-APPLICABLE` escape hatch.
  2. Fabricated/uncited SOTA targets (irrelevant big-name comparators, non-numeric "targets") → fixed by **R2** honest-targets gate.
  3. Perverse finding quotas ("fewer than 5 issues = failure") manufacturing noise on clean codebases → fixed by **R7** severity-weighted findings with a valid "no significant findings" outcome.
  4. Unreachable "match SOTA Top 5" exit condition causing arbitrary stops → fixed by **Phase 4** diminishing-returns stop rule + `LOOP_BUDGET`.
  Plus persona inflation → one-sentence role.
- **Carried forward from v1 (proven in production):** file-based memory and idempotent resume (R4), one-task micro-loop (R5), 3-strike circuit breaker with revert + root cause (R6), atomic commits, handoff document, secrets redaction (now **R8**, validated by v1 fixture F005), and the human-in-the-loop approval gate (now `MODE: gated`).
- **Research basis (selected):** IFScale / "curse of instructions" (arXiv 2507.11538, 2509.21051) — instruction-following decays with rule count, with bias toward earlier instructions; Anthropic *Effective harnesses for long-running agents*; Claude Code best practices ("show evidence — the command it ran and what it returned"); specification-gaming literature (Krakovna et al. 2020; arXiv 2604.15149, 2603.11337).
- v1 history (the 150 KB spec, its 8 fixtures, rule registry, and PE rubric) is preserved in git history prior to this commit.
