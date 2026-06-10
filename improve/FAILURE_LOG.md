# Failure log

Maps recurring failures to candidate edits. **Promote a fix only after the
failure recurs** (Rule of Three: 1st time = note it, 2nd time = candidate edit,
promoted = new version via `improve/CRITIC.md`). One row per observation.

> Version ids below the public 1.0.0 release ("v1 era", v2.0.0–v2.1.1) are
> internal pre-release identifiers; that lineage lives in git history. Rows are
> historical records and are never renumbered.

| Date | Project / run | Failure observed | Retro item | Seen before? | Candidate edit | Promoted to version? |
|------|---------------|------------------|-----------|--------------|----------------|----------------------|
| 2026-04 (v1 era) | Qi Men metaphysics app | Benchmarked vs Palantir/IBM Watsonx with no relevant public benchmark | #2 | 2nd time | Honest-targets gate with URL-or-INTERNAL rule | v2.0.0 (R2) |
| 2026-04 (v1 era) | React/Three.js app | "React Profiler" listed as a CLI verify command; metrics "verified via static code analysis" | #1 | 2nd time | Verbatim-output evidence gate; GUI tools banned in Verify column | v2.0.0 (R1) |
| 2026-04 (v1 era) | Small/clean repo | Low-value findings manufactured to satisfy "5 issues per loop" quota | #3 | 2nd time | Severity-weighted findings; "no significant findings" is a valid outcome | v2.0.0 (R7) |
| 2026-04 (v1 era) | All 4 runs | Stopped arbitrarily at loop 1–2 because "match SOTA Top 5" exit was unreachable | #4 | 4th time | Diminishing-returns stop rule + LOOP_BUDGET | v2.0.0 (Phase 4) |
| 2026-06-10 | Critic cycle 1 (this repo) | One fenced output block can "cover" N measured rows — partial fabrication passes R1's letter | #1 | Variant of v1 failure #1 (2nd occurrence of the family) | Require `$ <verify command>` opener per measured metric | v2.0.1 (R1 templates) |
| 2026-06-10 | Critic cycle 2 (this repo) | Gated approval lives only in conversation → resumed sessions can't honor it (gate degrades to autonomous) | #7 | v1 had `status: APPROVED`; regression introduced by v2.0.0 rewrite | `Approved:` line artifact + Phase 3 restriction | v2.1.0 (Phase 2/3) |
| 2026-06-10 | Critic cycle 3 (this repo) | R1 says NOT-APPLICABLE, Phase 5 said N-A → compliant runs flagged as violations | #6 | Queued in cycle-2 retro (2nd observation of vocabulary drift) | Single closed status set across R1 and Phase 5 | v2.1.1 (Phase 5) |
| 2026-06-10 | Critic cycle 4 (this repo) | Run artifacts don't state their MODE — post-hoc audit can't distinguish autonomous from gate-skipping | #7 | 1st observation — NOT promoted (Rule of Three) | Echo `Mode:` in the Scope & method line if it recurs | pending recurrence |
| 2026-06-10 | Ownership review / blind-spot audit (this repo) | Even with `Mode: gated` echoed, a run that executes tasks and never writes an `Approved:` line validates CLEAN — the v2.1.0-era check fired only when the line existed (live exploit: synthetic gated run → "CLEAN — no violations"; see improve/BLINDSPOTS.md BS-08) | #7 | 2nd observation of the cycle-4 family | Echo `Mode:` in Scope & method; validator flags gated loop sections with executed tasks and no `Approved:` line | pending (campaign 2) |
