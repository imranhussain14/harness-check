"""Render a Report as rich terminal output, Markdown, or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from rich.console import Console
from rich.table import Table

from .checks import Report, Severity

_SEVERITY_STYLE = {
    Severity.ERROR: "bold red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
}


def render_terminal(report: Report, console: Console | None = None) -> None:
    console = console or Console()
    console.print(f"\n[bold]harness-check report: {report.system_name}[/bold]\n")

    table = Table(show_lines=False)
    table.add_column("Severity")
    table.add_column("Check")
    table.add_column("Subject")
    table.add_column("Message")
    for issue in report.issues:
        table.add_row(
            f"[{_SEVERITY_STYLE[issue.severity]}]{issue.severity.value}[/{_SEVERITY_STYLE[issue.severity]}]",
            issue.check,
            issue.subject,
            issue.message,
        )
    console.print(table)

    if report.totals:
        console.print("\n[bold]Power budget summary[/bold]")
        for key, value in report.totals.items():
            if isinstance(value, float):
                console.print(f"  {key}: {value:.3f}")
            else:
                console.print(f"  {key}: {value}")

    n_err, n_warn = len(report.errors), len(report.warnings)
    console.print()
    if report.passed:
        console.print(f"[bold green]PASS[/bold green] — 0 errors, {n_warn} warning(s)")
    else:
        console.print(f"[bold red]FAIL[/bold red] — {n_err} error(s), {n_warn} warning(s)")


def to_dict(report: Report) -> dict:
    return {
        "system_name": report.system_name,
        "passed": report.passed,
        "totals": report.totals,
        "issues": [
            {
                "severity": issue.severity.value,
                "check": issue.check,
                "subject": issue.subject,
                "message": issue.message,
            }
            for issue in report.issues
        ],
    }


def render_json(report: Report) -> str:
    return json.dumps(to_dict(report), indent=2)


def render_markdown(report: Report) -> str:
    lines = [f"# harness-check report: {report.system_name}", ""]
    status = "✅ PASS" if report.passed else "❌ FAIL"
    lines.append(
        f"**Status:** {status} — {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    )
    lines.append("")
    if report.issues:
        lines.append("| Severity | Check | Subject | Message |")
        lines.append("|---|---|---|---|")
        for issue in report.issues:
            lines.append(
                f"| {issue.severity.value} | {issue.check} | {issue.subject} | {issue.message} |"
            )
        lines.append("")
    if report.totals:
        lines.append("## Power budget summary")
        for key, value in report.totals.items():
            if isinstance(value, float):
                lines.append(f"- **{key}**: {value:.3f}")
            else:
                lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)
