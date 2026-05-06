from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState


def test_critic_records_citation_review_without_crashing() -> None:
    state = ResearchState(request=ResearchQuery(query="Summarize production guardrails"))
    state.final_answer = "Guardrails need monitoring and citations [1]."
    state.sources = [
        SourceDocument(
            title="Guardrails",
            url="https://example.com/guardrails",
            snippet="Guardrails reference",
        )
    ]

    result = CriticAgent().run(state)

    assert result.agent_results[-1].agent == "critic"
    assert result.agent_results[-1].metadata == {
        "source_count": 1,
        "citation_coverage": 1.0,
        "has_final_answer": True,
    }
