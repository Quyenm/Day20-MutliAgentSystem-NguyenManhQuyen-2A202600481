from types import SimpleNamespace

from multi_agent_research_lab.services.search_client import SearchClient


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="web_search_call",
                    status="completed",
                ),
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(
                            type="output_text",
                            text=(
                                "Source one explains role clarity. "
                                "Source two explains tracing."
                            ),
                            annotations=[
                                SimpleNamespace(
                                    type="url_citation",
                                    title="Role clarity guide",
                                    url="https://example.com/roles",
                                    start_index=0,
                                    end_index=33,
                                ),
                                SimpleNamespace(
                                    type="url_citation",
                                    title="Tracing guide",
                                    url="https://example.com/tracing",
                                    start_index=41,
                                    end_index=69,
                                ),
                            ],
                        )
                    ],
                ),
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_search_client_uses_openai_web_search_when_api_key_and_client_are_provided() -> None:
    fake_client = FakeOpenAIClient()
    client = SearchClient(api_key="test-key", model="gpt-test", openai_client=fake_client)

    results = client.search("production LLM agent tracing", max_results=1)

    assert len(results) == 1
    assert results[0].title == "Role clarity guide"
    assert results[0].url == "https://example.com/roles"
    assert results[0].snippet == "Source one explains role clarity."
    assert results[0].metadata == {"provider": "openai_web_search", "rank": 1}
    assert fake_client.responses.calls == [
        {
            "model": "gpt-test",
            "input": "Find reliable sources for: production LLM agent tracing",
            "tools": [{"type": "web_search_preview"}],
        }
    ]


def test_search_client_keeps_local_fallback_without_api_key() -> None:
    results = SearchClient(api_key=None).search("agent guardrails", max_results=2)

    assert [item.metadata["provider"] for item in results] == ["local", "local"]
    assert results[0].title == "Local source 1: agent guardrails"
