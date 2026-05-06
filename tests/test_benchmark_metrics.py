from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    ResearchQuery,
    SourceDocument,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    estimate_cost_usd,
    score_quality,
    token_totals,
)


def test_token_totals_include_baseline_trace_and_agent_metadata() -> None:
    state = ResearchState(request=ResearchQuery(query="Summarize guardrails"))
    state.add_trace_event("baseline.complete", {"input_tokens": 10, "output_tokens": 20})
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content="answer",
            metadata={"input_tokens": 30, "output_tokens": 40},
        )
    )

    assert token_totals(state) == {"input_tokens": 40, "output_tokens": 60}


def test_estimate_cost_uses_token_totals() -> None:
    state = ResearchState(request=ResearchQuery(query="Summarize guardrails"))
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content="answer",
            metadata={"input_tokens": 1_000_000, "output_tokens": 1_000_000},
        )
    )

    assert estimate_cost_usd(state) == 0.75


def test_quality_score_rewards_sources_citations_and_route() -> None:
    state = ResearchState(request=ResearchQuery(query="Summarize guardrails"))
    state.final_answer = "Answer with citation [1]."
    state.route_history = ["researcher", "analyst", "writer", "done"]
    state.sources = [SourceDocument(title="Source", url="https://example.com", snippet="snippet")]

    assert score_quality(state) == 8.9
