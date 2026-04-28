from __future__ import annotations

from pathlib import Path
from typing import Any

from baeloop.io import read_json_dict


def render_demo_summary(report_dir: Path = Path("reports")) -> str:
    hard_ladder = [
        ("retry baseline", report_dir / "agentlab_hard_compare.json", "candidate"),
        ("step budget", report_dir / "agentlab_hard_budget30_compare.json", "candidate"),
        ("scroll policy", report_dir / "agentlab_hard_scroll_policy_compare.json", "candidate"),
        ("scroll + terminal", report_dir / "agentlab_hard_combined_policy_compare.json", "candidate"),
        ("full policy", report_dir / "agentlab_hard_full_policy_compare.json", "candidate"),
        ("same-slice repeat", report_dir / "agentlab_hard_full_policy_repeat_compare.json", "candidate"),
    ]
    broad = read_json_dict(report_dir / "agentlab_broad_full_policy_compare.json")
    control = read_json_dict(report_dir / "agentlab_control_full_policy_compare.json")
    advisor = read_json_dict(report_dir / "advisor_eval_holdout_llm_v2.json")

    lines = [
        "# BAELOOP Demo Summary",
        "",
        "## 1. Hard-Slice Optimization Ladder",
        "",
        "| Stage | Config | Success Rate | Regressions |",
        "|---|---|---:|---:|",
    ]
    for stage, path, side in hard_ladder:
        report = read_json_dict(path)
        metrics = report["metrics"][side]
        config_id = report[f"{side}_config_id"]
        lines.append(
            f"| {stage} | `{config_id}` | {_rate(metrics['success_rate'])} | {report['regression_count']} |"
        )

    lines.extend(
        [
            "",
            "## 2. Broad Validation",
            "",
            "| Baseline | Candidate | Success Delta | Improvements | Regressions |",
            "|---|---|---:|---:|---:|",
            (
                f"| `{broad['baseline_config_id']}` | `{broad['candidate_config_id']}` | "
                f"{_signed_rate(_delta(broad, 'success_rate'))} | {len(broad['improvements'])} | "
                f"{broad['regression_count']} |"
            ),
            "",
            "## 3. Control Boundary",
            "",
            "| Baseline Success | Candidate Success | Improvements | Regressions | Interpretation |",
            "|---:|---:|---:|---:|---|",
            (
                f"| {_rate(control['metrics']['baseline']['success_rate'])} | "
                f"{_rate(control['metrics']['candidate']['success_rate'])} | "
                f"{len(control['improvements'])} | {control['regression_count']} | "
                "remaining failures are coordinate/control capability boundaries |"
            ),
            "",
            "## 4. Advisor Holdout Eval",
            "",
            "| Advisor | Avg Score | Direction | Safe Patch | Evidence | Boundary |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for advisor_name, item in sorted(advisor["summary"].items()):
        lines.append(
            f"| `{advisor_name}` | {item['avg_score']:.3f} | "
            f"{item['direction_match_rate']:.3f} | {item['safe_patch_rate']:.3f} | "
            f"{item['evidence_use_rate']:.3f} | {item['boundary_awareness_rate']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 5. Current Project Claim",
            "",
            "- BAELOOP is not a prompt-only browser agent project.",
            "- The browser agent is the execution substrate; the project highlight is the optimization advisor.",
            "- `llm-v2` wins by combining LLM stages, deterministic reference, and evidence-maturity selection.",
            "- The next demo risk to address is external validity on fresher browser task distributions.",
        ]
    )
    return "\n".join(lines) + "\n"


def _delta(report: dict[str, Any], metric: str) -> float:
    return float(report["metrics"]["delta"][metric])


def _rate(value: float) -> str:
    return f"{float(value):.3f}"


def _signed_rate(value: float) -> str:
    return f"{float(value):+.3f}"
