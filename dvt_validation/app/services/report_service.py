"""
Report Service — generate a human-readable Markdown preflight report.

All content comes from the PreflightResult; nothing is hardcoded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.models.preflight_models import PreflightResult, Problem, Severity


def generate_report(result: PreflightResult, report_dir: Path) -> Path:
    """
    Generate ``preflight_report.md`` inside *report_dir* and return its path.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "preflight_report.md"

    lines: list[str] = []
    _h = lines.append

    _h("# Preflight Validation Report\n")
    _h(f"**Run ID:** `{result.run_id}`  ")
    _h(f"**Generated:** {datetime.now(timezone.utc).isoformat()}  \n")

    # ---- Overall Result ----
    _h("## Overall Result\n")
    emoji = "✅" if result.status.value == "SUCCESS" else "❌"
    _h(f"{emoji} **{result.status.value}**\n")

    # ---- Input Files ----
    _h("## Input Files\n")
    _h(f"| File | Path |")
    _h(f"|------|------|")
    _h(f"| Validation YAML | `{result.yaml_file or 'N/A'}` |")
    _h(f"| SeaTunnel .conf | `{result.conf_file or 'N/A'}` |\n")

    # ---- Summary ----
    _h("## Summary\n")
    s = result.summary
    _h(f"| Metric | Count |")
    _h(f"|--------|-------|")
    _h(f"| Total checks | {s.total_checks} |")
    _h(f"| Passed | {s.passed} |")
    _h(f"| Failed | {s.failed} |")
    _h(f"| Warnings | {s.warnings} |\n")

    # ---- Message ----
    if result.message:
        _h(f"> {result.message}\n")

    # ---- Problems ----
    if result.problems:
        _h("## Problems\n")

        errors = [p for p in result.problems if p.severity == Severity.ERROR]
        warnings = [p for p in result.problems if p.severity == Severity.WARNING]
        infos = [p for p in result.problems if p.severity == Severity.INFO]

        if errors:
            _h("### ❌ Errors\n")
            for idx, p in enumerate(errors, 1):
                _format_problem(lines, idx, p)

        if warnings:
            _h("### ⚠️ Warnings\n")
            for idx, p in enumerate(warnings, 1):
                _format_problem(lines, idx, p)

        if infos:
            _h("### ℹ️ Information\n")
            for idx, p in enumerate(infos, 1):
                _format_problem(lines, idx, p)
    else:
        _h("## Problems\n")
        _h("_No problems detected._\n")

    # ---- Write ----
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _format_problem(lines: list[str], idx: int, p: Problem) -> None:
    """Format a single problem as a Markdown subsection."""
    lines.append(f"#### {idx}. {p.type}\n")
    if p.job:
        lines.append(f"**Job:** `{p.job}`  ")
    if p.stage:
        lines.append(f"**Stage:** {p.stage}  ")
    lines.append(f"**Severity:** {p.severity.value}  \n")
    if p.message:
        lines.append(f"**Problem:** {p.message}  \n")

    parts: list[str] = []
    if p.file_a:
        parts.append(f"**File A:** `{p.file_a}`")
    if p.path_a:
        parts.append(f"**Path A:** `{p.path_a}`")
    if p.file_b:
        parts.append(f"**File B:** `{p.file_b}`")
    if p.path_b:
        parts.append(f"**Path B:** `{p.path_b}`")
    if parts:
        lines.append("  \n".join(parts) + "  \n")

    if p.expected is not None:
        lines.append(f"**Expected:** `{p.expected}`  ")
    if p.actual is not None:
        lines.append(f"**Actual:** `{p.actual}`  \n")

    lines.append("")
