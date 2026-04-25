from __future__ import annotations

from pathlib import Path

import typer

from baeloop.adapters.agentlab import AgentLabAdapterUnavailable
from baeloop.advisor import propose_patch
from baeloop.compare import build_comparison_report, render_markdown
from baeloop.doctor import probe_agentlab_environment
from baeloop.io import (
    read_agent_config,
    append_jsonl_record,
    read_jsonl_records,
    read_model_json,
    read_taskset,
    read_yaml_dict,
    reset_jsonl_records,
    write_json,
    write_yaml_dict,
)
from baeloop.models import AdvisorProposal, ComparisonReport
from baeloop.patcher import materialize_config_patch
from baeloop.runner import iter_taskset_records

app = typer.Typer(help="Browser-agent evaluation and optimization loop.")


@app.command()
def doctor(
    adapter: str = typer.Option("agentlab", help="Adapter to inspect. Currently supported: agentlab."),
    json_out: Path | None = typer.Option(None, help="Optional path for machine-readable environment report."),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Import modules instead of only checking import specs."),
    check_playwright_browser: bool = typer.Option(
        True,
        "--check-playwright-browser/--skip-playwright-browser",
        help="Check whether Playwright Chromium is installed.",
    ),
    check_miniwob_url: bool = typer.Option(
        True,
        "--check-miniwob-url/--skip-miniwob-url",
        help="Check whether MINIWOB_URL is set and points to local MiniWoB++ files.",
    ),
) -> None:
    """Inspect runtime dependencies for real benchmark adapters."""
    if adapter != "agentlab":
        raise typer.BadParameter("Unsupported adapter. Currently supported: agentlab")

    report = probe_agentlab_environment(
        strict_import=strict,
        check_playwright_browser=check_playwright_browser,
        check_miniwob_url=check_miniwob_url,
    )
    if json_out:
        write_json(json_out, report)

    status = "ready" if report.ready else "not ready"
    typer.echo(f"Adapter {report.adapter}: {status}")
    for dependency in report.dependencies:
        marker = "ok" if dependency.available else "missing"
        note = f" ({dependency.note})" if dependency.note else ""
        typer.echo(f"- {dependency.module}: {marker}{note}")


@app.command()
def run(
    config: Path = typer.Option(..., exists=True, readable=True, help="YAML agent config."),
    taskset: Path = typer.Option(..., exists=True, readable=True, help="YAML task set."),
    out: Path = typer.Option(..., help="Path for JSONL run records."),
    adapter: str = typer.Option("mock", help="Runtime adapter. Currently supported: mock, agentlab."),
    experiment_id: str | None = typer.Option(None, help="Optional experiment id."),
) -> None:
    """Run one config on one task set and persist normalized records."""
    if adapter not in {"mock", "agentlab"}:
        raise typer.BadParameter("Unsupported adapter. Currently supported: mock, agentlab")

    resolved_config = read_agent_config(config)
    resolved_taskset = read_taskset(taskset)
    records = []
    reset_jsonl_records(out)
    try:
        for record in iter_taskset_records(
            config=resolved_config,
            taskset=resolved_taskset,
            adapter=adapter,
            experiment_id=experiment_id,
        ):
            append_jsonl_record(out, record)
            records.append(record)
    except (AgentLabAdapterUnavailable, NotImplementedError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    success_count = sum(1 for record in records if record.status == "success")
    typer.echo(
        f"Ran {resolved_config.id} on {resolved_taskset.id} with {adapter}: "
        f"records={len(records)}, success_rate={success_count / len(records):.3f}, out={out}"
    )


@app.command()
def compare(
    base: Path = typer.Option(..., exists=True, readable=True, help="Baseline JSONL run records."),
    new: Path = typer.Option(..., exists=True, readable=True, help="Candidate JSONL run records."),
    taskset_id: str = typer.Option("unknown", help="Task set identifier."),
    json_out: Path | None = typer.Option(None, help="Path for machine-readable compare report."),
    markdown_out: Path | None = typer.Option(None, help="Path for markdown compare report."),
) -> None:
    """Compare two completed experiment runs."""
    report = build_comparison_report(
        baseline_records=read_jsonl_records(base),
        candidate_records=read_jsonl_records(new),
        taskset_id=taskset_id,
    )
    if json_out:
        write_json(json_out, report)
    if markdown_out:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_markdown(report), encoding="utf-8")

    delta = report.metrics["delta"]
    typer.echo(
        f"Compared {report.baseline_config_id} -> {report.candidate_config_id}: "
        f"success_rate_delta={delta['success_rate']:.3f}, "
        f"regressions={report.regression_count}, "
        f"improvements={len(report.improvements)}"
    )


@app.command()
def advise(
    report: Path = typer.Option(..., exists=True, readable=True, help="JSON compare report."),
    out: Path = typer.Option(..., help="Path for advisor proposal JSON."),
) -> None:
    """Generate a bounded next-config patch proposal."""
    proposal = propose_patch(read_model_json(report, ComparisonReport))
    write_json(out, proposal)
    typer.echo(f"Wrote advisor proposal {proposal.hypothesis_id} to {out}")


@app.command(name="patch")
def patch_config(
    base_config: Path = typer.Option(..., exists=True, readable=True, help="Base YAML agent config."),
    proposal: Path = typer.Option(..., exists=True, readable=True, help="Advisor proposal JSON."),
    out: Path = typer.Option(..., help="Path for generated YAML agent config."),
) -> None:
    """Materialize an advisor proposal into a concrete config file."""
    patched = materialize_config_patch(
        base_config=read_yaml_dict(base_config),
        proposal=read_model_json(proposal, AdvisorProposal),
    )
    write_yaml_dict(out, patched)
    typer.echo(f"Wrote patched config {patched['id']} to {out}")


if __name__ == "__main__":
    app()
