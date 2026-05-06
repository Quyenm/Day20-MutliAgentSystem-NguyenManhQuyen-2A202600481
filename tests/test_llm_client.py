from types import SimpleNamespace

from multi_agent_research_lab.services.llm_client import LLMClient


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text="Provider answer",
            usage=SimpleNamespace(input_tokens=7, output_tokens=11),
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_llm_client_uses_openai_responses_api_when_client_is_provided() -> None:
    fake_client = FakeOpenAIClient()
    client = LLMClient(api_key="test-key", model="gpt-test", openai_client=fake_client)

    response = client.complete("You are concise.", "Summarize agent guardrails.")

    assert response.content == "Provider answer"
    assert response.input_tokens == 7
    assert response.output_tokens == 11
    assert fake_client.responses.calls == [
        {
            "model": "gpt-test",
            "instructions": "You are concise.",
            "input": "Summarize agent guardrails.",
        }
    ]


def test_llm_client_keeps_local_fallback_without_api_key() -> None:
    response = LLMClient(api_key=None).complete("System prompt", "User prompt")

    assert "Local LLM draft." in response.content
    assert "System prompt" in response.content
    assert "User prompt" in response.content
