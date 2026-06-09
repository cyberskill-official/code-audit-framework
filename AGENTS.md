# AGENTS.md — operating rules for AI agents in this repository

This repo ships AUDIT.md, an agent audit protocol, plus the machinery that
improves it. You are either auditing a TARGET repo with it, or improving the
protocol itself. Identify which job you were given before acting.

## Job A — run the auditor on a target repo
1. Read `AUDIT.md` fully. Fill its CONFIG block from the user's answers;
   default to `MODE: gated` unless told otherwise.
2. Execute from PHASE 0 in the TARGET repo. Your only writes there are
   `docs/BACKLOG.md`, `docs/HANDOFF.md`, and approved task implementations.
3. Honesty gates you will be held to: every measured metric needs the literal
   command + raw output (R1); targets are cited-with-URL or `INTERNAL TARGET`
   (R2); statuses come from closed sets (R5); secrets are `[REDACTED:<kind>]`
   (R8). `python3 evals/validate.py --run <target>` checks your artifacts.

## Job B — improve the protocol (self-improvement cycle)
Follow `improve/CRITIC.md` step by step. Summary of its non-negotiables:
- ONE protocol change per cycle/version. Cite a trigger (failure-log row,
  retro item, or eval gap). Speculative edits are rejected.
- New rules require a recurred failure (Rule of Three). PATCH-level clarity
  fixes may proceed on first concrete evidence.
- Gate: `python3 evals/validate.py --all` green BEFORE release. If your change
  is testable, add/extend a fixture in the SAME cycle and register it in
  `evals/rules.json`.
- Release: bump version in AUDIT.md's title line → copy to
  `improve/versions/AUDIT-v<x.y.z>.md` → CHANGELOG.md entry → retro in
  `improve/retros/`.
- Campaign stop: 2 consecutive cycles with zero findings >= High. No lifetime
  cap on future campaigns.

## Hard invariants (both jobs — violating these is never acceptable)
- Never edit or delete anything in `improve/versions/` (immutable history).
- Never weaken, delete, or "adjust" an eval fixture to make a change pass.
  If a fixture is genuinely wrong, fixing it IS the cycle's one change.
- Never hand-edit `evals/baseline.json`; use `./evals/run-evals.sh --record`.
- Never remove failure-log rows; mark them promoted/deferred.
- Never commit secrets; this repo's outputs must satisfy R8 like any other.
- `docs/` in THIS repo is gitignored scratch (self-run output) — do not fight
  the gitignore.

## Verification commands
```bash
python3 evals/validate.py --all     # full regression suite (must be ALL GREEN)
./evals/run-evals.sh --record       # suite + pin baseline to AUDIT.md sha256
python3 -c "import json;b=json.load(open('evals/baseline.json'));print(b['audit_md_version'],b['all_ok'])"
```

## File map
`AUDIT.md` protocol (current) · `CHANGELOG.md` history · `improve/` the loop
(CRITIC, RETROSPECTIVE, FAILURE_LOG, versions/, retros/) · `evals/` regression
gate (validate.py, fixtures/, rules.json, baseline.json) · `index.html` +
`assets/` product page (CyberSkill design system; tokens documented inline).
