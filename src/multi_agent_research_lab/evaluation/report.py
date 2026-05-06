"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    trace_state: ResearchState | None = None,
) -> str:
    """Render benchmark metrics and optional agent trace summary to markdown."""

    lines = [
        "# Benchmark Report",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Citation Coverage | Notes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "N/A" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "N/A" if item.quality_score is None else f"{item.quality_score:.1f}"
        citation_coverage = (
            "N/A" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        )
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | "
            f"{citation_coverage} | {item.notes} |"
        )
    if trace_state is not None:
        lines.extend(_render_agent_trace_summary(trace_state))
    return "\n".join(lines) + "\n"


def _render_agent_trace_summary(state: ResearchState) -> list[str]:
    lines = [
        "",
        "## Agent Trace Summary",
        "",
        "| Agent | Duration (s) | Input Tokens | Output Tokens | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for event in state.trace:
        if event["name"] != "agent.end":
            continue
        payload = event["payload"]
        metadata = payload.get("metadata", {})
        input_tokens = metadata.get("input_tokens", "N/A")
        output_tokens = metadata.get("output_tokens", "N/A")
        notes = "N/A"
        if payload["agent"] == "researcher":
            notes = f"sources={len(state.sources)}"
        lines.append(
            f"| {payload['agent']} | {payload['duration_seconds']:.2f} | "
            f"{input_tokens} | {output_tokens} | "
            f"{notes} |"
        )
    return lines
