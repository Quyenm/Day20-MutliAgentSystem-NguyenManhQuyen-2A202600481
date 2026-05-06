from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMResponse


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.calls.append((system_prompt, user_prompt))
        return LLMResponse(content="Model-written analysis", input_tokens=21, output_tokens=13)


def test_analyst_uses_llm_client_with_research_context() -> None:
    llm_client = FakeLLMClient()
    state = ResearchState(
        request=ResearchQuery(query="Compare LLM guardrail patterns"),
        sources=[
            SourceDocument(
                title="Guardrail guide",
                url="https://example.com/guardrails",
                snippet="Input and output filters reduce safety risks.",
            )
        ],
        research_notes="- [1] Guardrail guide: Input and output filters reduce safety risks.",
    )

    result = AnalystAgent(llm_client=llm_client).run(state)

    assert result.analysis_notes == "Model-written analysis"
    assert result.agent_results[-1].metadata == {"input_tokens": 21, "output_tokens": 13}
    assert len(llm_client.calls) == 1
    system_prompt, user_prompt = llm_client.calls[0]
    assert "analyst" in system_prompt.lower()
    assert "Compare LLM guardrail patterns" in user_prompt
    assert "Guardrail guide" in user_prompt
    assert "Input and output filters" in user_prompt
