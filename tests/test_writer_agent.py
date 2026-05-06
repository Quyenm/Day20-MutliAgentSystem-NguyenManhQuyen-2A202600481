from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMResponse


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.calls.append((system_prompt, user_prompt))
        return LLMResponse(content="Model-written final answer", input_tokens=12, output_tokens=8)


def test_writer_uses_llm_client_with_research_context() -> None:
    llm_client = FakeLLMClient()
    state = ResearchState(
        request=ResearchQuery(query="Explain agent tracing"),
        sources=[SourceDocument(title="Trace guide", snippet="Trace every agent step.")],
        research_notes="- Trace every agent step.",
        analysis_notes="- Trace logs explain handoffs.",
    )

    result = WriterAgent(llm_client=llm_client).run(state)

    assert result.final_answer == "Model-written final answer"
    assert result.agent_results[-1].metadata == {"input_tokens": 12, "output_tokens": 8}
    assert len(llm_client.calls) == 1
    system_prompt, user_prompt = llm_client.calls[0]
    assert "writer" in system_prompt.lower()
    assert "Explain agent tracing" in user_prompt
    assert "Trace guide" in user_prompt
    assert "Trace logs explain handoffs" in user_prompt
