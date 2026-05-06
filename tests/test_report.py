from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    BenchmarkMetrics,
    ResearchQuery,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.report import render_markdown_report


def test_report_renders_markdown() -> None:
    report = render_markdown_report(
        [
            BenchmarkMetrics(
                run_name="baseline",
                latency_seconds=1.23,
                estimated_cost_usd=0.0,
                quality_score=4.0,
            )
        ]
    )
    assert "Benchmark Report" in report
    assert "| baseline | 1.23 | 0.0000 | 4.0 | N/A |" in report


def test_agent_trace_summary_uses_na_for_missing_tokens() -> None:
    state = ResearchState(request=ResearchQuery(query="Summarize production guardrails"))
    state.sources = []
    state.add_trace_event(
        "agent.end",
        {
            "agent": "researcher",
            "duration_seconds": 0.12,
            "status": "ok",
            "metadata": {},
        },
    )
    state.add_trace_event(
        "agent.end",
        {
            "agent": "writer",
            "duration_seconds": 0.34,
            "status": "ok",
            "metadata": {"input_tokens": 10, "output_tokens": 20},
        },
    )
    state.agent_results.append(
        AgentResult(agent=AgentName.WRITER, content="answer", metadata={})
    )

    report = render_markdown_report(
        [
            BenchmarkMetrics(
                run_name="multi-agent",
                latency_seconds=1.0,
                estimated_cost_usd=0.0,
                quality_score=8.0,
            )
        ],
        trace_state=state,
    )

    assert "| researcher | 0.12 | N/A | N/A | sources=0 |" in report
    assert "| writer | 0.34 | 10 | 20 | N/A |" in report
