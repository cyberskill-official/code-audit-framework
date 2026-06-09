#!/usr/bin/env python3
"""validate.py — deterministic conformance checker for AUDIT.md outputs.

Checks a run's docs/ directory (BACKLOG.md + HANDOFF.md) against the
machine-checkable subset of AUDIT.md's core rules:

  R1-NO-OUTPUT       measured baseline/metric without a verbatim fenced output block
  R1-UNLINKED-OUTPUT measured row whose verify command appears in no fenced block
  R1-NO-REASON       UNMEASURED / NOT-APPLICABLE without a (reason)
  R1-GUI-TOOL        GUI tool (profiler/inspector/devtools) used as a Verify command
  R2-UNCITED         target is neither cited-with-URL nor labeled INTERNAL / N-A
  R2-NONNUMERIC      banned non-numeric target word (Minimal / High / Strict / ...)
  R3-PROTECTED       DONE task references a path under protected_areas
  R5-BAD-STATUS      task status outside { OPEN, IN-PROGRESS, DONE, BLOCKED }
  R5-BAD-SEV         severity outside { Critical, High, Medium, Low }
  R5-BAD-ID          task ID not matching L<loop>-T<n>
  R6-NO-ROOTCAUSE    BLOCKED task without a "Root cause:" note
  R8-SECRET          unredacted credential pattern in any output file
  P5-NO-STOP-REASON  HANDOFF.md does not cite which stop condition fired
  HANDOFF-BAD-MSTATUS  metrics Status outside the closed metric-status set
  GATED-UNAPPROVED-EXEC  executed task not on the loop's `Approved:` line (gated mode)

A loop with zero findings is VALID (R7): absence of tasks is never a violation.

Usage:
  python3 evals/validate.py --run <dir-containing-docs>  [--protected p1,p2]
  python3 evals/validate.py --all          # run every fixture, compare to expectations
  python3 evals/validate.py --all --json   # machine-readable results

Exit codes: 0 = all good; 1 = violations / fixture mismatch; 2 = usage error.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

TASK_STATUSES = {"OPEN", "IN-PROGRESS", "DONE", "BLOCKED"}
SEVERITIES = {"Critical", "High", "Medium", "Low"}
METRIC_STATUSES = {"MEASURED", "UNMEASURED", "NOT-APPLICABLE"}
ID_RE = re.compile(r"^L\d+-T\d+$")

GUI_TOOLS = [
    "react profiler", "react devtools", "chrome devtools", "devtools",
    "browser inspector", "web inspector", "xcode instruments", "instruments.app",
    "lighthouse panel", "performance tab", "network tab", "profiler tab",
]

SECRET_PATTERNS = [
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("stripe-key", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    ("slack-token", re.compile(r"\bxox[bpoas]-[0-9A-Za-z-]{10,}\b")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
]

BANNED_TARGET_WORDS = {
    "minimal", "high", "strict", "low", "medium", "fast", "slow", "good",
    "great", "optimal", "best-in-class", "world-class", "enterprise-grade",
}

UNMEASURED_RE = re.compile(r"\b(UNMEASURED|NOT-APPLICABLE)\b")
REASONED_RE = re.compile(r"\b(?:UNMEASURED|NOT-APPLICABLE)\s*\([^)]+\)")
URL_RE = re.compile(r"https?://\S+")
STOP_RE = re.compile(r"Stop condition:\s*\(?[abc]\)?", re.IGNORECASE)


def norm(cell: str) -> str:
    """Strip markdown wrapping without mangling shell syntax: backticks go
    everywhere, but * and _ are stripped only at the edges (emphasis), so
    commands like `wc -l src/*.py` survive intact."""
    s = cell.strip().replace("`", "")
    return re.sub(r"^[*_]+|[*_]+$", "", s).strip()


def parse_tables(text: str):
    """Yield (header_cells, rows, end_line_idx) for every markdown table."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            header = [norm(c) for c in line.strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = [norm(c) for c in lines[j].strip().strip("|").split("|")]
                if any(cells):
                    rows.append(cells)
                j += 1
            yield header, rows, j
            i = j
        else:
            i += 1


def section_fences(text: str, after_line: int):
    """Contents of fenced code blocks between after_line and the next heading."""
    lines = text.splitlines()
    fences, current, inside = [], [], False
    for line in lines[after_line:]:
        if not inside and re.match(r"^#{1,3}\s", line):
            break
        if line.strip().startswith("```"):
            if inside:
                fences.append("\n".join(current))
                current = []
            inside = not inside
            continue
        if inside:
            current.append(line)
    return fences


def col(header, *names):
    """Index of first header cell containing any of names (case-insensitive)."""
    low = [h.lower() for h in header]
    for n in names:
        for i, h in enumerate(low):
            if n in h:
                return i
    return None


