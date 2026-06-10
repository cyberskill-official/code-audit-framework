# AUDIT.md — an honest, self-improving audit protocol for AI coding agents

**AUDIT.md** is a ~160-line, AI-agnostic master prompt that turns any coding agent
(Claude Code, Cursor, Gemini CLI, Codex CLI, Windsurf, …) into a rigorous,
evidence-based codebase auditor that works in loops across multiple sessions —
and **ships with the machinery to improve its own prompt over time**: a
versioned changelog, a retrospective rubric, a failure log, an LLM-as-critic
cycle, and a deterministic regression harness that blocks any change that
weakens a rule.

> Visitor-friendly tour: open [`index.html`](./index.html) in a browser.
> Built by [CyberSkill](https://cyberskill.world) — *Turn Your Will Into Real*.

| | |
|---|---|
| Protocol | [`AUDIT.md`](./AUDIT.md) — current release **v1.2.0** |
| History | [`CHANGELOG.md`](./CHANGELOG.md) · immutable copies in [`improve/versions/`](./improve/versions/) |
| Self-improvement | [`improve/CRITIC.md`](./improve/CRITIC.md) — one evidenced change per cycle |
| Regression gate | [`evals/`](./evals/) — **24 fixtures, 24/24 green** at v1.2.0, stdlib-only Python; enforced in CI on every push |
| For agents | [`AGENTS.md`](./AGENTS.md) — machine-facing operating rules for this repo |
| License | [Apache-2.0](./LICENSE) · [`CONTRIBUTING.md`](./CONTRIBUTING.md) · [`SECURITY.md`](./SECURITY.md) |

---

## Why it looks like this (the 60-second story)

The first internal version of this project was a 150 KB, 1,898-line mega-prompt
with 40+ registered rules. It worked — but four production runs surfaced five
failure modes that research says are *structural*, not accidental:

| Observed failure | Root cause | The fix |
|---|---|---|
| Metrics "verified via static code analysis"; GUI profilers cited as CLI commands | "No script = no metric" gave the agent no honest way out, so it fabricated | **R1** — verbatim command + output required, or `UNMEASURED (reason)`; each measured metric traceable to `$ <verify command>` |
| Benchmarked a metaphysics app against Palantir & IBM Watsonx | Mandatory "research Top-5 SOTA" forces the *format* of research even when no comparator exists | **R2** — every target is cited-with-URL **or** labeled `INTERNAL TARGET`; "No external benchmark applicable" is a valid answer |
| Trivial findings invented to satisfy "≥5 issues per loop" | A count quota is an objective the agent optimizes | **R7** — severity-weighted findings; "no significant findings" is a **successful** outcome |
| All runs stopped arbitrarily at loop 1–2 | "Terminate only when ALL metrics match SOTA Top 5" is unreachable, so the agent stopped on a vibe | **Phase 4** — diminishing-returns stop rule + `LOOP_BUDGET` safety net |
| "Elite agent, immune to laziness and hallucination" | Persona inflation burns the finite instruction budget | One-sentence role |

The deeper principle (IFScale, arXiv 2507.11538; "curse of instructions",
arXiv 2509.21051): instruction-following decays measurably as instruction count
grows, with bias toward earlier instructions. **Every non-essential rule lowers
compliance with the essential ones.** The protocol is short on purpose, and the
critical rules come first on purpose.

---

## Quickstart for humans (manual mode)

**1. Copy the protocol into your target repo:**

```bash
curl -O https://raw.githubusercontent.com/cyberskill-official/code-audit-framework/main/AUDIT.md
# or just copy the AUDIT.md file into your repo root
```

**2. Edit the CONFIG block at the top of `AUDIT.md`.** It is the only part you
ever change per project:

```text
PROJECT_PATH:    ./
TECH_STACK:      Python 3.12 / FastAPI / Postgres
PROJECT_PURPOSE: Internal invoicing API for the finance team
MODE:            gated          ← gated = you approve tasks before execution
LOOP_BUDGET:     3
DEPTH:           standard
SEVERITY_FLOOR:  High
PROTECTED_AREAS: src/billing/, public API contract
RUN_COMMANDS:    pytest -q; ruff check .
DOMAIN_NOTES:    PDPL — no customer data in logs
BENCHMARK_MODE:  auto
COMPARATORS:     (blank)
```

**3. Paste the whole file into your agent** (or point the agent at it):

> "Read AUDIT.md and execute it. Begin at PHASE 0."

**4. What happens next (gated mode — the default):**

1. The agent recovers state (`git log`, `docs/BACKLOG.md`), scopes the audit, and measures real baselines (Phase 0–1).
2. It writes a backlog section — benchmark table + severity-tagged task table — then **stops and asks you to review** (Phase 2).
3. You approve by writing one line under the loop heading: `Approved: L1-T1, L1-T3` (or `Approved: none`). The approval is a file artifact, so it survives across sessions.
4. The agent executes approved tasks one at a time — implement, re-run the task's verify command, paste raw output, atomic commit (Phase 3). Three failed validations = revert + `BLOCKED` with a root cause (R6).
5. It loops deeper until a stop condition fires (Phase 4), then writes `docs/HANDOFF.md` with metrics, deltas, debt, and an exact resume protocol (Phase 5).

Set `MODE: autonomous` to skip the approval pause (good for CI or sandboxed
repos). Everything else is identical.

**5. Resuming later** — just run the same instruction again. R4 makes resumes
idempotent: the agent reads `docs/BACKLOG.md` + `git log` and continues where
it stopped. Never restarts finished work.

**6. Optionally validate the run's honesty mechanically:**

```bash
python3 evals/validate.py --run /path/to/target-repo   # checks its docs/ output
```

---

## Quickstart for automated mode (scripted / headless runs)

Automated mode means **you** launch the run from a script, a cron job, or CI —
no chat session, no human in the loop until the handoff. The protocol is
model-agnostic: the same two steps work with any coding agent that has a
non-interactive (headless) mode and your API credentials in its environment.

**1. Prepare the target repo once** — copy `AUDIT.md` in, fill CONFIG, and set
`MODE: autonomous` (this is what removes the Phase 2 approval pause; everything
else is identical to manual mode):

```bash
cd /path/to/target-repo
curl -O https://raw.githubusercontent.com/cyberskill-official/code-audit-framework/main/AUDIT.md
$EDITOR AUDIT.md     # fill CONFIG; set MODE: autonomous
```

Leave `MODE: gated` instead if you want scripted runs that still stop for a
human `Approved:` line — the approval is a file artifact, so a teammate can
grant it hours later and the next scheduled run picks it up (R4).

**2. Trigger the agent headlessly with one kickoff prompt.** The prompt is the
same everywhere: `Read AUDIT.md and execute it. Begin at PHASE 0.`

```bash
# Claude Code (ANTHROPIC_API_KEY in env)
claude -p "Read AUDIT.md and execute it. Begin at PHASE 0."

# OpenAI Codex CLI (OPENAI_API_KEY in env)
codex exec "Read AUDIT.md and execute it. Begin at PHASE 0."

# Gemini CLI (GEMINI_API_KEY in env)
gemini -p "Read AUDIT.md and execute it. Begin at PHASE 0."
```

(Headless flag names are current as of this writing — check your CLI's
`--help`. Any agent that can read files and run shell commands qualifies.)

**3. Gate the output mechanically.** The run's artifacts are designed to be
machine-checked — fabricated measurements, uncited targets, gate-skips and
leaked secrets are detectable from the files alone:

```bash
python3 evals/validate.py --run /path/to/target-repo              # exit 1 on violations
python3 evals/validate.py --run /path/to/target-repo --report json  # findings for dashboards
```

In CI, run step 2 on a schedule and make step 3 the job's pass/fail — or use
the GitHub Action below. Re-running the same kickoff prompt resumes idempotently
(R4): state lives in `docs/BACKLOG.md`, not in the conversation.

**No clone needed — two distribution channels for step 3:**

```bash
# From PyPI (https://pypi.org/project/code-audit-validator/):
pipx install code-audit-validator          # or: uvx code-audit-validate --run .
code-audit-validate --run . --report json

# Or straight from the repo (@v1 = floating major tag; pin a release tag for immutability):
uvx --from git+https://github.com/cyberskill-official/code-audit-framework@v1 \
    code-audit-validate --run . --report json
```

```yaml
# In the TARGET repo's workflow — gates the audit artifacts on every push
- uses: cyberskill-official/code-audit-framework@v1
  with:
    path: .
    report: json   # optional; also writes audit-report.json
```

(The packaged entry point covers `--run`/`--report`; the fixture suite
`--all` stays repo-only, since fixtures ship with the repo, not the wheel.)

**Improving the protocol itself, scripted the same way** (Job B in
[`AGENTS.md`](./AGENTS.md) — the file agents are pointed at once they're
running in *this* repo):

```bash
claude -p "Run one improvement cycle per improve/CRITIC.md."
```

Hard invariants either job is held to: never edit `improve/versions/*`; never
weaken a fixture; `python3 evals/validate.py --all` green before any protocol
change is done.

---

## Tool-specific notes

| Tool | How to wire it |
|---|---|
| **Claude Code** | Paste `AUDIT.md` as the task, or put the CONFIG + a pointer in `CLAUDE.md` (auto-read every session). For hard guarantees (R1 evidence, R3 protection) add a PostToolUse/Stop **hook** — prompt text is advisory, hooks are deterministic. |
| **Cursor** | Root `AGENTS.md` is supported; or `.cursor/rules/audit-protocol.mdc`. Keep always-on content under ~200 words to avoid the token tax; let the rest load on demand. |
| **Gemini CLI** | Put the protocol in `GEMINI.md` (project) and stable parts in `~/.gemini/GEMINI.md`; `/memory refresh` after edits. |
| **Codex CLI** | `AGENTS.md` is auto-injected. Add an explicit persistence line ("persist until all OPEN tasks ≥ SEVERITY_FLOOR are DONE or BLOCKED this loop") — GPT-5.x models may otherwise end early. |
| **Windsurf / OpenHands / others** | Use `AGENTS.md` (Linux-Foundation-stewarded convention, adopted by 60k+ projects). Only the context-file name changes; the protocol itself relies on nothing but a shell, git, and file I/O. |

---

## The self-improvement loop

The prompt is treated like production software: versioned, changelogged,
regression-tested, and changed only with evidence.

```
        run AUDIT.md on a project
                  │
                  ▼
   improve/RETROSPECTIVE.md  ──  10 questions, /20 score, ~10 minutes
                  │
   score < 16 or repeat failure?
                  │ yes                          no → stop tuning (stability
                  ▼                                   is the goal)
   improve/FAILURE_LOG.md    ──  log it; promote only on recurrence
                  │                              (Rule of Three)
                  ▼
   improve/CRITIC.md         ──  ONE minimal change; PATCH/MINOR/MAJOR
                  │
                  ▼
   evals/validate.py --all   ──  24 fixtures must stay green
                  │
                  ▼
   CHANGELOG.md + improve/versions/AUDIT-vX.Y.Z.md  (immutable release)
```

There is **no lifetime cap on cycles** — only per-campaign stop rules
(2 consecutive zero-High cycles, or all failures promoted/deferred), the same
diminishing-returns logic the protocol applies to codebases. The protocol has
already been run on itself; the pre-release hardening campaign (2026-06-10,
5 cycles) produced:

| Cycle | One change | Evals |
|---|---|---|
| 1 | Evidence must be row-traceable: each measured metric's output block opens with `$ <verify command>` (closed a partial-fabrication exploit) | 13/13 |
| 2 | Gated approval became a durable `Approved:` artifact (restored the human-control guarantee the rewrite had dropped) | 14/14 |
| 3 | One escape-hatch vocabulary across R1 and Phase 5 (compliant runs were flagged as violations) | 15/15 |
| 4–5 | Zero findings ≥ High, twice → campaign stop (a) | 15/15 |

Campaign 2 (2026-06-10, after the move to CyberSkill ownership) opened with a
full blind-spot review — the seven declared harness blind spots re-verified and
four new ones registered ([`improve/BLINDSPOTS.md`](./improve/BLINDSPOTS.md)) —
and ran one cycle: **v1.1.0** echoes `Mode:` in every backlog, closing a
demonstrated gated-mode evasion (BS-08). Evals: 16/16. Stop condition (c):
fixed cycle count requested by the maintainer.

Campaign 3 (2026-06-10, production-readiness pass) re-verified the register,
adopted a structural review as its evidence base, and landed the hardening that
makes the suite trustworthy on hostile output: a template-conformance
meta-tripwire (non-template output can no longer silently escape every check —
BS-12), a CONFIG preflight with `PROTECTED_AREAS` auto-load (BS-13), a
precision fixture pack (G:B ratio 2:14 → 6:18), structured findings export
(`--report json|sarif`), a retro-score aggregator, and the CI gate. One
protocol change: **v1.2.0** — Phase 0 now STOPs on placeholder or out-of-set
CONFIG instead of letting the agent improvise it. Evals: 24/24. Stop condition
(b): every failure-log row promoted or explicitly deferred.

Full evidence trail: [`CHANGELOG.md`](./CHANGELOG.md),
[`improve/FAILURE_LOG.md`](./improve/FAILURE_LOG.md),
[`improve/BLINDSPOTS.md`](./improve/BLINDSPOTS.md),
[`improve/retros/`](./improve/retros/).

---

## The regression harness

```bash
python3 evals/validate.py --all      # 24 fixtures: G* must pass, B* must trip
./evals/run-evals.sh --record        # run + pin baseline.json to AUDIT.md's sha256
python3 evals/validate.py --run DIR  # validate any real run's docs/ output
python3 evals/validate.py --run DIR --report json   # structured findings export (or: sarif)
```

Zero dependencies (Python stdlib). Each `B*` fixture is a **fault-injection
trap**: it plants exactly one violation (a fabricated metric, an uncited SOTA
target, a leaked AWS key, an unapproved execution, …) and the validator must
report exactly that violation. A trap that stops tripping means a rule has
silently died — that is what blocks a bad prompt edit. Details:
[`evals/README.md`](./evals/README.md). What the validator *cannot* see
(judgment calls, live-agent behavior) is declared honestly in
[`evals/rules.json`](./evals/rules.json) coverage notes.

---

## Repo layout

```
AUDIT.md                 ← the product: the protocol (current release)
README.md                ← you are here
AGENTS.md                ← operating rules for AI agents working on this repo
CHANGELOG.md             ← one change per version, every change evidenced
index.html               ← visitor-facing product page (CyberSkill design system)
assets/                  ← logo, analytics bundle
improve/
  CRITIC.md              ← the self-improvement cycle (meta-prompt)
  RETROSPECTIVE.md       ← 10-question post-run rubric (/20)
  FAILURE_LOG.md         ← failures → candidate edits → promotions
  BLINDSPOTS.md          ← register of what the harness cannot see (+ status)
  versions/              ← immutable released versions (v1.0.0 …)
  retros/                ← filled retrospectives (pre-release cycles 1–5 included)
evals/
  validate.py            ← deterministic conformance checker (stdlib only)
  fixtures/              ← G* compliant runs + B* fault-injection traps (16)
  rules.json             ← rule → AUDIT.md anchor → fixtures (+ honest gaps)
  baseline.json          ← last green matrix, pinned to AUDIT.md sha256
  run-evals.sh           ← runner; --record refreshes the baseline
```

---

## Design principles (and their sources)

1. **Tightness is a feature.** Instruction-following degrades with rule count and favors earlier rules — IFScale (arXiv 2507.11538), ManyIFEval (arXiv 2509.21051). The protocol stays under 200 lines, critical rules first, and every addition must "pay" by trimming something.
2. **Evidence over assertion.** Show the command and its raw output, or say `UNMEASURED` — Claude Code best practices; verifier-gaming research (arXiv 2604.15149) shows weak checks *induce* shortcut strategies.
3. **Files are memory.** Initializer + incremental sessions + artifacts for the next session — Anthropic, *Effective harnesses for long-running agents*.
4. **Stops must be reachable.** Iteration caps as safety net, diminishing returns as signal; "done" defined per loop, never against an unreachable absolute.
5. **Honest outcomes beat impressive ones.** "No significant findings" and "No external benchmark applicable" are first-class results. Quotas manufacture noise (specification gaming — Krakovna et al., 2020).
6. **Prompt text is advisory; gates are deterministic.** ~80% adherence is the realistic ceiling for context-file guidance. Anything you cannot tolerate being skipped belongs in hooks/CI — here, that is `evals/validate.py`.

---

## Caveats

- **Prompt compliance is probabilistic.** Even this protocol is advisory to the agent running it. The eval harness catches dishonest *artifacts*; it cannot force honest *behavior* mid-run. For non-negotiables, use deterministic hooks in your own CI.
- **The validator is a tripwire, not a proof.** Denylists (GUI tools, secret patterns) are finite; substring matching can false-positive on prose. Known limits are documented in `evals/rules.json` and `improve/retros/2026-06-10-cycle-4.md`.
- **Harnesses go stale as models improve.** Re-examine the CORE RULES every few model generations; scaffolding that helps today may be dead weight tomorrow.
- **Small evidence base.** The redesign is grounded in 4 documented production runs plus published research; its effectiveness is validated continuously through the retrospective system — that's what the loop is for.

---

## About

Built and maintained by **CyberSkill** — software solutions consultancy and
development, Ho Chi Minh City, Vietnam. We build AI-first engineering systems
for clients globally. *Turn Your Will Into Real — Hiện Thực Hoá Ý Chí.*

Partnerships & client work: **info@cyberskill.world** · Product feedback: open
an issue. If AUDIT.md saved you a review cycle, you can
[buy a fine-tune cycle ☕](https://buymeacoffee.com/zintaen).
