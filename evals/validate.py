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
  TEMPLATE-NONCONFORMANT BACKLOG.md does not follow the Phase 2 template, so the
                     rule tripwires above cannot see it (BLINDSPOTS BS-12)
  CONFIG-PLACEHOLDER a CONFIG value in the target's AUDIT.md still contains
                     unedited <placeholder> text (Phase 0 preflight)
  CONFIG-BAD-ENUM    MODE / DEPTH / BENCHMARK_MODE / SEVERITY_FLOOR outside its
                     allowed set (Phase 0 preflight)

A loop with zero findings is VALID (R7): absence of tasks is never a violation.

When the run directory (or its parent, if you point --run at docs/ itself)
contains the target's AUDIT.md, the CONFIG block is preflighted and
PROTECTED_AREAS is loaded from it automatically — `--protected` then extends
rather than replaces it (closes the double-entry gap, review item G-F).

Usage:
  python3 evals/validate.py --run <dir-containing-docs>  [--protected p1,p2]
  python3 evals/validate.py --run <dir> --report json    # structured findings export
  python3 evals/validate.py --run <dir> --report sarif   # GitHub code-scanning format
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
    ("gitlab-token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20}\b")),
    ("stripe-key", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")),
    ("openai-key", re.compile(r"\bsk-proj-[A-Za-z0-9_-]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("npm-token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
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


CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")  # an escaped \| is cell CONTENT, not a separator


def norm(cell: str) -> str:
    """Strip markdown wrapping without mangling shell syntax: backticks go
    everywhere, but * and _ are stripped only at the edges (emphasis), so
    commands like `wc -l src/*.py` survive intact. Escaped pipes (\\|) are
    unescaped back to literal | so commands like `grep -cE "TODO\\|FIXME"`
    round-trip to what the agent actually ran (fixture G05)."""
    s = cell.strip().replace("`", "").replace("\\|", "|")
    return re.sub(r"^[*_]+|[*_]+$", "", s).strip()


def split_cells(line: str):
    return [norm(c) for c in CELL_SPLIT_RE.split(line.strip().strip("|"))]


def parse_tables(text: str):
    """Yield (header_cells, rows, end_line_idx) for every markdown table."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            header = split_cells(line)
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = split_cells(lines[j])
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
MODE_GATED_RE = re.compile(r"(?mi)^\s*-?\s*Mode:\s*gated\b")
EXECUTED_STATUSES = {"DONE", "IN-PROGRESS", "BLOCKED"}


def check_approvals(text, violations, src):
    """Gated-mode invariant: every executed task (DONE / IN-PROGRESS /
    BLOCKED) in a loop section must be listed on that section's `Approved:`
    line. The check fires when the line exists OR the section echoes
    `Mode: gated` (v1.1.0) — a gated loop with executed tasks and no
    `Approved:` line is a violation, not an exemption. Sections declaring
    neither are treated as autonomous and not checked."""
    sections = re.split(r"(?m)^## (?=Loop\b)", text)
    for sec in sections:
        m = APPROVED_RE.search(sec)
        gated = MODE_GATED_RE.search(sec) is not None
        if not m and not gated:
            continue
        if m:
            raw = m.group(1).strip()
            approved = set() if raw.lower() == "none" else {norm(x) for x in raw.split(",") if x.strip()}
        else:
            approved = set()
        for header, rows, _ in parse_tables(sec):
            ii, st_i = col(header, "id"), col(header, "status")
            if ii is None or st_i is None or col(header, "metric") is not None:
                continue
            for r in rows:
                tid = r[ii] if ii < len(r) else ""
                status = r[st_i] if st_i < len(r) else ""
                if status in EXECUTED_STATUSES and tid and tid not in approved:
                    why = ("not on this loop's Approved: line" if m
                           else "this gated loop has no Approved: line at all")
                    violations.append(("GATED-UNAPPROVED-EXEC", src,
                                       f"task '{tid}' is {status} but {why}"))


def check_secrets(text, violations, src):
    for kind, pat in SECRET_PATTERNS:
        for m in pat.finditer(text):
            ctx = text[max(0, m.start() - 40):m.start()]
            if "[REDACTED:" in ctx + m.group(0):
                continue
            violations.append(("R8-SECRET", src, f"unredacted {kind} matching '{m.group(0)[:12]}…'"))


MODE_LINE_RE = re.compile(r"(?mi)^\s*-?\s*Mode:\s*\S+")
NO_FINDINGS_RE = re.compile(r"No significant findings", re.IGNORECASE)


def check_template_conformance(text, violations, src):
    """BLINDSPOTS BS-12 — the meta-tripwire. Every other check activates only
    when output LOOKS like the Phase 2 template (pipe tables, headings, Mode
    echo); a run that emits prose instead silently escapes all of them. This
    converts that silent escape into a violation, making the rest of the rule
    set load-bearing. Per loop section the template requires a `Mode:` line in
    Scope & method, and EITHER (benchmark table AND task table) OR the R7
    "No significant findings" line (a tabled-baselines-but-no-tasks loop also
    carries that line, so benchmark-table-only sections remain conformant)."""
    sections = re.split(r"(?m)^##\s+(?=Loop\b)", text)[1:]
    if not sections:
        violations.append(("TEMPLATE-NONCONFORMANT", src,
                           "no '## Loop <N>' section found — output does not follow the Phase 2 template"))
        return
    for sec in sections:
        loop_id = (sec.splitlines() or ["?"])[0].strip()
        if not MODE_LINE_RE.search(sec):
            violations.append(("TEMPLATE-NONCONFORMANT", src,
                               f"'{loop_id}': Scope & method has no 'Mode:' line (required since v1.1.0)"))
        tables = list(parse_tables(sec))
        has_bench = any(col(h, "metric") is not None and col(h, "baseline") is not None for h, _, _ in tables)
        has_task = any(col(h, "id") is not None and col(h, "status") is not None
                       and col(h, "metric") is None for h, _, _ in tables)
        if not (has_bench and has_task) and not NO_FINDINGS_RE.search(sec):
            violations.append(("TEMPLATE-NONCONFORMANT", src,
                               f"'{loop_id}': missing benchmark and/or task table and no 'No significant findings' line"))


CONFIG_ENUMS = {
    "MODE": {"gated", "autonomous"},
    "DEPTH": {"quick", "standard", "deep"},
    "BENCHMARK_MODE": {"auto", "provided", "none"},
    "SEVERITY_FLOOR": {"Critical", "High", "Medium", "Low"},
}
PLACEHOLDER_RE = re.compile(r"<[^<>\n]*>")
CONFIG_KEY_RE = re.compile(r"^([A-Z][A-Z_]+):\s*(.*)$")


def parse_audit_config(audit_md: Path):
    """Flat KEY: value parse of the CONFIG block in a target repo's AUDIT.md.
    Trailing `# comment` text is stripped; placeholder text is preserved."""
    cfg, in_config = {}, False
    for line in audit_md.read_text(encoding="utf-8").splitlines():
        if re.match(r"^##\s*CONFIG\b", line):
            in_config = True
            continue
        if in_config and re.match(r"^##\s", line):
            break
        if not in_config:
            continue
        m = CONFIG_KEY_RE.match(line.strip())
        if not m:
            continue
        key, raw = m.groups()
        cfg[key] = re.split(r"\s+#", raw, 1)[0].strip()
    return cfg


def check_config_preflight(target_root: Path, violations, protected):
    """Phase 0 CONFIG preflight (review gap G-D) + PROTECTED_AREAS auto-load
    (gap G-F). Runs only when the target's AUDIT.md is present; placeholder
    values never silently configure anything."""
    audit = target_root / "AUDIT.md"
    if not audit.exists():
        return
    cfg = parse_audit_config(audit)
    for key, val in cfg.items():
        if PLACEHOLDER_RE.search(val):
            violations.append(("CONFIG-PLACEHOLDER", "AUDIT.md",
                               f"{key} still contains unedited template text: '{val[:60]}'"))
        elif key in CONFIG_ENUMS and val and val not in CONFIG_ENUMS[key]:
            violations.append(("CONFIG-BAD-ENUM", "AUDIT.md",
                               f"{key} '{val}' not in {sorted(CONFIG_ENUMS[key])}"))
    areas = cfg.get("PROTECTED_AREAS", "")
    if areas and not PLACEHOLDER_RE.search(areas):
        for p in areas.split(","):
            p = p.strip()
            if p and p not in protected:
                protected.append(p)


def validate_run(run_dir: Path, protected=None):
    """Validate one run directory (containing docs/BACKLOG.md, docs/HANDOFF.md)."""
    protected = list(protected or [])
    violations = []
    docs = run_dir / "docs" if (run_dir / "docs").is_dir() else run_dir
    # The target repo's root is docs/'s parent — whether --run was pointed at
    # the repo root or at docs/ itself. CONFIG preflight may extend `protected`.
    check_config_preflight(docs.parent, violations, protected)
    backlog = docs / "BACKLOG.md"
    handoff = docs / "HANDOFF.md"
    if not backlog.exists():
        violations.append(("MISSING-FILE", "docs/BACKLOG.md", "file not found"))
    if backlog.exists():
        text = backlog.read_text(encoding="utf-8")
        check_template_conformance(text, violations, "BACKLOG.md")
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


LOOP_HEAD_RE = re.compile(r"^Loop\s+(\d+)\s*(?:—|-)?\s*(.*)$")


def build_report(run_dir: Path, protected, violations):
    """Findings export (review gap G-G): one structured object per run, for
    roll-ups across projects, trend dashboards, and client-facing summaries.
    Parses the same artifacts the validator checks — no second source of truth."""
    import datetime
    docs = run_dir / "docs" if (run_dir / "docs").is_dir() else run_dir
    audit = docs.parent / "AUDIT.md"
    protocol_version = None
    protected = list(protected)
    if audit.exists():
        m = re.search(r"v\d+\.\d+\.\d+", audit.read_text(encoding="utf-8").splitlines()[0])
        protocol_version = m.group(0) if m else None
        check_config_preflight(docs.parent, [], protected)  # mirror the auto-load; violations already counted
    report = {
        "schema": "code-audit-framework/report@1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "protocol_version": protocol_version,
        "protected_areas": protected,
        "loops": [],
        "metrics": [],
        "summary": {},
    }
    backlog = docs / "BACKLOG.md"
    if backlog.exists():
        text = backlog.read_text(encoding="utf-8")
        for sec in re.split(r"(?m)^##\s+(?=Loop\b)", text)[1:]:
            first = (sec.splitlines() or [""])[0]
            hm = LOOP_HEAD_RE.match(first.strip())
            mode_m = re.search(r"(?mi)^\s*-?\s*Mode:\s*(\S+)", sec)
            appr_m = APPROVED_RE.search(sec)
            loop = {
                "loop": int(hm.group(1)) if hm else None,
                "date": (hm.group(2).strip() or None) if hm else None,
                "mode": mode_m.group(1) if mode_m else None,
                "approved": ([] if appr_m.group(1).strip().lower() == "none"
                             else [norm(x) for x in appr_m.group(1).split(",") if x.strip()]) if appr_m else None,
                "no_significant_findings": bool(NO_FINDINGS_RE.search(sec)),
                "tasks": [],
            }
            for header, rows, _ in parse_tables(sec):
                ii, st_i = col(header, "id"), col(header, "status")
                if ii is None or st_i is None or col(header, "metric") is not None:
                    continue
                sev_i, vec_i, d_i, v_i = (col(header, "sev"), col(header, "vector"),
                                          col(header, "description"), col(header, "verify"))
                for r in rows:
                    def cell(ix):
                        return r[ix] if ix is not None and ix < len(r) else ""
                    if cell(ii):
                        loop["tasks"].append({
                            "id": cell(ii), "severity": cell(sev_i), "status": cell(st_i),
                            "vector": cell(vec_i), "description": cell(d_i), "verify": cell(v_i),
                        })
            report["loops"].append(loop)
    handoff = docs / "HANDOFF.md"
    if handoff.exists():
        text = handoff.read_text(encoding="utf-8")
        for header, rows, _ in parse_tables(text):
            mi, fi = col(header, "metric"), col(header, "final")
            if mi is None or fi is None:
                continue
            bi, di, ti, vi, si = (col(header, "baseline"), col(header, "delta"),
                                  col(header, "target"), col(header, "verify"), col(header, "status"))
            for r in rows:
                def cell(ix):
                    return r[ix] if ix is not None and ix < len(r) else ""
                if cell(mi):
                    report["metrics"].append({
                        "metric": cell(mi), "baseline": cell(bi), "final": cell(fi),
                        "delta": cell(di), "target": cell(ti), "verify": cell(vi), "status": cell(si),
                    })
    tasks = [t for l in report["loops"] for t in l["tasks"]]
    by = lambda key: {k: sum(1 for t in tasks if t[key] == k)  # noqa: E731
                      for k in sorted({t[key] for t in tasks if t[key]})}
    vio_codes = {}
    for c, _, _ in violations:
        vio_codes[c] = vio_codes.get(c, 0) + 1
    report["summary"] = {
        "loops": len(report["loops"]),
        "tasks": len(tasks),
        "tasks_by_status": by("status"),
        "tasks_by_severity": by("severity"),
        "metrics_measured": sum(1 for m in report["metrics"] if m["status"] == "MEASURED"),
        "violations": len(violations),
        "violations_by_code": dict(sorted(vio_codes.items())),
        "clean": not violations,
    }
    report["violations"] = [{"code": c, "file": s, "detail": d} for c, s, d in violations]
    return report


def to_sarif(report):
    """Minimal SARIF 2.1.0 for GitHub code scanning (review F5, optional output)."""
    rules, results = {}, []
    for v in report["violations"]:
        rules.setdefault(v["code"], {"id": v["code"], "name": v["code"],
                                     "shortDescription": {"text": v["code"]}})
        results.append({
            "ruleId": v["code"],
            "level": "error",
            "message": {"text": v["detail"]},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f"docs/{v['file']}"
                          if not v["file"].endswith("AUDIT.md") else v["file"]}}}],
        })
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "code-audit-framework",
                "informationUri": "https://github.com/cyberskill-official/code-audit-framework",
                "version": (report.get("protocol_version") or "unknown").lstrip("v"),
                "rules": list(rules.values()),
            }},
            "results": results,
        }],
    }


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


def check_registry(fixture_dirs):
    """Registry drift guard (improve/BLINDSPOTS.md BS-10): rules.json must
    agree with fixtures/ on disk, in both directions. A rule referencing a
    missing fixture means its coverage silently died; an unregistered fixture
    means coverage the registry does not own."""
    problems = []
    reg = HERE / "rules.json"
    if not reg.exists():
        return ["rules.json missing — registry is mandatory"]
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"rules.json unparseable: {e}"]
    on_disk = {d.name for d in fixture_dirs}
    referenced = set()
    for rule in data.get("rules", []):
        for fx in rule.get("fixtures_exercising", []):
            referenced.add(fx)
            if fx not in on_disk:
                problems.append(f"rules.json: {rule.get('rule_id', '?')} references missing fixture '{fx}'")
    for d in sorted(on_disk - referenced):
        problems.append(f"fixture '{d}' exists on disk but is registered under no rule in rules.json")
    return problems


def run_all(as_json=False):
    results, ok = [], True
    fixtures = sorted(d for d in FIXTURES.iterdir() if d.is_dir())
    registry_problems = check_registry(fixtures)
    ok &= not registry_problems
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
    summary = {"fixtures": len(results), "passed": sum(r["ok"] for r in results), "all_ok": ok,
               "registry_problems": registry_problems, "results": results}
    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        for p in registry_problems:
            print(f"[FAIL] REGISTRY DRIFT — {p}")
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
    ap.add_argument("--report", choices=["json", "sarif"],
                    help="with --run: emit a structured findings report instead of plain violations")
    ap.add_argument("--protected", default="", help="comma-separated protected paths (extends the target AUDIT.md's PROTECTED_AREAS)")
    args = ap.parse_args()
    if args.all:
        sys.exit(run_all(as_json=args.json))
    if args.run:
        protected = [p for p in args.protected.split(",") if p]
        v = validate_run(Path(args.run), protected=protected)
        if args.report:
            report = build_report(Path(args.run), protected, v)
            print(json.dumps(to_sarif(report) if args.report == "sarif" else report, indent=2))
        elif args.json:
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
