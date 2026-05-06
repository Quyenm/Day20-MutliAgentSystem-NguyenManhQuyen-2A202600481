"""Backend payload builder for the localhost demo."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from multi_agent_research_lab.core.schemas import BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.hosted import export_hosted_traces
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

StateRunner = Callable[[str], ResearchState]


def build_demo_payload(
    query: str,
    baseline_runner: StateRunner | None = None,
    multi_runner: StateRunner | None = None,
    export_hosted: bool = True,
) -> dict[str, Any]:
    """Run both systems and return a UI-ready comparison payload."""

    clean_query = query.strip()
    if len(clean_query) < 5:
        raise ValueError("Query must contain at least 5 characters.")

    baseline_state, baseline_metrics = run_benchmark(
        "baseline",
        clean_query,
        baseline_runner or run_baseline,
    )
    multi_state, multi_metrics = run_benchmark(
        "multi-agent",
        clean_query,
        multi_runner or run_multi_agent,
    )
    hosted_exports = []
    if export_hosted:
        hosted_exports = [
            *export_hosted_traces(baseline_state, "baseline benchmark"),
            *export_hosted_traces(multi_state, "multi-agent benchmark"),
        ]

    report = render_markdown_report([baseline_metrics, multi_metrics], trace_state=multi_state)
    payload = {
        "query": clean_query,
        "runs": {
            "baseline": _run_payload(baseline_state, baseline_metrics, "baseline"),
            "multi_agent": _run_payload(multi_state, multi_metrics, "multi_agent"),
        },
        "comparison": _comparison_payload(baseline_metrics, multi_metrics),
        "report_markdown": report,
        "hosted_exports": [item.as_dict() for item in hosted_exports],
        "artifacts": {
            "benchmark_report": "reports/benchmark_report.md",
            "last_trace": "reports/last_trace.json",
            "hosted_trace_exports": "reports/hosted_trace_exports.json",
            "web_demo_last_run": "reports/web_demo_last_run.json",
        },
    }
    _write_demo_artifacts(payload, report, multi_state, hosted_exports)
    return payload


def run_baseline(query: str) -> ResearchState:
    """Single-agent baseline used by CLI and web demo."""

    state = ResearchState(request=ResearchQuery(query=query))
    response = LLMClient().complete(
        system_prompt=(
            "You are a single-agent research baseline. Answer directly and concisely. "
            "Do not claim external sources unless provided."
        ),
        user_prompt=query,
    )
    state.final_answer = response.content
    state.add_trace_event(
        "baseline.complete",
        {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens},
    )
    return state


def run_multi_agent(query: str) -> ResearchState:
    """Multi-agent workflow runner used by the web demo."""

    return MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=query)))


def _run_payload(
    state: ResearchState,
    metrics: BenchmarkMetrics,
    run_kind: str,
) -> dict[str, Any]:
    return {
        "run_name": metrics.run_name,
        "answer": state.final_answer or "",
        "latency_seconds": metrics.latency_seconds,
        "citation_coverage": metrics.citation_coverage,
        "notes": metrics.notes,
        "route_history": state.route_history,
        "trace": state.trace,
        "agent_results": [item.model_dump(mode="json") for item in state.agent_results],
        "sources": [item.model_dump(mode="json") for item in state.sources],
        "tools": _tool_payload(state, run_kind),
        "flow": _flow_payload(state, run_kind),
        "metrics": {
            "latency_seconds": metrics.latency_seconds,
            "citation_coverage": metrics.citation_coverage,
            "source_count": len(state.sources),
            "route_count": len(state.route_history),
            "input_tokens": _metadata_total(state, "input_tokens"),
            "output_tokens": _metadata_total(state, "output_tokens"),
        },
    }


def _tool_payload(state: ResearchState, run_kind: str) -> list[dict[str, Any]]:
    if run_kind == "baseline":
        return [
            {
                "owner": "baseline",
                "name": "OpenAI Responses API",
                "purpose": "Single-agent direct answer",
                "metadata": _baseline_metadata(state),
            }
        ]

    tools = [
        {
            "owner": "researcher",
            "name": "OpenAI web_search_preview",
            "purpose": "Find current web evidence and URL citations",
            "metadata": {"source_count": len(state.sources)},
        }
    ]
    for result in state.agent_results:
        if str(result.agent) in {"analyst", "writer"}:
            tools.append(
                {
                    "owner": str(result.agent),
                    "name": "OpenAI Responses API",
                    "purpose": f"{result.agent} LLM reasoning",
                    "metadata": dict(result.metadata),
                }
            )
    return tools


def _flow_payload(state: ResearchState, run_kind: str) -> dict[str, Any]:
    if run_kind == "baseline":
        return {
            "nodes": [
                {"id": "query", "label": "User Query", "kind": "input"},
                {"id": "baseline", "label": "Baseline LLM", "kind": "model"},
                {"id": "answer", "label": "Answer", "kind": "output"},
            ],
            "edges": [
                {"from": "query", "to": "baseline", "label": "direct prompt"},
                {"from": "baseline", "to": "answer", "label": "final answer"},
            ],
        }

    nodes = [{"id": "query", "label": "User Query", "kind": "input"}]
    nodes.extend(
        {"id": route, "label": route.title(), "kind": "agent"}
        for route in state.route_history
        if route != "done"
    )
    nodes.append({"id": "answer", "label": "Answer", "kind": "output"})

    sequence = [node["id"] for node in nodes]
    edges = [
        {"from": source, "to": target, "label": _edge_label(source, target)}
        for source, target in zip(sequence, sequence[1:], strict=False)
    ]
    return {"nodes": nodes, "edges": edges}


def _edge_label(source: str, target: str) -> str:
    labels = {
        ("query", "researcher"): "search task",
        ("researcher", "analyst"): "evidence notes",
        ("analyst", "writer"): "analysis brief",
        ("writer", "answer"): "final report",
    }
    return labels.get((source, target), "handoff")


def _comparison_payload(
    baseline_metrics: BenchmarkMetrics,
    multi_metrics: BenchmarkMetrics,
) -> dict[str, float | None]:
    baseline_coverage = baseline_metrics.citation_coverage or 0.0
    multi_coverage = multi_metrics.citation_coverage or 0.0
    baseline_sources = _source_count_from_notes(baseline_metrics.notes)
    multi_sources = _source_count_from_notes(multi_metrics.notes)
    return {
        "latency_delta_seconds": multi_metrics.latency_seconds - baseline_metrics.latency_seconds,
        "citation_coverage_delta": multi_coverage - baseline_coverage,
        "source_delta": multi_sources - baseline_sources,
    }


def _write_demo_artifacts(
    payload: dict[str, Any],
    report: str,
    multi_state: ResearchState,
    hosted_exports: list[Any],
) -> None:
    store = LocalArtifactStore()
    store.write_text("benchmark_report.md", report)
    store.write_text(
        "last_trace.json",
        json.dumps(
            {
                "run_name": "multi-agent",
                "route_history": multi_state.route_history,
                "trace": multi_state.trace,
                "agent_results": [
                    item.model_dump(mode="json") for item in multi_state.agent_results
                ],
            },
            indent=2,
        ),
    )
    store.write_text(
        "hosted_trace_exports.json",
        json.dumps([item.as_dict() for item in hosted_exports], indent=2),
    )
    store.write_text("web_demo_last_run.json", json.dumps(payload, indent=2))


def _baseline_metadata(state: ResearchState) -> dict[str, Any]:
    for event in state.trace:
        if event.get("name") == "baseline.complete":
            return dict(event.get("payload", {}))
    return {}


def _metadata_total(state: ResearchState, key: str) -> int:
    total = 0
    for result in state.agent_results:
        value = result.metadata.get(key)
        if isinstance(value, int):
            total += value
    if total:
        return total
    baseline_value = _baseline_metadata(state).get(key)
    return baseline_value if isinstance(baseline_value, int) else 0


def _source_count_from_notes(notes: str) -> int:
    for part in notes.split():
        if part.startswith("sources="):
            return int(part.removeprefix("sources="))
    return 0
