# evals/ — regression gate for AUDIT.md

Every change to `AUDIT.md` must keep this suite green. The harness validates
**agent outputs** (a run's `docs/BACKLOG.md` + `docs/HANDOFF.md`) against the
machine-checkable subset of the protocol's rules, and proves each rule is
**load-bearing** by fault injection: a `B*` fixture plants a known fault set
(usually exactly one; `B16` deliberately plants three to verify exact-set
reporting), and the validator must catch exactly that set — no more, no less.
A trap that stops tripping means a rule has silently died. `G*` fixtures are
the precision half: compliant-but-tricky outputs (negated prose, redaction
markers, adversarial formatting, minimal-valid) that must NOT trip anything —
the suite proves rules fire *and* don't over-fire.

Two checks make the rest load-bearing: `TEMPLATE-NONCONFORMANT` (output that
doesn't follow the Phase 2 template can no longer silently escape the other
tripwires — BS-12) and the CONFIG preflight (`CONFIG-PLACEHOLDER` /
`CONFIG-BAD-ENUM`, which also auto-loads `PROTECTED_AREAS` from the target's
AUDIT.md so R3 needs no `--protected` double entry — BS-13).

## Files

| File | Role |
|---|---|
| `validate.py` | The validator. Zero dependencies (stdlib only). |
| `fixtures/` | `G*` = compliant outputs that must pass. `B*` = fault-injection traps that must fail with declared codes. |
| `rules.json` | Rule registry: rule → AUDIT.md anchor → violation codes → fixtures proving it. Coverage gaps are declared honestly. |
| `baseline.json` | Last recorded matrix (fixture → outcome) pinned to an AUDIT.md version + sha256. |
| `run-evals.sh` | Runner; `--record` refreshes `baseline.json`. |

## Commands

```bash
python3 evals/validate.py --all                  # full suite, human output
python3 evals/validate.py --all --json           # machine-readable
./evals/run-evals.sh --record                    # run + pin baseline to current AUDIT.md
python3 evals/validate.py --run <dir>            # validate a real run's docs/ output
python3 evals/validate.py --run <dir> --report json   # structured findings export (loops, tasks, metrics, violations)
python3 evals/validate.py --run <dir> --report sarif  # GitHub code-scanning format
python3 evals/scripts/retro-summary.py           # retro scores per protocol version (did each release help?)
```

Point `--run` at the target repo root (or its `docs/`): if the target's
`AUDIT.md` is found, its CONFIG is preflighted and `PROTECTED_AREAS` is loaded
automatically; `--protected` extends it.

## Adding a fixture

1. Create `evals/fixtures/<Gnn|Bnn>-<slug>/` with `fixture.yaml` + `docs/BACKLOG.md` (and `docs/HANDOFF.md` if relevant).
2. `fixture.yaml` is flat `key: value` (no YAML library needed):

   ```yaml
   id: B11-my-trap
   description: one line
   expect: fail                  # or pass
   expected_violations: [R1-NO-OUTPUT]
   exercises_rules: [R1]
   protected_areas: []
   ```

3. For `expect: fail`, the validator must report **exactly** `expected_violations` — plant one fault per fixture unless the fixture's purpose is exact-set verification (B16). Keep `docs/BACKLOG.md` template-conformant (Mode line + tables or the R7 line) so the planted fault is the only signal; ship a near-miss `G*` sibling when adding a new rule, so precision is pinned alongside recall.
4. Register the fixture in `rules.json` under the rule(s) it exercises — `validate.py --all` fails on registry drift in either direction (BS-10).
5. Run `./evals/run-evals.sh --record`.

## What the validator cannot see (declared gaps)

The authoritative register is [`improve/BLINDSPOTS.md`](../improve/BLINDSPOTS.md)
— one row per blind spot, with status and evidence. Headlines:

- Whether code changes were genuinely valuable (retro item 9 — human judgment).
- Whether findings were padded (retro item 3 — judgment; the validator only guarantees padding is never *required*).
- Live-agent properties: actual command execution, 3-strike counting, resume behavior (R4). For hard guarantees on those, use deterministic hooks/CI in the target repo, not prompt text.
- Run completeness: `--run` accepts a docs/ directory without HANDOFF.md (legitimate mid-flight). When reviewing a run that claims to be finished, confirm HANDOFF.md exists yourself (BS-09).