def check_benchmark_like_table(header, rows, end_idx, text, violations, src, is_handoff):
    mi = col(header, "metric")
    bi = col(header, "baseline")
    ti = col(header, "target")
    vi = col(header, "verify")
    si = col(header, "status")
    if mi is None or bi is None:
        return
    has_measured_row = False
    measured_rows = []  # (metric, verify) pairs claiming a measurement
    for r in rows:
        def cell(ix):
            return r[ix] if ix is not None and ix < len(r) else ""
        baseline, target, verify = cell(bi), cell(ti), cell(vi)
        # R1 — escape hatch must carry a reason
        for v in (baseline, cell(si) if is_handoff else ""):
            if UNMEASURED_RE.search(v) and not REASONED_RE.search(v):
                # In HANDOFF the reason may live in the Baseline/Final cells; only
                # flag the cell that itself claims UNMEASURED without any reason nearby.
                if not REASONED_RE.search(" ".join(r)):
                    violations.append((f"R1-NO-REASON", src, f"'{v}' lacks (reason): row {r[:2]}"))
        # Which rows claim a measurement?
        if is_handoff:
            status = cell(si)
            if status and status not in METRIC_STATUSES:
                violations.append(("HANDOFF-BAD-MSTATUS", src, f"Status '{status}' not in {sorted(METRIC_STATUSES)}"))
            if status == "MEASURED":
                has_measured_row = True
                measured_rows.append((cell(mi), verify))
        else:
            if baseline and not UNMEASURED_RE.search(baseline):
                has_measured_row = True
                measured_rows.append((cell(mi), verify))
        # R2 — honest targets
        if ti is not None and target:
            t = target.strip()
            t_low = t.lower().rstrip(".")
            if t_low in BANNED_TARGET_WORDS:
                violations.append(("R2-NONNUMERIC", src, f"banned non-numeric target '{t}'"))
            elif not (
                URL_RE.search(t)
                or "internal target" in t_low
                or "no external benchmark applicable" in t_low
                or t_low in {"n-a", "n/a", "—", "-"}
            ):
                violations.append(("R2-UNCITED", src, f"target '{t}' has no URL and no INTERNAL label"))
        # R1 — GUI tools are not verification
        if verify:
            v_low = verify.lower()
            for tool in GUI_TOOLS:
                if tool in v_low:
                    violations.append(("R1-GUI-TOOL", src, f"'{verify}' is a GUI tool, not a shell command"))
                    break
    # R1 — measured rows need verbatim output nearby…
    fences = section_fences(text, end_idx)
    if has_measured_row and not fences:
        violations.append(("R1-NO-OUTPUT", src, "table has MEASURED/measured rows but no fenced raw-output block before next heading"))
    # …and each measured row must be traceable to ITS verify command
    elif fences:
        joined = "\n".join(fences)
        for metric, verify in measured_rows:
            if verify and verify not in {"—", "-", ""} and verify not in joined:
                violations.append(("R1-UNLINKED-OUTPUT", src, f"measured metric '{metric}': verify command '{verify}' appears in no fenced output block"))


def check_task_table(header, rows, violations, src, protected):
    ii = col(header, "id")
    sev_i = col(header, "sev")
    st_i = col(header, "status")
    d_i = col(header, "description")
    if ii is None or st_i is None:
        return
    for r in rows:
        def cell(ix):
            return r[ix] if ix is not None and ix < len(r) else ""
        tid, sev, status, desc = cell(ii), cell(sev_i), cell(st_i), cell(d_i)
        if tid and not ID_RE.match(tid):
            violations.append(("R5-BAD-ID", src, f"task id '{tid}' != L<loop>-T<n>"))
        if status and status not in TASK_STATUSES:
            violations.append(("R5-BAD-STATUS", src, f"status '{status}' not in {sorted(TASK_STATUSES)}"))
        if sev and sev not in SEVERITIES:
            violations.append(("R5-BAD-SEV", src, f"severity '{sev}' not in {sorted(SEVERITIES)}"))
        if status == "BLOCKED" and "root cause" not in " ".join(r).lower():
            violations.append(("R6-NO-ROOTCAUSE", src, f"BLOCKED task '{tid}' has no 'Root cause:' note"))
        if status == "DONE" and protected:
            joined = " ".join(r)
            for p in protected:
                if p and p in joined:
                    violations.append(("R3-PROTECTED", src, f"DONE task '{tid}' touches protected path '{p}'"))


APPROVED_RE = re.compile(r"^Approved:\s*(.+)$", re.MULTILINE)
EXECUTED_STATUSES = {"DONE", "IN-PROGRESS", "BLOCKED"}


def check_approvals(text, violations, src):
    """Gated-mode invariant: if a loop section carries an `Approved:`
    line, every executed task (DONE / IN-PROGRESS / BLOCKED) in that section
    must be listed on it. Sections without an Approved line are not checked
    (autonomous mode)."""
    sections = re.split(r"(?m)^## (?=Loop\b)", text)
    for sec in sections:
        m = APPROVED_RE.search(sec)
        if not m:
            continue
        raw = m.group(1).strip()
        approved = set() if raw.lower() == "none" else {norm(x) for x in raw.split(",") if x.strip()}
        for header, rows, _ in parse_tables(sec):
            ii, st_i = col(header, "id"), col(header, "status")
            if ii is None or st_i is None or col(header, "metric") is not None:
                continue
            for r in rows:
                tid = r[ii] if ii < len(r) else ""
                status = r[st_i] if st_i < len(r) else ""
                if status in EXECUTED_STATUSES and tid and tid not in approved:
                    violations.append(("GATED-UNAPPROVED-EXEC", src,
                                       f"task '{tid}' is {status} but not on this loop's Approved: line"))


