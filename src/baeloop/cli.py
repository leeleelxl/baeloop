from __future__ import annotations

from pathlib import Path

import typer

from baeloop.adapters.agentlab import AgentLabAdapterUnavailable
from baeloop.advisor import propose_patch
from baeloop.compare import build_comparison_report, render_markdown
from baeloop.doctor import probe_agentlab_environment
from baeloop.grid_probe import run_grid_coordinate_probe, render_grid_coordinate_probe_markdown
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
from baeloop.llm_advisor import LLMAdvisorConfig, propose_patch_with_llm
from baeloop.models import AdvisorProposal, ComparisonReport
from baeloop.patcher import materialize_config_patch
from baeloop.policy_replay import replay_action_policy_trace, render_policy_replay_markdown
from baeloop.runner import iter_taskset_records
from baeloop.terminal_probe import run_terminal_probe, render_terminal_probe_markdown

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
    advisor_mode: str = typer.Option(
        "deterministic",
        "--advisor-mode",
        help="Advisor implementation: deterministic or llm.",
    ),
    model: str = typer.Option("gpt-5.4", help="LLM advisor model when --advisor-mode llm."),
    base_url: str = typer.Option(
        "https://api.ai.ohfi.com.cn/v1",
        help="OpenAI-compatible base URL for the LLM advisor.",
    ),
    api_key_env: str = typer.Option(
        "OHFI_API_KEY",
        help="Environment variable containing the LLM advisor API key.",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Use streaming chat completions for the LLM advisor.",
    ),
) -> None:
    """Generate a bounded next-config patch proposal."""
    comparison = read_model_json(report, ComparisonReport)
    if advisor_mode == "deterministic":
        proposal = propose_patch(comparison)
    elif advisor_mode == "llm":
        proposal = propose_patch_with_llm(
            comparison,
            config=LLMAdvisorConfig(
                model=model,
                base_url=base_url,
                api_key_env=api_key_env,
                stream=stream,
            ),
        )
    else:
        raise typer.BadParameter("Unsupported advisor mode. Use deterministic or llm.")
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


@app.command(name="replay-policy")
def replay_policy(
    trace_dir: Path = typer.Option(
        ...,
        exists=True,
        file_okay=False,
        readable=True,
        help="AgentLab trace directory containing step_*.pkl.gz files.",
    ),
    config: Path = typer.Option(..., exists=True, readable=True, help="YAML agent config with action_policy."),
    json_out: Path | None = typer.Option(None, help="Path for machine-readable replay report."),
    markdown_out: Path | None = typer.Option(None, help="Path for markdown replay report."),
) -> None:
    """Replay a bounded action policy over an AgentLab trace without rerunning the browser."""
    policy = read_agent_config(config).action_policy
    try:
        report = replay_action_policy_trace(trace_dir=trace_dir, policy=policy)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc

    if json_out:
        write_json(json_out, report)
    if markdown_out:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_policy_replay_markdown(report), encoding="utf-8")

    typer.echo(
        f"Replayed {policy.name} on {trace_dir}: "
        f"steps={report.step_count}, applied={report.applied_count}"
    )


@app.command(name="probe-terminal")
def probe_terminal(
    seed: int = typer.Option(27, help="MiniWoB terminal task seed."),
    base_url: str | None = typer.Option(
        None,
        help="MiniWoB base URL. Defaults to MINIWOB_URL or local external/miniwob-plusplus assets.",
    ),
    json_out: Path | None = typer.Option(None, help="Path for machine-readable terminal probe report."),
    markdown_out: Path | None = typer.Option(None, help="Path for markdown terminal probe report."),
) -> None:
    """Probe which BrowserGym actions actually mutate MiniWoB terminal state."""
    try:
        report = run_terminal_probe(seed=seed, base_url=base_url)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc

    if json_out:
        write_json(json_out, report)
    if markdown_out:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_terminal_probe_markdown(report), encoding="utf-8")

    typer.echo(
        f"Probed terminal seed={seed}: "
        f"results={len(report.results)}, working={len(report.working_results)}"
    )


@app.command(name="probe-grid-coordinate")
def probe_grid_coordinate(
    seed: int = typer.Option(25, help="MiniWoB grid-coordinate task seed."),
    base_url: str | None = typer.Option(
        None,
        help="MiniWoB base URL. Defaults to MINIWOB_URL or local external/miniwob-plusplus assets.",
    ),
    json_out: Path | None = typer.Option(None, help="Path for machine-readable grid probe report."),
    markdown_out: Path | None = typer.Option(None, help="Path for markdown grid probe report."),
) -> None:
    """Probe whether coordinate clicks solve MiniWoB grid-coordinate targets."""
    try:
        report = run_grid_coordinate_probe(seed=seed, base_url=base_url)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc

    if json_out:
        write_json(json_out, report)
    if markdown_out:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_grid_coordinate_probe_markdown(report), encoding="utf-8")

    typer.echo(
        f"Probed grid-coordinate seed={seed}: "
        f"results={len(report.results)}, working={len(report.working_results)}"
    )


if __name__ == "__main__":
    app()
