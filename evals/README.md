# evals/ — regression gate for AUDIT.md

Every change to `AUDIT.md` must keep this suite green. The harness validates
**agent outputs** (a run's `docs/BACKLOG.md` + `docs/HANDOFF.md`) against the
machine-checkable subset of the protocol's rules, and proves each rule is
**load-bearing** by fault injection: every `B*` fixture plants exactly one
violation, and the validator must catch exactly that violation — no more, no
less. A trap that stops tripping means a rule has silently died.

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
python3 evals/validate.py --all          # full suite, human output
python3 evals/validate.py --all --json   # machine-readable
./evals/run-evals.sh --record            # run + pin baseline to current AUDIT.md
python3 evals/validate.py --run <dir>    # validate a real run's docs/ output
```

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

3. For `expect: fail`, the validator must report **exactly** `expected_violations` — plant one fault per fixture.
4. Register the fixture in `rules.json` under the rule(s) it exercises.
5. Run `./evals/run-evals.sh --record`.

## What the validator cannot see (declared gaps)

- Whether code changes were genuinely valuable (retro item 9 — human judgment).
- Whether findings were padded (retro item 3 — judgment; the validator only guarantees padding is never *required*).
- Live-agent properties: actual command execution, 3-strike counting, resume behavior (R4). For hard guarantees on those, use deterministic hooks/CI in the target repo, not prompt text.