def check_secrets(text, violations, src):
    for kind, pat in SECRET_PATTERNS:
        for m in pat.finditer(text):
            ctx = text[max(0, m.start() - 40):m.start()]
            if "[REDACTED:" in ctx + m.group(0):
                continue
            violations.append(("R8-SECRET", src, f"unredacted {kind} matching '{m.group(0)[:12]}…'"))


def validate_run(run_dir: Path, protected=None):
    """Validate one run directory (containing docs/BACKLOG.md, docs/HANDOFF.md)."""
    protected = protected or []
    violations = []
    docs = run_dir / "docs" if (run_dir / "docs").is_dir() else run_dir
    backlog = docs / "BACKLOG.md"
    handoff = docs / "HANDOFF.md"
    if not backlog.exists():
        violations.append(("MISSING-FILE", "docs/BACKLOG.md", "file not found"))
    if backlog.exists():
        text = backlog.read_text(encoding="utf-8")
        check_secrets(text, violations, "BACKLOG.md")
        check_approvals(text, violations, "BACKLOG.md")
        for header, rows, end in parse_tables(text):
            if col(header, "metric") is not None and col(header, "final") is None:
                check_benchmark_like_table(header, rows, end, text, violations, "BACKLOG.md", is_handoff=False)
            elif col(header, "status") is not None and col(header, "id") is not None:
                check_task_table(header, rows, violations, "BACKLOG.md", protected)
    if handoff.exists():
        text = handoff.read_text(encoding="utf-8")
        check_secrets(text, violations, "HANDOFF.md")
        if not STOP_RE.search(text):
            violations.append(("P5-NO-STOP-REASON", "HANDOFF.md", "no 'Stop condition: (a|b|c)' line"))
        for header, rows, end in parse_tables(text):
            if col(header, "metric") is not None:
                check_benchmark_like_table(header, rows, end, text, violations, "HANDOFF.md", is_handoff=(col(header, "final") is not None))
            elif col(header, "status") is not None and col(header, "id") is not None:
                check_task_table(header, rows, violations, "HANDOFF.md", protected)
    return violations


def load_fixture_meta(fdir: Path):
    """fixture.yaml is intentionally flat key: value (no YAML dependency)."""
    meta = {"id": fdir.name, "expect": "pass", "expected_violations": [], "protected_areas": [], "exercises_rules": []}
    f = fdir / "fixture.yaml"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if ":" not in line or line.startswith("#"):
                continue
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k in ("expected_violations", "protected_areas", "exercises_rules"):
                meta[k] = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
            elif k in ("id", "expect", "description"):
                meta[k] = v
    return meta


def run_all(as_json=False):
    results, ok = [], True
    fixtures = sorted(d for d in FIXTURES.iterdir() if d.is_dir())
    for fdir in fixtures:
        meta = load_fixture_meta(fdir)
        violations = validate_run(fdir, protected=meta["protected_areas"])
        codes = sorted({c for c, _, _ in violations})
        expected = sorted(set(meta["expected_violations"]))
        if meta["expect"] == "pass":
            fixture_ok = not violations
            verdict_note = "clean" if fixture_ok else f"unexpected: {codes}"
        else:  # expect: fail — the validator MUST catch exactly the planted faults
            fixture_ok = codes == expected
            verdict_note = "trapped as expected" if fixture_ok else f"expected {expected}, got {codes}"
        ok &= fixture_ok
        results.append({
            "fixture": meta["id"], "expect": meta["expect"],
            "violations": [f"{c} [{s}] {d}" for c, s, d in violations],
            "codes": codes, "ok": fixture_ok, "note": verdict_note,
        })
    summary = {"fixtures": len(results), "passed": sum(r["ok"] for r in results), "all_ok": ok, "results": results}
    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        for r in results:
            print(f"[{'PASS' if r['ok'] else 'FAIL'}] {r['fixture']:32s} expect={r['expect']:4s} → {r['note']}")
        print(f"\n{summary['passed']}/{summary['fixtures']} fixtures OK — "
              + ("ALL GREEN" if ok else "REGRESSIONS PRESENT"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="validate one run directory (containing docs/)")
    ap.add_argument("--all", action="store_true", help="run the full fixture suite")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--protected", default="", help="comma-separated protected paths")
    args = ap.parse_args()
    if args.all:
        sys.exit(run_all(as_json=args.json))
    if args.run:
        v = validate_run(Path(args.run), protected=[p for p in args.protected.split(",") if p])
        if args.json:
            print(json.dumps([{"code": c, "file": s, "detail": d} for c, s, d in v], indent=2))
        else:
            for c, s, d in v:
                print(f"VIOLATION {c} [{s}] {d}")
            print("CLEAN — no violations" if not v else f"{len(v)} violation(s)")
        sys.exit(0 if not v else 1)
    ap.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
