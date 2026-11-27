"""CLI entry point for harness-check."""

from __future__ import annotations

import sys

import click
import yaml
from rich.console import Console

from .checks import run_all_checks
from .loader import load_spec
from .report_render import render_json, render_markdown, render_terminal
from .wireviz_export import to_wireviz_yaml_dict


@click.group()
@click.version_option()
def main() -> None:
    """harness-check: validate a robot's electrical system from a YAML spec."""


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json", "markdown"]),
    default="terminal",
    help="Report output format.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(),
    default=None,
    help="Write the report to this file instead of stdout (json/markdown only).",
)
@click.option(
    "--fail-on-warning",
    is_flag=True,
    default=False,
    help="Exit non-zero if there are warnings, not just errors.",
)
def check(spec_path: str, output_format: str, out_path: str | None, fail_on_warning: bool) -> None:
    """Run all checks against SPEC_PATH and print a report."""
    system = load_spec(spec_path)
    report = run_all_checks(system)

    if output_format == "terminal":
        render_terminal(report, Console())
    elif output_format == "json":
        text = render_json(report)
        _write_or_print(text, out_path)
    elif output_format == "markdown":
        text = render_markdown(report)
        _write_or_print(text, out_path)

    if not report.passed:
        sys.exit(1)
    if fail_on_warning and report.warnings:
        sys.exit(2)


@main.command("export-wireviz")
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--out", "out_path", type=click.Path(), required=True, help="Output YAML path.")
def export_wireviz(spec_path: str, out_path: str) -> None:
    """Export SPEC_PATH as a WireViz-compatible harness YAML for diagram rendering."""
    system = load_spec(spec_path)
    wv = to_wireviz_yaml_dict(system)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(wv, f, sort_keys=False)
    click.echo(f"Wrote WireViz YAML to {out_path}")


def _write_or_print(text: str, out_path: str | None) -> None:
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        click.echo(text)


if __name__ == "__main__":
    main()
