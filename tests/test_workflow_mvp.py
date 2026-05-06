from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_linear_workflow_produces_research_answer_with_trace(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    state = ResearchState(
        request=ResearchQuery(
            query="Explain production guardrails for LLM agents",
            max_sources=2,
        )
    )

    result = MultiAgentWorkflow().run(state)

    assert result.route_history == ["researcher", "analyst", "writer", "done"]
    assert len(result.sources) == 2
    assert result.research_notes
    assert result.analysis_notes
    assert result.final_answer
    assert "production guardrails for llm agents" in result.final_answer.lower()
    assert [item.agent for item in result.agent_results] == ["researcher", "analyst", "writer"]
    trace_names = [event["name"] for event in result.trace]
    assert trace_names == [
        "workflow.start",
        "workflow.route",
        "agent.start",
        "agent.end",
        "workflow.route",
        "agent.start",
        "agent.end",
        "workflow.route",
        "agent.start",
        "agent.end",
        "workflow.route",
        "workflow.end",
    ]
    agent_end_events = [event for event in result.trace if event["name"] == "agent.end"]
    assert [event["payload"]["agent"] for event in agent_end_events] == [
        "researcher",
        "analyst",
        "writer",
    ]
    assert all(event["payload"]["duration_seconds"] >= 0 for event in agent_end_events)
    get_settings.cache_clear()
